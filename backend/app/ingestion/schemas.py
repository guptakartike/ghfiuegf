from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _ensure_utc_datetime(v: Any) -> datetime:
    """Normalize input value to a timezone-aware UTC datetime."""
    if isinstance(v, str):
        dt = datetime.fromisoformat(v)
    elif isinstance(v, datetime):
        dt = v
    else:
        raise ValueError(f"Cannot parse {v!r} as datetime")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _ensure_date(v: Any) -> date:
    """Normalize input value to a date object."""
    if isinstance(v, str):
        return date.fromisoformat(v)
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    raise ValueError(f"Cannot parse {v!r} as date")


class WindforRecord(BaseModel):
    """Pydantic schema for a single WINDFOR dataset record."""

    dataset: str = "WINDFOR"
    publish_time: datetime = Field(..., alias="publishTime")
    start_time: datetime = Field(..., alias="startTime")
    generation: float = Field(..., alias="generation")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("publish_time", "start_time", mode="before")
    @classmethod
    def validate_timestamps(cls, v: Any) -> datetime:
        return _ensure_utc_datetime(v)

    @field_validator("generation")
    @classmethod
    def validate_generation(cls, v: float) -> float:
        if v < 0:
            raise ValueError("WINDFOR generation must be non-negative")
        return v


class FuelhhRecord(BaseModel):
    """Pydantic schema for a single FUELHH dataset record."""

    dataset: str = "FUELHH"
    publish_time: datetime = Field(..., alias="publishTime")
    start_time: datetime = Field(..., alias="startTime")
    settlement_date: date = Field(..., alias="settlementDate")
    settlement_period: int = Field(..., alias="settlementPeriod")
    fuel_type: str = Field(..., alias="fuelType")
    generation: float = Field(..., alias="generation")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("publish_time", "start_time", mode="before")
    @classmethod
    def validate_timestamps(cls, v: Any) -> datetime:
        return _ensure_utc_datetime(v)

    @field_validator("settlement_date", mode="before")
    @classmethod
    def validate_settlement_date(cls, v: Any) -> date:
        return _ensure_date(v)

    @field_validator("fuel_type")
    @classmethod
    def validate_fuel_type(cls, v: str) -> str:
        if str(v).upper() != "WIND":
            raise ValueError("FUELHH fuelType must be WIND")
        return str(v).upper()

    @field_validator("settlement_period")
    @classmethod
    def validate_settlement_period(cls, v: int) -> int:
        if v < 1 or v > 48:
            raise ValueError("FUELHH settlementPeriod must be 1-48 (30-min intervals per day)")
        return v

    @field_validator("generation")
    @classmethod
    def validate_generation(cls, v: float) -> float:
        if v < 0:
            raise ValueError("FUELHH generation must be non-negative")
        return v


class IngestionReport(BaseModel):
    """Pydantic schema for an ingestion report."""

    source_dataset: str
    requested_date_range: str
    retrieved_record_count: int = 0
    valid_record_count: int = 0
    inserted_record_count: int = 0
    skipped_duplicate_count: int = 0
    invalid_record_count: int = 0
    missing_interval_count: int = 0
    earliest_timestamp: Optional[datetime] = None
    latest_timestamp: Optional[datetime] = None
    ingestion_status: str = "pending"

    model_config = ConfigDict(populate_by_name=True)
