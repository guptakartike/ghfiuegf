from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional, Tuple

from pydantic import ValidationError

from app.ingestion.schemas import (
    FuelhhRecord,
    WindforRecord,
    _ensure_date,
    _ensure_utc_datetime,
)


def validate_windfor_record(
    record: dict[str, Any],
) -> Tuple[Optional[WindforRecord], List[str]]:
    """Validate a single WINDFOR record against the Pydantic schema.

    Parameters
    ----------
    record : dict[str, Any]
        Raw record dictionary from the API.

    Returns
    -------
    Tuple[Optional[WindforRecord], List[str]]
        Validated record (or None) and list of error messages.
    """
    if not isinstance(record, dict):
        return None, ["Record must be a dictionary"]

    # Validate required fields
    required = ["dataset", "generation"]
    errors: List[str] = []
    for f in required:
        if f not in record or record[f] is None:
            errors.append(f"Missing required field: {f}")

    has_publish = "publishTime" in record or "publish_time" in record
    if not has_publish or (record.get("publishTime") is None and record.get("publish_time") is None):
        errors.append("Missing required field: publishTime")

    has_start = "startTime" in record or "start_time" in record
    if not has_start or (record.get("startTime") is None and record.get("start_time") is None):
        errors.append("Missing required field: startTime")

    if errors:
        return None, errors

    try:
        validated = WindforRecord.model_validate(record)
        return validated, []
    except ValidationError as exc:
        return None, [f"{err['loc'][0]}: {err['msg']}" for err in exc.errors()]
    except Exception as exc:
        return None, [str(exc)]


def validate_fuelhh_record(
    record: dict[str, Any],
) -> Tuple[Optional[FuelhhRecord], List[str]]:
    """Validate a single FUELHH record against the Pydantic schema.

    Parameters
    ----------
    record : dict[str, Any]
        Raw record dictionary from the API.

    Returns
    -------
    Tuple[Optional[FuelhhRecord], List[str]]
        Validated record (or None) and list of error messages.
    """
    if not isinstance(record, dict):
        return None, ["Record must be a dictionary"]

    required = ["dataset", "generation", "fuelType", "settlementPeriod", "settlementDate"]
    errors: List[str] = []
    for f in required:
        alt = f
        if f == "fuelType":
            alt = "fuel_type"
        elif f == "settlementPeriod":
            alt = "settlement_period"
        elif f == "settlementDate":
            alt = "settlement_date"

        if (f not in record and alt not in record) or (record.get(f) is None and record.get(alt) is None):
            errors.append(f"Missing required field: {f}")

    has_publish = "publishTime" in record or "publish_time" in record
    if not has_publish or (record.get("publishTime") is None and record.get("publish_time") is None):
        errors.append("Missing required field: publishTime")

    has_start = "startTime" in record or "start_time" in record
    if not has_start or (record.get("startTime") is None and record.get("start_time") is None):
        errors.append("Missing required field: startTime")

    if errors:
        return None, errors

    try:
        validated = FuelhhRecord.model_validate(record)
        return validated, []
    except ValidationError as exc:
        return None, [f"{err['loc'][0]}: {err['msg']}" for err in exc.errors()]
    except Exception as exc:
        return None, [str(exc)]


def check_date_range(
    record_date: datetime,
    expected_start: datetime,
    expected_end: datetime,
    field_name: str,
) -> List[str]:
    """Check that a record's date falls within the expected range."""
    errors: List[str] = []
    if record_date.tzinfo is None:
        record_date = record_date.replace(tzinfo=timezone.utc)
    if expected_start.tzinfo is None:
        expected_start = expected_start.replace(tzinfo=timezone.utc)
    if expected_end.tzinfo is None:
        expected_end = expected_end.replace(tzinfo=timezone.utc)

    if record_date < expected_start:
        errors.append(
            f"{field_name} {record_date.isoformat()} is before expected start {expected_start.isoformat()}"
        )
    if record_date > expected_end:
        errors.append(
            f"{field_name} {record_date.isoformat()} is after expected end {expected_end.isoformat()}"
        )
    return errors


def has_sufficient_resolution(
    record: dict[str, Any],
    dataset_type: str,
) -> Tuple[bool, List[str]]:
    """Check that the record has the expected delivery resolution.

    - WINDFOR: hourly delivery resolution (start_time minute and second == 0).
    - FUELHH: half-hourly resolution (settlement_period 1..48).
    """
    errors: List[str] = []

    if dataset_type == "forecast":
        raw_start = record.get("startTime") or record.get("start_time")
        if raw_start is not None:
            try:
                dt = _ensure_utc_datetime(raw_start)
                if dt.minute != 0 or dt.second != 0:
                    errors.append(
                        "WINDFOR startTime should be on the hour for hourly resolution"
                    )
            except Exception:
                errors.append("Failed to parse WINDFOR startTime")
    elif dataset_type == "actual":
        sp = record.get("settlementPeriod") or record.get("settlement_period")
        if sp is not None:
            try:
                sp_int = int(sp)
                if sp_int < 1 or sp_int > 48:
                    errors.append(
                        "FUELHH settlementPeriod must be 1-48 for 30-min resolution"
                    )
            except Exception:
                errors.append("Failed to parse FUELHH settlementPeriod")

    return len(errors) == 0, errors


def detect_missing_actual_intervals(
    valid_records: list[FuelhhRecord],
    start_date: date,
    end_date: date,
) -> int:
    """Detect missing half-hourly intervals for FUELHH actuals within the requested date range.

    Parameters
    ----------
    valid_records : list[FuelhhRecord]
        List of validated FUELHH records.
    start_date : date
        Start date (inclusive).
    end_date : date
        End date (inclusive).

    Returns
    -------
    int
        Number of missing settlement periods.
    """
    if start_date > end_date:
        return 0

    total_days = (end_date - start_date).days + 1
    expected_total = total_days * 48

    observed_intervals = set()
    for r in valid_records:
        if start_date <= r.settlement_date <= end_date:
            observed_intervals.add((r.settlement_date, r.settlement_period))

    return max(0, expected_total - len(observed_intervals))


def detect_missing_forecast_intervals(
    valid_records: list[WindforRecord],
    start_time: datetime,
    end_time: datetime,
) -> int:
    """Detect missing hourly delivery intervals for WINDFOR forecasts.

    Counts distinct hourly start_time delivery values observed within [start_time, end_time].
    """
    if start_time > end_time:
        return 0

    cur = start_time.replace(minute=0, second=0, microsecond=0)
    expected_hours = 0
    expected_set = set()
    while cur <= end_time:
        expected_set.add(cur)
        cur += timedelta(hours=1)
        expected_hours += 1

    observed_delivery_hours = {
        r.start_time.replace(minute=0, second=0, microsecond=0)
        for r in valid_records
        if start_time <= r.start_time <= end_time
    }

    return max(0, len(expected_set - observed_delivery_hours))
