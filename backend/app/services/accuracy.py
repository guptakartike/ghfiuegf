from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

import numpy as np
from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.models.matched_observation import MatchedHourlyObservation
from app.schemas.accuracy import (
    AccuracyMetrics,
    AccuracySummaryResponse,
    DailyAccuracyMetric,
    DailyTimeseriesPoint,
    ErrorDistributionBin,
    ErrorDistributionStats,
    ErrorObservationsResponse,
    HourlyTimeseriesPoint,
    TimeseriesResponse,
    TopErrorRecord,
    TopErrorsResponse,
)
from app.services.cutoff import CutoffConfig, get_decision_cutoff

LONDON_TZ = ZoneInfo("Europe/London")


def compute_accuracy_metrics(
    records: Sequence[MatchedHourlyObservation],
) -> AccuracyMetrics:
    """Calculate MAE, RMSE, Bias, sample count, and extremes from matched observations."""
    if not records:
        return AccuracyMetrics(
            mae=None,
            rmse=None,
            bias=None,
            sample_count=0,
            avg_forecast=None,
            avg_actual=None,
            min_error=None,
            max_error=None,
        )

    errors = np.array([r.forecast_error for r in records], dtype=np.float64)
    forecasts = np.array([r.forecast_generation for r in records], dtype=np.float64)
    actuals = np.array([r.actual_generation for r in records], dtype=np.float64)

    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    bias = float(np.mean(errors))
    avg_f = float(np.mean(forecasts))
    avg_a = float(np.mean(actuals))
    min_e = float(np.min(errors))
    max_e = float(np.max(errors))

    return AccuracyMetrics(
        mae=round(mae, 2),
        rmse=round(rmse, 2),
        bias=round(bias, 2),
        sample_count=len(records),
        avg_forecast=round(avg_f, 2),
        avg_actual=round(avg_a, 2),
        min_error=round(min_e, 2),
        max_error=round(max_e, 2),
    )


def compute_daily_metrics(
    records: Sequence[MatchedHourlyObservation],
) -> List[DailyAccuracyMetric]:
    """Group observations by UK delivery date (Europe/London) and compute daily accuracy metrics."""
    by_day: Dict[str, List[MatchedHourlyObservation]] = {}

    for r in records:
        dt = (
            r.delivery_time.replace(tzinfo=timezone.utc)
            if r.delivery_time.tzinfo is None
            else r.delivery_time.astimezone(timezone.utc)
        )
        local_date_str = dt.astimezone(LONDON_TZ).strftime("%Y-%m-%d")
        by_day.setdefault(local_date_str, []).append(r)

    daily_results: List[DailyAccuracyMetric] = []
    for day_str in sorted(by_day.keys()):
        day_records = by_day[day_str]
        metrics = compute_accuracy_metrics(day_records)
        daily_results.append(
            DailyAccuracyMetric(
                date=day_str,
                mae=metrics.mae,
                rmse=metrics.rmse,
                bias=metrics.bias,
                sample_count=metrics.sample_count,
                avg_forecast=metrics.avg_forecast,
                avg_actual=metrics.avg_actual,
            )
        )

    return daily_results


def _filter_records(
    session: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    cutoff_hour: Optional[int] = 15,
    cutoff_minute: int = 0,
    days_ahead: int = 1,
) -> List[MatchedHourlyObservation]:
    """Query matched observations with optional delivery window and cutoff timestamp filter.

    Filters observations using the exact expected cutoff timestamp computed via
    get_decision_cutoff for each delivery hour, rather than merely checking the hour.
    """
    if cutoff_hour is not None and not (0 <= cutoff_hour <= 23):
        raise ValueError(f"cutoff_hour must be between 0 and 23, got {cutoff_hour}")
    if not (0 <= cutoff_minute <= 59):
        raise ValueError(f"cutoff_minute must be between 0 and 59, got {cutoff_minute}")

    stmt = select(MatchedHourlyObservation).order_by(
        MatchedHourlyObservation.delivery_time
    )

    if start_time is not None:
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        else:
            start_time = start_time.astimezone(timezone.utc)
        stmt = stmt.where(MatchedHourlyObservation.delivery_time >= start_time)

    if end_time is not None:
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        else:
            end_time = end_time.astimezone(timezone.utc)
        stmt = stmt.where(MatchedHourlyObservation.delivery_time <= end_time)

    records = session.execute(stmt).scalars().all()

    # Filter by exact decision cutoff timestamp per delivery hour
    if cutoff_hour is not None:
        cutoff_cfg = CutoffConfig(
            cutoff_hour=cutoff_hour,
            cutoff_minute=cutoff_minute,
            timezone_name="Europe/London",
            days_ahead=days_ahead,
        )
        filtered: List[MatchedHourlyObservation] = []
        for r in records:
            r_cutoff = (
                r.cutoff_time.replace(tzinfo=timezone.utc)
                if r.cutoff_time.tzinfo is None
                else r.cutoff_time.astimezone(timezone.utc)
            )
            r_delivery = (
                r.delivery_time.replace(tzinfo=timezone.utc)
                if r.delivery_time.tzinfo is None
                else r.delivery_time.astimezone(timezone.utc)
            )
            expected_cutoff = get_decision_cutoff(r_delivery, cutoff_cfg)
            if r_cutoff == expected_cutoff:
                filtered.append(r)
        return filtered

    return list(records)


