from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.accuracy import (
    AccuracySummaryResponse,
    ErrorObservationsResponse,
    TimeseriesResponse,
    TopErrorsResponse,
)
from app.services.accuracy import (
    get_accuracy_summary,
    get_accuracy_timeseries,
    get_error_distribution_and_observations,
    get_top_errors,
)

LONDON_TZ = ZoneInfo("Europe/London")

router = APIRouter(tags=["Accuracy Analytics"])


def _parse_query_dates(
    start_date: Optional[str],
    end_date: Optional[str],
) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parse and validate date/datetime query parameters into timezone-aware UTC.

    - Date-only strings (YYYY-MM-DD) are interpreted as UK market delivery dates
      in Europe/London (start of day: 00:00:00 London -> UTC, end of day: 23:59:59.999999 London -> UTC).
    - ISO 8601 timestamps are parsed and converted to UTC (naive timestamps default to Europe/London).
    """
    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None

    if start_date:
        try:
            if "T" in start_date or " " in start_date:
                dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=LONDON_TZ)
                start_dt = dt.astimezone(timezone.utc)
            else:
                d = datetime.strptime(start_date, "%Y-%m-%d").date()
                local_dt = datetime.combine(d, time.min, tzinfo=LONDON_TZ)
                start_dt = local_dt.astimezone(timezone.utc)
        except ValueError as err:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid start_date format: {start_date}. Expected YYYY-MM-DD or ISO 8601.",
            ) from err

    if end_date:
        try:
            if "T" in end_date or " " in end_date:
                dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=LONDON_TZ)
                end_dt = dt.astimezone(timezone.utc)
            else:
                d = datetime.strptime(end_date, "%Y-%m-%d").date()
                local_dt = datetime.combine(d, time(23, 59, 59, 999999), tzinfo=LONDON_TZ)
                end_dt = local_dt.astimezone(timezone.utc)
        except ValueError as err:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid end_date format: {end_date}. Expected YYYY-MM-DD or ISO 8601.",
            ) from err

    if start_dt and end_dt and start_dt > end_dt:
        raise HTTPException(
            status_code=400,
            detail=f"start_date ({start_date}) must be before or equal to end_date ({end_date}).",
        )

    return start_dt, end_dt


@router.get("", response_model=AccuracySummaryResponse)
def get_accuracy(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO 8601)"),
    cutoff_hour: int = Query(15, ge=0, le=23, description="Decision cutoff hour (default: 15)"),
    cutoff_minute: int = Query(0, ge=0, le=59, description="Decision cutoff minute (default: 0)"),
    db: Session = Depends(get_db),
) -> AccuracySummaryResponse:
    """Retrieve overall aggregate accuracy metrics (MAE, RMSE, Bias) and daily metrics."""
    start_dt, end_dt = _parse_query_dates(start_date, end_date)
    return get_accuracy_summary(
        session=db,
        start_time=start_dt,
        end_time=end_dt,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
    )


@router.get("/timeseries", response_model=TimeseriesResponse)
def get_timeseries(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO 8601)"),
    cutoff_hour: int = Query(15, ge=0, le=23, description="Decision cutoff hour (default: 15)"),
    cutoff_minute: int = Query(0, ge=0, le=59, description="Decision cutoff minute (default: 0)"),
    granularity: str = Query("hourly", pattern="^(hourly|daily)$", description="'hourly' or 'daily'"),
    db: Session = Depends(get_db),
) -> TimeseriesResponse:
    """Retrieve forecast error time series with hourly or daily granularity."""
    start_dt, end_dt = _parse_query_dates(start_date, end_date)
    return get_accuracy_timeseries(
        session=db,
        start_time=start_dt,
        end_time=end_dt,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
        granularity=granularity,
    )


@router.get("/errors", response_model=ErrorObservationsResponse)
def get_errors(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO 8601)"),
    cutoff_hour: int = Query(15, ge=0, le=23, description="Decision cutoff hour (default: 15)"),
    cutoff_minute: int = Query(0, ge=0, le=59, description="Decision cutoff minute (default: 0)"),
    page: int = Query(1, ge=1, description="Page number (default: 1)"),
    limit: int = Query(100, ge=1, le=1000, description="Observations per page (default: 100)"),
    bin_size: Optional[float] = Query(None, gt=0, description="Optional custom histogram bin width in MW"),
    db: Session = Depends(get_db),
) -> ErrorObservationsResponse:
    """Retrieve error distribution histogram, summary statistics, and individual error observations."""
    start_dt, end_dt = _parse_query_dates(start_date, end_date)
    return get_error_distribution_and_observations(
        session=db,
        start_time=start_dt,
        end_time=end_dt,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
        page=page,
        limit=limit,
        bin_size=bin_size,
    )


@router.get("/top-errors", response_model=TopErrorsResponse)
def get_top_forecast_errors(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO 8601)"),
    cutoff_hour: int = Query(15, ge=0, le=23, description="Decision cutoff hour (default: 15)"),
    cutoff_minute: int = Query(0, ge=0, le=59, description="Decision cutoff minute (default: 0)"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return (default: 10)"),
    error_type: str = Query(
        "absolute",
        pattern="^(absolute|overforecast|underforecast)$",
        description="'absolute' (|error|), 'overforecast' (+error), or 'underforecast' (-error)",
    ),
    db: Session = Depends(get_db),
) -> TopErrorsResponse:
    """Retrieve largest forecast errors ranked by error magnitude."""
    start_dt, end_dt = _parse_query_dates(start_date, end_date)
    return get_top_errors(
        session=db,
        start_time=start_dt,
        end_time=end_dt,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
        limit=limit,
        error_type=error_type,
    )
