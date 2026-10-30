from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional, Tuple

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)
from tenacity.wait import wait_base

from app.core.config import settings

logger = logging.getLogger(__name__)

ELEXON_BASE_URL = settings.elexon_api_base_url
HTTP_TIMEOUT = 30.0
MAX_RETRIES = 3


class ElexonAPIError(RuntimeError):
    """Raised when the Elexon API returns an error response."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class ElexonConnectionError(RuntimeError):
    """Raised when the Elexon API connection fails."""


class ElexonEmptyResponseError(RuntimeError):
    """Raised when the Elexon API returns an empty response."""


def _build_url(endpoint: str) -> str:
    """Build the full API URL from the base URL and endpoint."""
    base = settings.elexon_api_base_url.rstrip("/")
    return f"{base}/{endpoint.lstrip('/')}"


def _format_date(d: date | datetime) -> str:
    """Format a date or datetime to YYYY-MM-DD string."""
    if isinstance(d, datetime):
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        d = d.date()
    return d.isoformat()


def _format_datetime(dt: datetime) -> str:
    """Format a datetime to ISO 8601 string in UTC for Elexon API."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_retryable_exception(exc: BaseException) -> bool:
    """Determine whether an exception is transient and safe to retry."""
    if isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.NetworkError,
            ElexonConnectionError,
        ),
    ):
        return True
    if isinstance(exc, ElexonAPIError):
        if exc.status_code == 429:
            return True
        if exc.status_code is not None and exc.status_code >= 500:
            return True
    return False


class _ElexonWaitStrategy(wait_base):
    """Tenacity wait strategy that respects Retry-After when available."""

    def __init__(self, fallback_wait: wait_base) -> None:
        self.fallback_wait = fallback_wait

    def __call__(self, retry_state: RetryCallState) -> float:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if isinstance(exc, ElexonAPIError) and exc.retry_after is not None:
            return min(float(exc.retry_after), 30.0)
        return self.fallback_wait(retry_state)


@retry(
    reraise=True,
    stop=stop_after_attempt(MAX_RETRIES),
    retry=retry_if_exception(_is_retryable_exception),
    wait=_ElexonWaitStrategy(wait_exponential(multiplier=0.1, min=0.1, max=2.0)),
)
async def _async_request(
    client: httpx.AsyncClient,
    method: str,
    endpoint: str,
    timeout: float = HTTP_TIMEOUT,
    **params: Any,
) -> dict[str, Any]:
    """Make a retryable HTTP request to the Elexon API."""
    url = _build_url(endpoint)
    logger.debug("Making %s request to %s with params %s", method.upper(), url, params)

    try:
        response = await client.request(method, url, params=params, timeout=timeout)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
        logger.error("Connection error to Elexon API: %s", exc)
        raise ElexonConnectionError(f"Failed to connect to Elexon API: {exc}") from exc

    retry_after: Optional[float] = None
    if "retry-after" in response.headers:
        try:
            retry_after = float(response.headers["retry-after"])
        except (ValueError, TypeError):
            retry_after = None

    if response.status_code == 429:
        logger.warning("Elexon API 429 rate limit exceeded. Retry-After: %s", retry_after)
        raise ElexonAPIError(
            f"Elexon API 429 rate limit exceeded: {response.text}",
            status_code=429,
            retry_after=retry_after,
        )

    if response.status_code >= 500:
        logger.warning("Elexon API %s server error", response.status_code)
        raise ElexonAPIError(
            f"Elexon API {response.status_code}: {response.text}",
            status_code=response.status_code,
        )

    if response.status_code >= 400:
        logger.warning("Elexon API client error %s", response.status_code)
        raise ElexonAPIError(
            f"Elexon API error {response.status_code}: {response.text}",
            status_code=response.status_code,
        )

    if response.status_code != 200:
        raise ElexonAPIError(
            f"Unexpected status code {response.status_code}: {response.text}",
            status_code=response.status_code,
        )

    try:
        data = response.json()
    except Exception as exc:
        logger.error("Failed to parse JSON from Elexon API response: %s", exc)
        raise ElexonAPIError("Failed to parse API response JSON") from exc

    if data is None or (isinstance(data, dict) and not data):
        logger.warning("Elexon API returned empty response for %s", endpoint)
        raise ElexonEmptyResponseError("Elexon API returned empty response")

    return data