def get_accuracy_summary(
    session: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    cutoff_hour: int = 15,
    cutoff_minute: int = 0,
) -> AccuracySummaryResponse:
    """Get overall and daily accuracy summary for the requested delivery window."""
    records = _filter_records(
        session,
        start_time=start_time,
        end_time=end_time,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
    )
    overall_metrics = compute_accuracy_metrics(records)
    daily_metrics = compute_daily_metrics(records)

    return AccuracySummaryResponse(
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
        delivery_from=start_time,
        delivery_to=end_time,
        overall=overall_metrics,
        daily=daily_metrics,
    )


def get_accuracy_timeseries(
    session: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    cutoff_hour: int = 15,
    cutoff_minute: int = 0,
    granularity: str = "hourly",
) -> TimeseriesResponse:
    """Get error timeseries with either hourly or daily granularity."""
    records = _filter_records(
        session,
        start_time=start_time,
        end_time=end_time,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
    )

    if granularity == "daily":
        daily_list = compute_daily_metrics(records)
        daily_points = [
            DailyTimeseriesPoint(
                date=d.date,
                mae=d.mae,
                rmse=d.rmse,
                bias=d.bias,
                sample_count=d.sample_count,
                avg_forecast=d.avg_forecast,
                avg_actual=d.avg_actual,
            )
            for d in daily_list
        ]
        return TimeseriesResponse(
            granularity="daily",
            cutoff_hour=cutoff_hour,
            cutoff_minute=cutoff_minute,
            delivery_from=start_time,
            delivery_to=end_time,
            sample_count=len(records),
            daily_data=daily_points,
            hourly_data=None,
        )

    # Hourly granularity
    hourly_points = [
        HourlyTimeseriesPoint(
            delivery_time=(
                r.delivery_time.replace(tzinfo=timezone.utc)
                if r.delivery_time.tzinfo is None
                else r.delivery_time.astimezone(timezone.utc)
            ),
            forecast_publish_time=(
                r.forecast_publish_time.replace(tzinfo=timezone.utc)
                if r.forecast_publish_time.tzinfo is None
                else r.forecast_publish_time.astimezone(timezone.utc)
            ),
            forecast_generation=float(r.forecast_generation),
            actual_generation=float(r.actual_generation),
            forecast_error=float(r.forecast_error),
            abs_error=round(abs(float(r.forecast_error)), 2),
            cutoff_time=(
                r.cutoff_time.replace(tzinfo=timezone.utc)
                if r.cutoff_time.tzinfo is None
                else r.cutoff_time.astimezone(timezone.utc)
            ),
        )
        for r in records
    ]

    return TimeseriesResponse(
        granularity="hourly",
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
        delivery_from=start_time,
        delivery_to=end_time,
        sample_count=len(records),
        hourly_data=hourly_points,
        daily_data=None,
    )


def compute_distribution_bins(
    errors: Sequence[float],
    num_bins: int = 15,
    custom_bin_size: Optional[float] = None,
) -> Tuple[List[ErrorDistributionBin], ErrorDistributionStats]:
    """Compute histogram bins and distribution statistics for forecast errors."""
    if not errors:
        return [], ErrorDistributionStats()

    arr = np.array(errors, dtype=np.float64)
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))

    stats = ErrorDistributionStats(
        min=round(min_val, 2),
        max=round(max_val, 2),
        mean=round(float(np.mean(arr)), 2),
        median=round(float(np.median(arr)), 2),
        std_dev=round(float(np.std(arr)), 2),
        p10=round(float(np.percentile(arr, 10)), 2),
        p25=round(float(np.percentile(arr, 25)), 2),
        p75=round(float(np.percentile(arr, 75)), 2),
        p90=round(float(np.percentile(arr, 90)), 2),
    )

    if min_val == max_val:
        return [
            ErrorDistributionBin(
                bin_start=min_val - 1.0,
                bin_end=max_val + 1.0,
                bin_center=min_val,
                count=len(errors),
                percentage=100.0,
            )
        ], stats

    if custom_bin_size and custom_bin_size > 0:
        bin_edges = np.arange(min_val, max_val + custom_bin_size, custom_bin_size)
    else:
        bin_edges = np.linspace(min_val, max_val, num_bins + 1)

    counts, edges = np.histogram(arr, bins=bin_edges)
    total = len(errors)

    bins: List[ErrorDistributionBin] = []
    for i in range(len(counts)):
        b_start = round(float(edges[i]), 2)
        b_end = round(float(edges[i + 1]), 2)
        b_center = round((b_start + b_end) / 2.0, 2)
        cnt = int(counts[i])
        pct = round((cnt / total) * 100.0, 2)
        bins.append(
            ErrorDistributionBin(
                bin_start=b_start,
                bin_end=b_end,
                bin_center=b_center,
                count=cnt,
                percentage=pct,
            )
        )

    return bins, stats


