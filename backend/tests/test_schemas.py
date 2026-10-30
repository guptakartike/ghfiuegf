from __future__ import annotations

from datetime import date, datetime, timezone
import pytest

from app.ingestion.schemas import FuelhhRecord, WindforRecord


class TestWindforRecord:
    """Test WINDFOR Pydantic schema validation."""

    def test_valid_windfor_record_camel_case(self) -> None:
        """Test that a valid WINDFOR record with API camelCase passes validation."""
        record = {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T12:00:00Z",
            "startTime": "2026-01-02T00:00:00Z",
            "generation": 1250.5,
        }
        validated = WindforRecord.model_validate(record)
        assert validated.dataset == "WINDFOR"
        assert validated.generation == 1250.5
        assert validated.publish_time == datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert validated.start_time == datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc)

    def test_valid_windfor_with_naive_datetimes(self) -> None:
        """Test WINDFOR record with naive datetime strings is normalized to UTC."""
        record = {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T12:00:00",
            "startTime": "2026-01-02T00:00:00",
            "generation": 1100.0,
        }
        validated = WindforRecord.model_validate(record)
        assert validated.publish_time.tzinfo == timezone.utc
        assert validated.start_time.tzinfo == timezone.utc
        assert validated.publish_time.hour == 12

    def test_negative_generation_rejected(self) -> None:
        """Test that negative generation values are rejected."""
        record = {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T12:00:00Z",
            "startTime": "2026-01-02T00:00:00Z",
            "generation": -50.0,
        }
        with pytest.raises(ValueError, match="must be non-negative"):
            WindforRecord.model_validate(record)

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields are detected."""
        record = {"dataset": "WINDFOR", "generation": 100.0}
        with pytest.raises(ValueError):
            WindforRecord.model_validate(record)

    def test_generation_zero_accepted(self) -> None:
        """Test that zero generation is accepted."""
        record = {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T12:00:00Z",
            "startTime": "2026-01-02T00:00:00Z",
            "generation": 0.0,
        }
        validated = WindforRecord.model_validate(record)
        assert validated.generation == 0.0


class TestFuelhhRecord:
    """Test FUELHH Pydantic schema validation."""

    def test_valid_fuelhh_record(self) -> None:
        """Test that a valid FUELHH record passes validation and normalizes date."""
        record = {
            "dataset": "FUELHH",
            "publishTime": "2026-01-02T00:30:00Z",
            "startTime": "2026-01-02T00:00:00Z",
            "settlementDate": "2026-01-02",
            "settlementPeriod": 1,
            "fuelType": "WIND",
            "generation": 1200.0,
        }
        validated = FuelhhRecord.model_validate(record)
        assert validated.dataset == "FUELHH"
        assert validated.fuel_type == "WIND"
        assert validated.generation == 1200.0
        assert validated.settlement_period == 1
        assert validated.settlement_date == date(2026, 1, 2)
        assert validated.start_time.tzinfo == timezone.utc

    def test_invalid_fuel_type_rejected(self) -> None:
        """Test that non-WIND fuel types are rejected."""
        record = {
            "dataset": "FUELHH",
            "publishTime": "2026-01-02T00:30:00Z",
            "startTime": "2026-01-02T00:00:00Z",
            "settlementDate": "2026-01-02",
            "settlementPeriod": 1,
            "fuelType": "GAS",
            "generation": 500.0,
        }
        with pytest.raises(ValueError, match="must be WIND"):
            FuelhhRecord.model_validate(record)

    def test_invalid_settlement_period_rejected(self) -> None:
        """Test that settlement periods outside 1-48 are rejected."""
        record = {
            "dataset": "FUELHH",
            "publishTime": "2026-01-02T00:30:00Z",
            "startTime": "2026-01-02T00:00:00Z",
            "settlementDate": "2026-01-02",
            "settlementPeriod": 50,
            "fuelType": "WIND",
            "generation": 500.0,
        }
        with pytest.raises(ValueError, match="must be 1-48"):
            FuelhhRecord.model_validate(record)

    def test_negative_generation_rejected_fuelhh(self) -> None:
        """Test that negative generation values are rejected in FUELHH."""
        record = {
            "dataset": "FUELHH",
            "publishTime": "2026-01-02T00:30:00Z",
            "startTime": "2026-01-02T00:00:00Z",
            "settlementDate": "2026-01-02",
            "settlementPeriod": 1,
            "fuelType": "WIND",
            "generation": -100.0,
        }
        with pytest.raises(ValueError, match="must be non-negative"):
            FuelhhRecord.model_validate(record)

    def test_settlement_period_boundary_1_and_48(self) -> None:
        """Test boundary settlement periods 1 and 48."""
        for p in (1, 48):
            record = {
                "dataset": "FUELHH",
                "publishTime": "2026-01-02T00:30:00Z",
                "startTime": "2026-01-02T00:00:00Z",
                "settlementDate": "2026-01-02",
                "settlementPeriod": p,
                "fuelType": "WIND",
                "generation": 500.0,
            }
            validated = FuelhhRecord.model_validate(record)
            assert validated.settlement_period == p


class TestResolutionAndMissingIntervals:
    """Test resolution checks and missing-interval calculations."""

    def test_forecast_resolution_checks(self) -> None:
        from app.ingestion.validation import has_sufficient_resolution

        ok, _ = has_sufficient_resolution({"startTime": "2026-01-02T00:00:00Z"}, "forecast")
        assert ok is True

        bad, errors = has_sufficient_resolution({"startTime": "2026-01-02T00:30:00Z"}, "forecast")
        assert bad is False
        assert any("on the hour" in e for e in errors)

    def test_actual_resolution_checks(self) -> None:
        from app.ingestion.validation import has_sufficient_resolution

        ok, _ = has_sufficient_resolution({"settlementPeriod": 1}, "actual")
        assert ok is True

        bad, errors = has_sufficient_resolution({"settlementPeriod": 49}, "actual")
        assert bad is False

    def test_detect_missing_actual_intervals(self) -> None:
        from app.ingestion.validation import detect_missing_actual_intervals

        records = [
            FuelhhRecord(
                dataset="FUELHH",
                publishTime="2026-01-02T00:30:00Z",
                startTime="2026-01-02T00:00:00Z",
                settlementDate="2026-01-02",
                settlementPeriod=1,
                fuelType="WIND",
                generation=100.0,
            ),
            FuelhhRecord(
                dataset="FUELHH",
                publishTime="2026-01-02T01:00:00Z",
                startTime="2026-01-02T00:30:00Z",
                settlementDate="2026-01-02",
                settlementPeriod=2,
                fuelType="WIND",
                generation=100.0,
            ),
        ]
        missing = detect_missing_actual_intervals(records, date(2026, 1, 2), date(2026, 1, 2))
        assert missing == 46