def extract_records(response_data: Any) -> list[dict[str, Any]]:
    """Extract list of records from Elexon API response envelope."""
    if isinstance(response_data, list):
        return response_data
    if isinstance(response_data, dict):
        if "data" in response_data and isinstance(response_data["data"], list):
            return response_data["data"]
        if "items" in response_data and isinstance(response_data["items"], list):
            return response_data["items"]
    return []


def chunk_datetime_range(
    start_dt: datetime,
    end_dt: datetime,
    max_days: int = 7,
) -> list[tuple[datetime, datetime]]:
    """Split [start_dt, end_dt] into non-overlapping sub-ranges of at most max_days."""
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    else:
        start_dt = start_dt.astimezone(timezone.utc)

    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)
    else:
        end_dt = end_dt.astimezone(timezone.utc)

    if start_dt > end_dt:
        return []

    chunks: list[tuple[datetime, datetime]] = []
    current = start_dt
    delta = timedelta(days=max_days)

    while current < end_dt:
        nxt = min(current + delta, end_dt)
        chunks.append((current, nxt))
        current = nxt

    if not chunks and start_dt == end_dt:
        chunks.append((start_dt, end_dt))

    return chunks


def chunk_date_range(
    start_date: date,
    end_date: date,
    max_days: int = 7,
) -> list[tuple[str, str]]:
    """Split [start_date, end_date] into date chunks of at most max_days."""
    if start_date > end_date:
        return []

    chunks: list[tuple[str, str]] = []
    current = start_date
    delta = timedelta(days=max_days - 1)

    while current <= end_date:
        nxt = min(current + delta, end_date)
        chunks.append((current.isoformat(), nxt.isoformat()))
        current = nxt + timedelta(days=1)

    return chunks


async def fetch_windfor(
    client: httpx.AsyncClient,
    publish_date_from: datetime,
    publish_date_to: datetime,
) -> dict[str, Any]:
    """Fetch WINDFOR dataset from the Elexon API for a single chunk."""
    endpoint = "datasets/WINDFOR"
    params = {
        "publishDateTimeFrom": _format_datetime(publish_date_from),
        "publishDateTimeTo": _format_datetime(publish_date_to),
    }
    return await _async_request(client, "GET", endpoint, **params)


async def fetch_fuelhh(
    client: httpx.AsyncClient,
    settlement_date_from: str,
    settlement_date_to: str,
    fuel_type: str = "WIND",
) -> dict[str, Any]:
    """Fetch FUELHH dataset from the Elexon API for a single chunk."""
    endpoint = "datasets/FUELHH"
    params = {
        "settlementDateFrom": settlement_date_from,
        "settlementDateTo": settlement_date_to,
        "fuelType": fuel_type,
    }
    return await _async_request(client, "GET", endpoint, **params)


async def get_windfor_records(
    publish_date_from: datetime,
    publish_date_to: datetime,
    client: Optional[httpx.AsyncClient] = None,
) -> list[dict[str, Any]]:
    """Fetch and return all WINDFOR records across chunked requests.

    Automatically splits the requested date range into windows of <= 7 days
    to comply with Elexon's maximum query limit.
    """
    chunks = chunk_datetime_range(publish_date_from, publish_date_to, max_days=7)
    records: list[dict[str, Any]] = []

    async def _fetch_all(c: httpx.AsyncClient) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for start_chunk, end_chunk in chunks:
            data = await fetch_windfor(c, start_chunk, end_chunk)
            chunk_records = extract_records(data)
            results.extend(chunk_records)
        return results

    if client is not None:
        return await _fetch_all(client)

    async with httpx.AsyncClient() as new_client:
        return await _fetch_all(new_client)


async def get_fuelhh_records(
    settlement_date_from: str,
    settlement_date_to: str,
    fuel_type: str = "WIND",
    client: Optional[httpx.AsyncClient] = None,
) -> list[dict[str, Any]]:
    """Fetch and return all FUELHH records across chunked requests.

    Automatically splits the requested date range into windows of <= 7 days
    to comply with Elexon's maximum query limit.
    """
    from datetime import date as _date

    start_d = _date.fromisoformat(settlement_date_from)
    end_d = _date.fromisoformat(settlement_date_to)
    chunks = chunk_date_range(start_d, end_d, max_days=7)

    async def _fetch_all(c: httpx.AsyncClient) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for start_chunk, end_chunk in chunks:
            data = await fetch_fuelhh(c, start_chunk, end_chunk, fuel_type=fuel_type)
            chunk_records = extract_records(data)
            results.extend(chunk_records)
        return results

    if client is not None:
        return await _fetch_all(client)

    async with httpx.AsyncClient() as new_client:
        return await _fetch_all(new_client)
