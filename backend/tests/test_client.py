from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.ingestion.client import (
    ElexonAPIError,
    ElexonConnectionError,
    ElexonEmptyResponseError,
    _async_request,
    _format_date,
    _format_datetime,
    _is_retryable_exception,
    chunk_date_range,
    chunk_datetime_range,
    extract_records,
    fetch_fuelhh,
    fetch_windfor,
    get_fuelhh_records,
    get_windfor_records,
)


class TestClientFormattingAndChunking:
    """Test date/datetime formatting and chunking utilities."""

    def test_format_date(self) -> None:
        dt = datetime(2026, 1, 15, tzinfo=timezone.utc)
        assert _format_date(dt) == "2026-01-15"

    def test_format_datetime(self) -> None:
        dt = datetime(2026, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        assert _format_datetime(dt) == "2026-01-15T12:30:45Z"

    def test_datetime_chunking_exceeding_7_days(self) -> None:
        """Verify that a 31-day datetime range is split into chunks of at most 7 days."""
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        chunks = chunk_datetime_range(start, end, max_days=7)

        assert len(chunks) == 5
        for s, e in chunks:
            diff_days = (e - s).total_seconds() / 86400
            assert diff_days <= 7.0

        assert chunks[0][0] == start
        assert chunks[-1][1] == end

    def test_date_chunking_january_delivery(self) -> None:
        """Verify that settlement dates Jan 2 - Feb 1 are split into chunks <= 7 days."""
        start = date(2026, 1, 2)
        end = date(2026, 2, 1)
        chunks = chunk_date_range(start, end, max_days=7)

        assert len(chunks) == 5
        assert chunks[0] == ("2026-01-02", "2026-01-08")
        assert chunks[-1] == ("2026-01-30", "2026-02-01")


class TestEnvelopeExtraction:
    """Test parsing of Elexon response envelopes."""

    def test_extract_data_envelope(self) -> None:
        response = {"data": [{"dataset": "WINDFOR", "generation": 100.0}]}
        records = extract_records(response)
        assert len(records) == 1
        assert records[0]["generation"] == 100.0

    def test_extract_legacy_items_envelope(self) -> None:
        response = {"items": [{"dataset": "FUELHH", "generation": 200.0}]}
        records = extract_records(response)
        assert len(records) == 1
        assert records[0]["generation"] == 200.0

    def test_extract_empty_envelope(self) -> None:
        response = {"data": []}
        assert extract_records(response) == []


class TestRetryLogic:
    """Test retry predicates and HTTP error classifications."""

    def test_is_retryable_transient_errors(self) -> None:
        assert _is_retryable_exception(httpx.ConnectError("Connection refused")) is True
        assert _is_retryable_exception(httpx.TimeoutException("Read timed out")) is True
        assert _is_retryable_exception(ElexonAPIError("Rate limit", status_code=429)) is True
        assert _is_retryable_exception(ElexonAPIError("Server error", status_code=500)) is True
        assert _is_retryable_exception(ElexonAPIError("Bad Gateway", status_code=502)) is True

    def test_is_not_retryable_permanent_client_errors(self) -> None:
        # 400 Bad Request, 404 Not Found should fail fast without retry
        assert _is_retryable_exception(ElexonAPIError("Bad Request", status_code=400)) is False
        assert _is_retryable_exception(ElexonAPIError("Not Found", status_code=404)) is False
        assert _is_retryable_exception(ValueError("Invalid argument")) is False


class TestFetchOperations:
    """Test HTTP fetching with mocked async client."""

    def test_fetch_windfor_success(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "dataset": "WINDFOR",
                    "publishTime": "2026-01-01T12:00:00Z",
                    "startTime": "2026-01-02T00:00:00Z",
                    "generation": 1250.5,
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        res = asyncio.run(fetch_windfor(
            mock_client,
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 2, tzinfo=timezone.utc),
        ))
        assert "data" in res
        assert len(res["data"]) == 1

    def test_fetch_permanent_400_not_retried(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "The date range must not exceed 7 days"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        with pytest.raises(ElexonAPIError) as exc:
            asyncio.run(fetch_windfor(
                mock_client,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 15, tzinfo=timezone.utc),
            ))
        assert exc.value.status_code == 400
        # Should only be called once because 400 is not retryable
        assert mock_client.request.call_count == 1
