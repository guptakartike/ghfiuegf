from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

# Provisional operational day-ahead cutoff: 15:00 UK time on D-1.
# Note: As documented in PRD Section 6, this is a provisional operational
# parameter and must not be represented as a verified market gate-closure
# rule without supporting evidence and client confirmation.
DEFAULT_CUTOFF_HOUR = 15
DEFAULT_CUTOFF_MINUTE = 0
DEFAULT_CUTOFF_TIMEZONE = "Europe/London"
DEFAULT_DAYS_AHEAD = 1


@dataclass(frozen=True)
class CutoffConfig:
    """Configuration for decision cutoff calculation.

    Attributes:
        cutoff_hour: Hour of the day for cutoff (default: 15).
        cutoff_minute: Minute of the hour for cutoff (default: 0).
        timezone_name: Timezone identifier (default: "Europe/London").
        days_ahead: Number of days prior to delivery date for decision (default: 1 for D-1).
    """

    cutoff_hour: int = DEFAULT_CUTOFF_HOUR
    cutoff_minute: int = DEFAULT_CUTOFF_MINUTE
    timezone_name: str = DEFAULT_CUTOFF_TIMEZONE
    days_ahead: int = DEFAULT_DAYS_AHEAD

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)


DEFAULT_CUTOFF_CONFIG = CutoffConfig()


def get_decision_cutoff(
    delivery_time: datetime,
    config: CutoffConfig = DEFAULT_CUTOFF_CONFIG,
) -> datetime:
    """Calculate the decision cutoff timestamp in UTC for a given delivery time.

    For a delivery hour starting at `delivery_time` (UTC):
    1. Determine the UK market delivery date (Europe/London).
    2. Subtract `days_ahead` (default: 1 day for D-1) to determine the decision date.
    3. Construct the local cutoff timestamp (e.g., 15:00 Europe/London).
    4. Convert and return the cutoff as a timezone-aware UTC datetime.

    Strict Eligibility Rule:
        A forecast published at `publish_time` is eligible if and only if:
        publish_time < decision_cutoff
        (Forecasts published at or after the cutoff are strictly ineligible).
    """
    if delivery_time.tzinfo is None:
        delivery_time = delivery_time.replace(tzinfo=timezone.utc)
    else:
        delivery_time = delivery_time.astimezone(timezone.utc)

    # 1. Local delivery date in UK market time
    delivery_local = delivery_time.astimezone(config.tz)
    delivery_date: date = delivery_local.date()

    # 2. Decision date (D - days_ahead)
    decision_date: date = delivery_date - timedelta(days=config.days_ahead)

    # 3. Local cutoff timestamp
    cutoff_local = datetime.combine(
        decision_date,
        time(config.cutoff_hour, config.cutoff_minute),
        tzinfo=config.tz,
    )

    # 4. Normalized to UTC
    return cutoff_local.astimezone(timezone.utc)

