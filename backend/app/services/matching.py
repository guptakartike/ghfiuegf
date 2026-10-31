from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import sys
from typing import Dict, List, Optional, Sequence

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.matched_observation import MatchedHourlyObservation
from app.services.actual_aggregation import (
    ActualAggregationResult,
    AggregatedActual,
    IncompleteHourReport,
    aggregate_actuals,
    aggregate_actuals_from_db,
)
from app.services.cutoff import CutoffConfig, DEFAULT_CUTOFF_CONFIG
from app.services.forecast_selection import (
    ForecastSelectionResult,
    SelectedForecast,
    select_forecasts,
    select_forecasts_from_db,
)

logger = logging.getLogger(__name__)

DEFAULT_DELIVERY_FROM = datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
DEFAULT_DELIVERY_TO = datetime(2026, 2, 1, 23, 0, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class MatchedRecord:
    """In-memory representation of a matched observation."""

    delivery_time: datetime
    forecast_publish_time: datetime
    forecast_generation: float
    actual_generation: float
    forecast_error: float
    cutoff_time: datetime


@dataclass
class MatchingResult:
    """Result of the forecast-actual matching process."""

    matched: List[MatchedRecord]
    unmatched_forecasts: List[datetime]  # Eligible forecast exists, but actual missing/incomplete
    unmatched_actuals: List[datetime]    # Aggregated actual exists, but no eligible forecast
    missing_both: List[datetime]         # Neither eligible forecast nor complete actual
    incomplete_actual_reports: List[IncompleteHourReport]
    total_evaluated_hours: int

    @property
    def matched_count(self) -> int:
        return len(self.matched)

    @property
    def unmatched_count(self) -> int:
        return len(self.unmatched_forecasts) + len(self.unmatched_actuals) + len(self.missing_both)


def match_forecasts_and_actuals(
    expected_delivery_hours: Sequence[datetime],
    selected_forecasts: Dict[datetime, SelectedForecast],
    aggregated_actuals: Dict[datetime, AggregatedActual],
    incomplete_actual_reports: Optional[List[IncompleteHourReport]] = None,
) -> MatchingResult:
    """Match selected forecasts and aggregated actuals by delivery hour.

    Error formula:
        forecast_error = forecast_generation - actual_generation
        Positive = overforecast
        Negative = underforecast
    """
    matched: List[MatchedRecord] = []
    unmatched_forecasts: List[datetime] = []
    unmatched_actuals: List[datetime] = []
    missing_both: List[datetime] = []

    for hour in expected_delivery_hours:
        norm_hour = (
            hour.replace(tzinfo=timezone.utc)
            if hour.tzinfo is None
            else hour.astimezone(timezone.utc)
        )

        fc = selected_forecasts.get(norm_hour)
        act = aggregated_actuals.get(norm_hour)

        if fc is not None and act is not None:
            # Calculate forecast error
            error = fc.generation - act.generation
            matched.append(
                MatchedRecord(
                    delivery_time=norm_hour,
                    forecast_publish_time=fc.publish_time,
                    forecast_generation=fc.generation,
                    actual_generation=act.generation,
                    forecast_error=error,
                    cutoff_time=fc.cutoff_time,
                )
            )
        elif fc is not None and act is None:
            unmatched_forecasts.append(norm_hour)
        elif fc is None and act is not None:
            unmatched_actuals.append(norm_hour)
        else:
            missing_both.append(norm_hour)

    return MatchingResult(
        matched=matched,
        unmatched_forecasts=unmatched_forecasts,
        unmatched_actuals=unmatched_actuals,
        missing_both=missing_both,
        incomplete_actual_reports=incomplete_actual_reports or [],
        total_evaluated_hours=len(expected_delivery_hours),
    )


def persist_matched_records(
    session: Session,
    matched_records: Sequence[MatchedRecord],
) -> int:
    """Persist matched records to the database with idempotent UPSERT.

    Returns the number of rows inserted or updated.
    """
    if not matched_records:
        return 0

    values = [
        {
            "delivery_time": r.delivery_time,
            "forecast_publish_time": r.forecast_publish_time,
            "forecast_generation": r.forecast_generation,
            "actual_generation": r.actual_generation,
            "forecast_error": r.forecast_error,
            "cutoff_time": r.cutoff_time,
        }
        for r in matched_records
    ]

    bind = session.get_bind()
    dialect_name = bind.dialect.name if bind else "postgresql"

    table = MatchedHourlyObservation.__table__

    if dialect_name == "sqlite":
        stmt = sqlite_insert(table).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["delivery_time", "cutoff_time"],
            set_={
                "forecast_publish_time": stmt.excluded.forecast_publish_time,
                "forecast_generation": stmt.excluded.forecast_generation,
                "actual_generation": stmt.excluded.actual_generation,
                "forecast_error": stmt.excluded.forecast_error,
            },
        )
    else:
        stmt = pg_insert(table).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_matched_delivery_cutoff",
            set_={
                "forecast_publish_time": stmt.excluded.forecast_publish_time,
                "forecast_generation": stmt.excluded.forecast_generation,
                "actual_generation": stmt.excluded.actual_generation,
                "forecast_error": stmt.excluded.forecast_error,
            },
        )

    result = session.execute(stmt)
    session.commit()
    return len(values)


