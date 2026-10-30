from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, patch

from app.ingestion.forecast_ingestion import (
    _ingest_forecasts,
    ingest_forecasts,
)
from app.ingestion.persistence import get_forecast_count
from app.ingestion.schemas import WindforRecord
from app.ingestion.validation import validate_windfor_record
from app.models.forecast import WindForecast


class TestForecastValidation:
    """Unit tests for WINDFOR validation logic."""

    def test_validation_success(self, sample_windfor_record) -> None:
        validated, errors = validate_windfor_record(sample_windfor_record)
        assert errors == []
        assert validated is not None
        assert validated.publish_time.year == 2026
        assert validated.start_time.year == 2026
        assert validated.publish_time.tzinfo == timezone.utc

    def test_validation_invalid_generation(self, sample_windfor_invalid) -> None:
        validated, errors = validate_windfor_record(sample_windfor_invalid)
        assert validated is None
        assert len(errors) > 0


class TestForecastIngestionPipeline:
    """End-to-end tests that actually execute the WINDFOR ingestion pipeline."""

    def test_successful_ingestion_end_to_end(self, test_db_session) -> None:
        """Test complete forecast ingestion execution with real DB persistence."""
        sample_api_records = [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T12:00:00Z",
                "startTime": "2026-01-02T00:00:00Z",
                "generation": 1250.5,
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T12:00:00Z",
                "startTime": "2026-01-02T01:00:00Z",
                "generation": 1300.0,
            },
        ]

        with patch(
            "app.ingestion.forecast_ingestion.get_windfor_records",
            new=AsyncMock(return_value=sample_api_records),
        ):
            report = asyncio.run(_ingest_forecasts(
                publish_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                publish_to=datetime(2026, 1, 1, 23, 59, 59, tzinfo=timezone.utc),
                session=test_db_session,
            ))

        assert report.ingestion_status == "completed"
        assert report.retrieved_record_count == 2
        assert report.valid_record_count == 2
        assert report.inserted_record_count == 2
        assert report.skipped_duplicate_count == 0
        assert report.invalid_record_count == 0

        # Assert records actually exist in database
        count = test_db_session.query(WindForecast).count()
        assert count == 2

    def test_duplicate_ingestion_idempotency(self, test_db_session) -> None:
        """Test that running ingestion twice inserts records on first run and skips on second."""
        sample_api_records = [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T12:00:00Z",
                "startTime": "2026-01-02T00:00:00Z",
                "generation": 1250.5,
            }
        ]

        with patch(
            "app.ingestion.forecast_ingestion.get_windfor_records",
            new=AsyncMock(return_value=sample_api_records),
        ):
            # First execution
            report1 = asyncio.run(_ingest_forecasts(
                publish_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                publish_to=datetime(2026, 1, 1, 23, 59, 59, tzinfo=timezone.utc),
                session=test_db_session,
            ))
            assert report1.inserted_record_count == 1
            assert report1.skipped_duplicate_count == 0

            # Second execution with exact same records
            report2 = asyncio.run(_ingest_forecasts(
                publish_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                publish_to=datetime(2026, 1, 1, 23, 59, 59, tzinfo=timezone.utc),
                session=test_db_session,
            ))
            assert report2.inserted_record_count == 0
            assert report2.skipped_duplicate_count == 1

        # Total in DB should still be 1
        assert test_db_session.query(WindForecast).count() == 1

    def test_multiple_forecast_versions_preserved(self, test_db_session) -> None:
        """Test that different publication versions for the same delivery interval are preserved."""
        versioned_records = [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T12:00:00Z",
                "startTime": "2026-01-02T00:00:00Z",
                "generation": 1200.0,
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T18:00:00Z",
                "startTime": "2026-01-02T00:00:00Z",  # Same delivery start
                "generation": 1350.0,
            },
        ]

        with patch(
            "app.ingestion.forecast_ingestion.get_windfor_records",
            new=AsyncMock(return_value=versioned_records),
        ):
            report = asyncio.run(_ingest_forecasts(
                publish_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                publish_to=datetime(2026, 1, 2, tzinfo=timezone.utc),
                session=test_db_session,
            ))

        assert report.inserted_record_count == 2
        assert report.skipped_duplicate_count == 0

        # Verify both distinct records were saved
        db_records = test_db_session.query(WindForecast).all()
        assert len(db_records) == 2
        generations = {r.generation for r in db_records}
        assert generations == {1200.0, 1350.0}

    def test_invalid_records_counted_and_reported(self, test_db_session) -> None:
        """Test that invalid records are counted and valid records are still persisted."""
        mixed_records = [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T12:00:00Z",
                "startTime": "2026-01-02T00:00:00Z",
                "generation": 1250.5,
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T12:00:00Z",
                "startTime": "2026-01-02T01:00:00Z",
                "generation": -100.0,  # Invalid negative generation
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "not-a-timestamp",
                "startTime": "2026-01-02T02:00:00Z",
                "generation": 500.0,  # Invalid timestamp
            },
        ]

        with patch(
            "app.ingestion.forecast_ingestion.get_windfor_records",
            new=AsyncMock(return_value=mixed_records),
        ):
            report = asyncio.run(_ingest_forecasts(
                publish_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                publish_to=datetime(2026, 1, 2, tzinfo=timezone.utc),
                session=test_db_session,
            ))

        assert report.retrieved_record_count == 3
        assert report.valid_record_count == 1
        assert report.invalid_record_count == 2
        assert report.inserted_record_count == 1
        assert test_db_session.query(WindForecast).count() == 1

    def test_empty_api_response(self, test_db_session) -> None:
        """Test graceful handling of empty API response."""
        with patch(
            "app.ingestion.forecast_ingestion.get_windfor_records",
            new=AsyncMock(return_value=[]),
        ):
            report = asyncio.run(_ingest_forecasts(
                publish_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                publish_to=datetime(2026, 1, 2, tzinfo=timezone.utc),
                session=test_db_session,
            ))

        assert report.retrieved_record_count == 0
        assert report.inserted_record_count == 0
        assert report.ingestion_status == "completed"

    def test_sync_ingest_forecasts_wrapper(self, test_db_session) -> None:
        """Test the synchronous ingest_forecasts wrapper function."""
        sample_api_records = [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T12:00:00Z",
                "startTime": "2026-01-02T00:00:00Z",
                "generation": 1000.0,
            }
        ]

        with patch(
            "app.ingestion.forecast_ingestion.get_windfor_records",
            new=AsyncMock(return_value=sample_api_records),
        ):
            report = ingest_forecasts(
                publish_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                publish_to=datetime(2026, 1, 2, tzinfo=timezone.utc),
                session=test_db_session,
            )

        assert report.inserted_record_count == 1
        assert test_db_session.query(WindForecast).count() == 1