def get_error_distribution_and_observations(
    session: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    cutoff_hour: int = 15,
    cutoff_minute: int = 0,
    page: int = 1,
    limit: int = 100,
    bin_size: Optional[float] = None,
) -> ErrorObservationsResponse:
    """Get error histogram bins, percentiles, and paginated error observations."""
    records = _filter_records(
        session,
        start_time=start_time,
        end_time=end_time,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
    )
    errors = [r.forecast_error for r in records]

    bins, stats = compute_distribution_bins(errors, custom_bin_size=bin_size)

    total_count = len(records)
    total_pages = max(1, math.ceil(total_count / limit)) if limit > 0 else 1

    # Paginate
    offset = (page - 1) * limit
    page_records = records[offset : offset + limit]

    obs_points = [
        HourlyTimeseriesPoint(
            delivery_time=(
                r.delivery_time.replace(tzinfo=timezone.utc)
                if r.delivery_time.tzinfo is None
                else r.delivery_time.astimezone(timezone.utc)
            ),
            forecast_publish_time=(
                r.forecast_publish_time.replace(tzinfo=timezone.utc)
                if r.forecast_publish_time.tzinfo is None
                else r.forecast_publish_time.astimezone(timezone.utc)
            ),
            forecast_generation=float(r.forecast_generation),
            actual_generation=float(r.actual_generation),
            forecast_error=float(r.forecast_error),
            abs_error=round(abs(float(r.forecast_error)), 2),
            cutoff_time=(
                r.cutoff_time.replace(tzinfo=timezone.utc)
                if r.cutoff_time.tzinfo is None
                else r.cutoff_time.astimezone(timezone.utc)
            ),
        )
        for r in page_records
    ]

    return ErrorObservationsResponse(
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
        delivery_from=start_time,
        delivery_to=end_time,
        total_count=total_count,
        page=page,
        limit=limit,
        total_pages=total_pages,
        stats=stats,
        bins=bins,
        observations=obs_points,
    )


def get_top_errors(
    session: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    cutoff_hour: int = 15,
    cutoff_minute: int = 0,
    limit: int = 10,
    error_type: str = "absolute",
) -> TopErrorsResponse:
    """Retrieve the largest forecast errors ordered by absolute, overforecast, or underforecast magnitude."""
    records = _filter_records(
        session,
        start_time=start_time,
        end_time=end_time,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
    )

    if error_type == "overforecast":
        # Largest positive errors
        sorted_records = sorted(records, key=lambda r: r.forecast_error, reverse=True)
    elif error_type == "underforecast":
        # Largest negative errors (most negative first)
        sorted_records = sorted(records, key=lambda r: r.forecast_error)
    else:
        # Largest absolute error (default)
        sorted_records = sorted(
            records, key=lambda r: abs(r.forecast_error), reverse=True
        )

    top_n = sorted_records[:limit]

    top_records = [
        TopErrorRecord(
            rank=idx + 1,
            delivery_time=(
                r.delivery_time.replace(tzinfo=timezone.utc)
                if r.delivery_time.tzinfo is None
                else r.delivery_time.astimezone(timezone.utc)
            ),
            forecast_publish_time=(
                r.forecast_publish_time.replace(tzinfo=timezone.utc)
                if r.forecast_publish_time.tzinfo is None
                else r.forecast_publish_time.astimezone(timezone.utc)
            ),
            forecast_generation=float(r.forecast_generation),
            actual_generation=float(r.actual_generation),
            forecast_error=float(r.forecast_error),
            abs_error=round(abs(float(r.forecast_error)), 2),
            cutoff_time=(
                r.cutoff_time.replace(tzinfo=timezone.utc)
                if r.cutoff_time.tzinfo is None
                else r.cutoff_time.astimezone(timezone.utc)
            ),
        )
        for idx, r in enumerate(top_n)
    ]

    return TopErrorsResponse(
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
        delivery_from=start_time,
        delivery_to=end_time,
        error_type=error_type,
        total_evaluated_samples=len(records),
        top_errors=top_records,
    )