def run_matching_pipeline(
    session: Session,
    start_delivery: datetime = DEFAULT_DELIVERY_FROM,
    end_delivery: datetime = DEFAULT_DELIVERY_TO,
    config: CutoffConfig = DEFAULT_CUTOFF_CONFIG,
    persist: bool = True,
) -> MatchingResult:
    """Execute complete Phase 2 analytics matching pipeline for delivery window."""
    if start_delivery.tzinfo is None:
        start_delivery = start_delivery.replace(tzinfo=timezone.utc)
    else:
        start_delivery = start_delivery.astimezone(timezone.utc)

    if end_delivery.tzinfo is None:
        end_delivery = end_delivery.replace(tzinfo=timezone.utc)
    else:
        end_delivery = end_delivery.astimezone(timezone.utc)

    # 1. Select eligible forecasts
    forecast_result: ForecastSelectionResult = select_forecasts_from_db(
        session=session,
        start_delivery=start_delivery,
        end_delivery=end_delivery,
        config=config,
    )

    # 2. Aggregate half-hourly actuals
    actual_result: ActualAggregationResult = aggregate_actuals_from_db(
        session=session,
        start_delivery=start_delivery,
        end_delivery=end_delivery,
    )

    # 3. Build expected hours
    expected_hours: List[datetime] = []
    curr = start_delivery
    while curr <= end_delivery:
        expected_hours.append(curr)
        curr += timedelta(hours=1)

    # 4. Match
    matching_result = match_forecasts_and_actuals(
        expected_delivery_hours=expected_hours,
        selected_forecasts=forecast_result.selected,
        aggregated_actuals=actual_result.aggregated,
        incomplete_actual_reports=actual_result.incomplete_hours,
    )

    if matching_result.unmatched_count > 0:
        logger.warning(
            "Found %d unmatched hours: %d forecasts without actuals, %d actuals without forecasts, %d missing both",
            matching_result.unmatched_count,
            len(matching_result.unmatched_forecasts),
            len(matching_result.unmatched_actuals),
            len(matching_result.missing_both),
        )
    else:
        logger.info(
            "Successfully matched all %d delivery hours with zero unmatched records",
            matching_result.matched_count,
        )

    # 5. Persist
    if persist and matching_result.matched:
        persist_matched_records(session, matching_result.matched)

    return matching_result


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Wind Analytics Forecast-Actual Matching Pipeline")
    parser.add_argument(
        "--delivery-from",
        type=lambda v: datetime.fromisoformat(
            v.replace("Z", "+00:00") if "T" in v else f"{v}T00:00:00+00:00"
        ),
        default=DEFAULT_DELIVERY_FROM,
        help="Start delivery timestamp (ISO 8601, default: 2026-01-02T00:00:00Z)",
    )
    parser.add_argument(
        "--delivery-to",
        type=lambda v: datetime.fromisoformat(
            v.replace("Z", "+00:00") if "T" in v else f"{v}T23:00:00+00:00"
        ),
        default=DEFAULT_DELIVERY_TO,
        help="End delivery timestamp (ISO 8601, default: 2026-02-01T23:00:00Z)",
    )
    parser.add_argument(
        "--cutoff-hour",
        type=int,
        default=DEFAULT_CUTOFF_CONFIG.cutoff_hour,
        help="Decision cutoff hour (default: 15)",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()

    config = CutoffConfig(cutoff_hour=args.cutoff_hour)

    session = SessionLocal()
    try:
        result = run_matching_pipeline(
            session=session,
            start_delivery=args.delivery_from,
            end_delivery=args.delivery_to,
            config=config,
            persist=True,
        )
    finally:
        session.close()

    print("\n=== Forecast-Actual Matching Report ===")
    print(f"Delivery window: {args.delivery_from.isoformat()} to {args.delivery_to.isoformat()}")
    print(f"Decision cutoff rule: {config.cutoff_hour}:00 {config.timezone_name} on D-{config.days_ahead} (PROVISIONAL)")
    print(f"Total evaluated hours: {result.total_evaluated_hours}")
    print(f"Matched observations: {result.matched_count}")
    print(f"Unmatched forecasts: {len(result.unmatched_forecasts)}")
    print(f"Unmatched actuals: {len(result.unmatched_actuals)}")
    print(f"Missing both: {len(result.missing_both)}")
    print(f"Incomplete actual hours: {len(result.incomplete_actual_reports)}")
    print("=======================================\n")


if __name__ == "__main__":
    main()
