from __future__ import annotations

from datetime import date, datetime, timezone
import pytest

from app.models.actual import ActualGeneration
from app.services.actual_aggregation import (
    aggregate_actuals,
    aggregate_actuals_for_hour,
    aggregate_actuals_from_db,
)


class TestActualAggregation:
    """Test aggregation of half-hourly FUELHH observations into hourly MW averages."""

    def test_hourly_averaging_arithmetic_mean(self) -> None:
        """Verify that two half-hourly observations are averaged, NOT summed."""
        h = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        obs_00 = ActualGeneration(
            start_time=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
            settlement_date=date(2026, 1, 2),
            settlement_period=21,
            generation=1000.0,
            publish_time=datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc),
        )
        obs_30 = ActualGeneration(
            start_time=datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc),
            settlement_date=date(2026, 1, 2),
            settlement_period=22,
            generation=1400.0,
            publish_time=datetime(2026, 1, 2, 11, 0, tzinfo=timezone.utc),
        )

        agg, incomplete = aggregate_actuals_for_hour(h, [obs_00, obs_30])
        assert incomplete is None
        assert agg is not None
        assert agg.generation == 1200.0  # (1000 + 1400) / 2.0
        assert agg.generation != 2400.0  # Confirm not summed

    def test_missing_minute_30_incomplete(self) -> None:
        """Hour with only minute 00 is reported as incomplete and not zero-filled."""
        h = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        obs_00 = ActualGeneration(
            start_time=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
            settlement_date=date(2026, 1, 2),
            settlement_period=21,
            generation=1000.0,
            publish_time=datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc),
        )

        agg, incomplete = aggregate_actuals_for_hour(h, [obs_00])
        assert agg is None
        assert incomplete is not None
        assert incomplete.observation_count == 1
        assert incomplete.has_minute_00 is True
        assert incomplete.has_minute_30 is False
        assert "Missing minute :30" in incomplete.reason

    def test_missing_minute_00_incomplete(self) -> None:
        """Hour with only minute 30 is reported as incomplete."""
        h = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        obs_30 = ActualGeneration(
            start_time=datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc),
            settlement_date=date(2026, 1, 2),
            settlement_period=22,
            generation=1500.0,
            publish_time=datetime(2026, 1, 2, 11, 0, tzinfo=timezone.utc),
        )

        agg, incomplete = aggregate_actuals_for_hour(h, [obs_30])
        assert agg is None
        assert incomplete is not None
        assert incomplete.has_minute_00 is False
        assert incomplete.has_minute_30 is True

    def test_duplicate_actual_interval_reported(self) -> None:
        """Hour with duplicate observations for the same interval is flagged irregular."""
        h = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        obs_00_a = ActualGeneration(
            start_time=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
            settlement_date=date(2026, 1, 2),
            settlement_period=21,
            generation=1000.0,
            publish_time=datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc),
        )
        obs_00_b = ActualGeneration(
            start_time=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
            settlement_date=date(2026, 1, 2),
            settlement_period=21,
            generation=1050.0,
            publish_time=datetime(2026, 1, 2, 10, 35, tzinfo=timezone.utc),
        )
        obs_30 = ActualGeneration(
            start_time=datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc),
            settlement_date=date(2026, 1, 2),
            settlement_period=22,
            generation=1200.0,
            publish_time=datetime(2026, 1, 2, 11, 0, tzinfo=timezone.utc),
        )

        agg, incomplete = aggregate_actuals_for_hour(h, [obs_00_a, obs_00_b, obs_30])
        assert agg is None
        assert incomplete is not None
        assert "Duplicate minute :00" in incomplete.reason

    def test_aggregate_from_db(self, test_db_session) -> None:
        """Test DB aggregation querying real session."""
        h = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        obs_00 = ActualGeneration(
            start_time=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
            settlement_date=date(2026, 1, 2),
            settlement_period=21,
            generation=800.0,
            publish_time=datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc),
        )
        obs_30 = ActualGeneration(
            start_time=datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc),
            settlement_date=date(2026, 1, 2),
            settlement_period=22,
            generation=1000.0,
            publish_time=datetime(2026, 1, 2, 11, 0, tzinfo=timezone.utc),
        )
        test_db_session.add_all([obs_00, obs_30])
        test_db_session.commit()

        res = aggregate_actuals_from_db(test_db_session, h, h)
        assert len(res.aggregated) == 1
        assert res.aggregated[h].generation == 900.0
        assert len(res.incomplete_hours) == 0

