from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.forecast import WindForecast
from app.services.cutoff import CutoffConfig, DEFAULT_CUTOFF_CONFIG, get_decision_cutoff

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SelectedForecast:
    """A selected forecast version for a single delivery hour."""

    delivery_time: datetime
    publish_time: datetime
    generation: float
    cutoff_time: datetime


@dataclass
class ForecastSelectionResult:
    """Result of the forecast selection process across a delivery range."""

    selected: Dict[datetime, SelectedForecast]
    missing_hours: List[datetime]
    total_evaluated_hours: int


def select_forecast_for_delivery_hour(
    delivery_hour: datetime,
    candidate_forecasts: Sequence[WindForecast],
    config: CutoffConfig = DEFAULT_CUTOFF_CONFIG,
) -> Optional[SelectedForecast]:
    """Select the latest forecast for a delivery hour published strictly before cutoff.

    Rule:
        publish_time < decision_cutoff
        Forecasts published at or after cutoff are strictly excluded.
    """
    if delivery_hour.tzinfo is None:
        delivery_hour = delivery_hour.replace(tzinfo=timezone.utc)
    else:
        delivery_hour = delivery_hour.astimezone(timezone.utc)

    cutoff = get_decision_cutoff(delivery_hour, config)

    # Filter candidate forecasts strictly before cutoff
    eligible: List[WindForecast] = [
        f
        for f in candidate_forecasts
        if (
            f.start_time.replace(tzinfo=timezone.utc)
            if f.start_time.tzinfo is None
            else f.start_time.astimezone(timezone.utc)
        )
        == delivery_hour
        and (
            f.publish_time.replace(tzinfo=timezone.utc)
            if f.publish_time.tzinfo is None
            else f.publish_time.astimezone(timezone.utc)
        )
        < cutoff
    ]

    if not eligible:
        return None

    # Pick latest publish_time
    latest = max(
        eligible,
        key=lambda f: (
            f.publish_time.replace(tzinfo=timezone.utc)
            if f.publish_time.tzinfo is None
            else f.publish_time.astimezone(timezone.utc)
        ),
    )

    pub_time = (
        latest.publish_time.replace(tzinfo=timezone.utc)
        if latest.publish_time.tzinfo is None
        else latest.publish_time.astimezone(timezone.utc)
    )

    return SelectedForecast(
        delivery_time=delivery_hour,
        publish_time=pub_time,
        generation=float(latest.generation),
        cutoff_time=cutoff,
    )


def select_forecasts(
    expected_delivery_hours: Sequence[datetime],
    all_forecasts: Sequence[WindForecast],
    config: CutoffConfig = DEFAULT_CUTOFF_CONFIG,
) -> ForecastSelectionResult:
    """Select the latest eligible forecast for each expected delivery hour in-memory."""
    # Group forecasts by normalized delivery hour
    by_hour: Dict[datetime, List[WindForecast]] = {}
    for f in all_forecasts:
        st = (
            f.start_time.replace(tzinfo=timezone.utc)
            if f.start_time.tzinfo is None
            else f.start_time.astimezone(timezone.utc)
        )
        by_hour.setdefault(st, []).append(f)

    selected: Dict[datetime, SelectedForecast] = {}
    missing_hours: List[datetime] = []

    for hour in expected_delivery_hours:
        norm_hour = (
            hour.replace(tzinfo=timezone.utc)
            if hour.tzinfo is None
            else hour.astimezone(timezone.utc)
        )
        candidates = by_hour.get(norm_hour, [])
        match = select_forecast_for_delivery_hour(norm_hour, candidates, config)
        if match is not None:
            selected[norm_hour] = match
        else:
            missing_hours.append(norm_hour)

    return ForecastSelectionResult(
        selected=selected,
        missing_hours=missing_hours,
        total_evaluated_hours=len(expected_delivery_hours),
    )


def select_forecasts_from_db(
    session: Session,
    start_delivery: datetime,
    end_delivery: datetime,
    config: CutoffConfig = DEFAULT_CUTOFF_CONFIG,
) -> ForecastSelectionResult:
    """Query database and select eligible forecasts for the delivery window [start_delivery, end_delivery]."""
    if start_delivery.tzinfo is None:
        start_delivery = start_delivery.replace(tzinfo=timezone.utc)
    else:
        start_delivery = start_delivery.astimezone(timezone.utc)

    if end_delivery.tzinfo is None:
        end_delivery = end_delivery.replace(tzinfo=timezone.utc)
    else:
        end_delivery = end_delivery.astimezone(timezone.utc)

    # Query all candidate forecasts for delivery window
    stmt = (
        select(WindForecast)
        .where(
            WindForecast.start_time >= start_delivery,
            WindForecast.start_time <= end_delivery,
        )
        .order_by(WindForecast.start_time, WindForecast.publish_time)
    )
    records = session.execute(stmt).scalars().all()

    # Generate expected delivery hours between start and end
    expected_hours: List[datetime] = []
    curr = start_delivery
    from datetime import timedelta

    while curr <= end_delivery:
        expected_hours.append(curr)
        curr += timedelta(hours=1)

    return select_forecasts(expected_hours, records, config)

