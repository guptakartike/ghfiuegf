from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.actual import ActualGeneration

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AggregatedActual:
    """Hourly aggregated actual generation for a single delivery hour."""

    delivery_time: datetime
    generation: float  # Arithmetic mean of the two half-hourly observations (MW)
    interval_00_generation: float
    interval_30_generation: float
    observation_count: int = 2


@dataclass
class IncompleteHourReport:
    """Details of a delivery hour that lacked exactly two valid half-hourly observations."""

    delivery_time: datetime
    observation_count: int
    has_minute_00: bool
    has_minute_30: bool
    reason: str


@dataclass
class ActualAggregationResult:
    """Result of actual generation aggregation across a delivery range."""

    aggregated: Dict[datetime, AggregatedActual]
    incomplete_hours: List[IncompleteHourReport]
    total_evaluated_hours: int


def aggregate_actuals_for_hour(
    delivery_hour: datetime,
    hour_observations: Sequence[ActualGeneration],
) -> tuple[Optional[AggregatedActual], Optional[IncompleteHourReport]]:
    """Aggregate half-hourly observations for a single delivery hour.

    Rules:
    - Arithmetic mean: (gen_00 + gen_30) / 2.0.
    - NEVER sum MW values.
    - Require exactly two valid observations: one at minute 0 and one at minute 30.
    - Never replace missing values with zero.
    """
    if delivery_hour.tzinfo is None:
        delivery_hour = delivery_hour.replace(tzinfo=timezone.utc)
    else:
        delivery_hour = delivery_hour.astimezone(timezone.utc)

    int_00 = delivery_hour
    int_30 = delivery_hour + timedelta(minutes=30)

    obs_00: List[ActualGeneration] = []
    obs_30: List[ActualGeneration] = []

    for obs in hour_observations:
        st = (
            obs.start_time.replace(tzinfo=timezone.utc)
            if obs.start_time.tzinfo is None
            else obs.start_time.astimezone(timezone.utc)
        )
        if st == int_00:
            obs_00.append(obs)
        elif st == int_30:
            obs_30.append(obs)

    has_00 = len(obs_00) == 1
    has_30 = len(obs_30) == 1

    if has_00 and has_30 and len(hour_observations) == 2:
        g0 = float(obs_00[0].generation)
        g30 = float(obs_30[0].generation)
        avg_mw = (g0 + g30) / 2.0
        return (
            AggregatedActual(
                delivery_time=delivery_hour,
                generation=avg_mw,
                interval_00_generation=g0,
                interval_30_generation=g30,
            ),
            None,
        )

    # Incomplete or irregular hour
    reasons: List[str] = []
    if len(obs_00) == 0:
        reasons.append("Missing minute :00 observation")
    elif len(obs_00) > 1:
        reasons.append(f"Duplicate minute :00 observations (count={len(obs_00)})")

    if len(obs_30) == 0:
        reasons.append("Missing minute :30 observation")
    elif len(obs_30) > 1:
        reasons.append(f"Duplicate minute :30 observations (count={len(obs_30)})")

    report = IncompleteHourReport(
        delivery_time=delivery_hour,
        observation_count=len(hour_observations),
        has_minute_00=has_00,
        has_minute_30=has_30,
        reason="; ".join(reasons) if reasons else f"Unexpected observation count: {len(hour_observations)}",
    )
    return None, report


def aggregate_actuals(
    expected_delivery_hours: Sequence[datetime],
    all_actuals: Sequence[ActualGeneration],
) -> ActualAggregationResult:
    """Aggregate half-hourly actuals for all expected delivery hours in-memory."""
    by_hour: Dict[datetime, List[ActualGeneration]] = {}
    for obs in all_actuals:
        st = (
            obs.start_time.replace(tzinfo=timezone.utc)
            if obs.start_time.tzinfo is None
            else obs.start_time.astimezone(timezone.utc)
        )
        hour = st.replace(minute=0, second=0, microsecond=0)
        by_hour.setdefault(hour, []).append(obs)

    aggregated: Dict[datetime, AggregatedActual] = {}
    incomplete_hours: List[IncompleteHourReport] = []

    for hour in expected_delivery_hours:
        norm_hour = (
            hour.replace(tzinfo=timezone.utc)
            if hour.tzinfo is None
            else hour.astimezone(timezone.utc)
        )
        candidates = by_hour.get(norm_hour, [])
        agg, report = aggregate_actuals_for_hour(norm_hour, candidates)
        if agg is not None:
            aggregated[norm_hour] = agg
        elif report is not None:
            incomplete_hours.append(report)

    return ActualAggregationResult(
        aggregated=aggregated,
        incomplete_hours=incomplete_hours,
        total_evaluated_hours=len(expected_delivery_hours),
    )


def aggregate_actuals_from_db(
    session: Session,
    start_delivery: datetime,
    end_delivery: datetime,
) -> ActualAggregationResult:
    """Query database and aggregate actuals for the delivery window [start_delivery, end_delivery]."""
    if start_delivery.tzinfo is None:
        start_delivery = start_delivery.replace(tzinfo=timezone.utc)
    else:
        start_delivery = start_delivery.astimezone(timezone.utc)

    if end_delivery.tzinfo is None:
        end_delivery = end_delivery.replace(tzinfo=timezone.utc)
    else:
        end_delivery = end_delivery.astimezone(timezone.utc)

    # Cover full hour of end_delivery (up to end_delivery:30)
    query_end = end_delivery + timedelta(minutes=30)

    stmt = (
        select(ActualGeneration)
        .where(
            ActualGeneration.start_time >= start_delivery,
            ActualGeneration.start_time <= query_end,
        )
        .order_by(ActualGeneration.start_time)
    )
    records = session.execute(stmt).scalars().all()

    expected_hours: List[datetime] = []
    curr = start_delivery
    while curr <= end_delivery:
        expected_hours.append(curr)
        curr += timedelta(hours=1)

    return aggregate_actuals(expected_hours, records)

