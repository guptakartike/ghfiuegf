from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
import pytest
from unittest.mock import AsyncMock, patch

from app.ingestion.actual_ingestion import (
    _ingest_actuals,
    ingest_actuals,
)
from app.ingestion.persistence import get_actual_count
from app.ingestion.schemas import FuelhhRecord
from app.ingestion.validation import validate_fuelhh_record
from app.models.actual import ActualGeneration


class TestActualValidation:
    """Unit tests for FUELHH validation logic."""

    def test_validation_success(self, sample_fuelhh_record) -> None:
        validated, errors = validate_fuelhh_record(sample_fuelhh_record)
        assert errors == []
        assert validated is not None
        assert validated.fuel_type == "WIND"
        assert validated.settlement_date == date(2026, 1, 2)
        assert validated.settlement_period == 1
        assert validated.start_time.tzinfo == timezone.utc

    def test_validation_invalid_fuel_type(self, sample_fuelhh_invalid_fuel) -> None:
        validated, errors = validate_fuelhh_record(sample_fuelhh_invalid_fuel)
        assert validated is None
        assert any("fuelType" in e for e in errors)

    def test_validation_invalid_period(self, sample_fuelhh_invalid_period) -> None:
        validated, errors = validate_fuelhh_record(sample_fuelhh_invalid_period)
        assert validated is None
        assert any("settlementPeriod" in e for e in errors)


class TestActualIngestionPipeline:
    """End-to-end tests that actually execute the FUELHH ingestion pipeline."""

    def test_successful_ingestion_end_to_end(self, test_db_session) -> None:
        """Test complete actuals ingestion execution with real DB persistence."""
        sample_api_records = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-02T00:30:00Z",
                "startTime": "2026-01-02T00:00:00Z",
                "settlementDate": "2026-01-02",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 1200.0,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-02T01:00:00Z",
                "startTime": "2026-01-02T00:30:00Z",
                "settlementDate": "2026-01-02",
                "settlementPeriod": 2,
                "fuelType": "WIND",
                "generation": 1150.0,
            },
        ]

        with patch(
            "app.ingestion.actual_ingestion.get_fuelhh_records",
            new=AsyncMock(return_value=sample_api_records),
        ):
            report = asyncio.run(_ingest_actuals(
                settlement_from="2026-01-02",
                settlement_to="2026-01-02",
                fuel_type="WIND",
                session=test_db_session,
            ))

        assert report.ingestion_status == "completed"
        assert report.retrieved_record_count == 2
        assert report.valid_record_count == 2
        assert report.inserted_record_count == 2
        assert report.skipped_duplicate_count == 0
        assert report.invalid_record_count == 0
        # 48 periods in 1 day; 2 retrieved -> 46 missing
        assert report.missing_interval_count == 46

        # Assert records actually exist in database
        count = test_db_session.query(ActualGeneration).count()
        assert count == 2

    def test_duplicate_ingestion_idempotency(self, test_db_session) -> None:
        """Test that running ingestion twice inserts records on first run and skips on second."""
        sample_api_records = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-02T00:30:00Z",
                "startTime": "2026-01-02T00:00:00Z",
                "settlementDate": "2026-01-02",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 1200.0,
            }
        ]

        with patch(
            "app.ingestion.actual_ingestion.get_fuelhh_records",
            new=AsyncMock(return_value=sample_api_records),
        ):
            # First execution
            report1 = asyncio.run(_ingest_actuals(
                settlement_from="2026-01-02",
                settlement_to="2026-01-02",
                fuel_type="WIND",
                session=test_db_session,
            ))
            assert report1.inserted_record_count == 1
            assert report1.skipped_duplicate_count == 0

            # Second execution with identical record
            report2 = asyncio.run(_ingest_actuals(
                settlement_from="2026-01-02",
                settlement_to="2026-01-02",
                fuel_type="WIND",
                session=test_db_session,
            ))
            assert report2.inserted_record_count == 0
            assert report2.skipped_duplicate_count == 1

        assert test_db_session.query(ActualGeneration).count() == 1

    def test_fuel_type_strictly_filtered(self, test_db_session) -> None:
        """Test that records with fuelType != WIND are rejected and excluded from insertion."""
        mixed_records = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-02T00:30:00Z",
                "startTime": "2026-01-02T00:00:00Z",
                "settlementDate": "2026-01-02",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 1200.0,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-02T00:30:00Z",
                "startTime": "2026-01-02T00:00:00Z",
                "settlementDate": "2026-01-02",
                "settlementPeriod": 1,
                "fuelType": "GAS",  # Non-WIND
                "generation": 4500.0,
            },
        ]

        with patch(
            "app.ingestion.actual_ingestion.get_fuelhh_records",
            new=AsyncMock(return_value=mixed_records),
        ):
            report = asyncio.run(_ingest_actuals(
                settlement_from="2026-01-02",
                settlement_to="2026-01-02",
                fuel_type="WIND",
                session=test_db_session,
            ))

        assert report.retrieved_record_count == 2
        assert report.valid_record_count == 1
        assert report.invalid_record_count == 1
        assert report.inserted_record_count == 1
        assert test_db_session.query(ActualGeneration).count() == 1

    def test_empty_api_response(self, test_db_session) -> None:
        """Test graceful handling of empty actuals response."""
        with patch(
            "app.ingestion.actual_ingestion.get_fuelhh_records",
            new=AsyncMock(return_value=[]),
        ):
            report = asyncio.run(_ingest_actuals(
                settlement_from="2026-01-02",
                settlement_to="2026-01-02",
                fuel_type="WIND",
                session=test_db_session,
            ))

        assert report.retrieved_record_count == 0
        assert report.inserted_record_count == 0
        assert report.ingestion_status == "completed"

    def test_sync_ingest_actuals_wrapper(self, test_db_session) -> None:
        """Test the synchronous ingest_actuals wrapper function."""
        sample_api_records = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-02T00:30:00Z",
                "startTime": "2026-01-02T00:00:00Z",
                "settlementDate": "2026-01-02",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 950.0,
            }
        ]

        with patch(
            "app.ingestion.actual_ingestion.get_fuelhh_records",
            new=AsyncMock(return_value=sample_api_records),
        ):
            report = ingest_actuals(
                settlement_from="2026-01-02",
                settlement_to="2026-01-02",
                fuel_type="WIND",
                session=test_db_session,
            )

        assert report.inserted_record_count == 1
        assert test_db_session.query(ActualGeneration).count() == 1
