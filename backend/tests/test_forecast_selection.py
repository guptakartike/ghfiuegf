from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pytest

from app.models.forecast import WindForecast
from app.services.cutoff import CutoffConfig, get_decision_cutoff
from app.services.forecast_selection import (
    select_forecast_for_delivery_hour,
    select_forecasts,
    select_forecasts_from_db,
)


class TestCutoffCalculation:
    """Test decision cutoff calculation and timezone handling."""

    def test_january_delivery_cutoff_utc(self) -> None:
        # Delivery on 2026-01-02 05:00:00 UTC
        # D-1 decision date: 2026-01-01
        # Cutoff: 2026-01-01 15:00:00 Europe/London -> 2026-01-01 15:00:00 UTC (GMT)
        delivery = datetime(2026, 1, 2, 5, 0, tzinfo=timezone.utc)
        cutoff = get_decision_cutoff(delivery)
        assert cutoff == datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc)

    def test_custom_cutoff_config(self) -> None:
        delivery = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
        config = CutoffConfig(cutoff_hour=12, cutoff_minute=30, days_ahead=1)
        cutoff = get_decision_cutoff(delivery, config)
        assert cutoff == datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)

    def test_utc_and_london_boundary_handling(self) -> None:
        # Midnight delivery in UTC: 2026-01-02 00:00:00 UTC is also 2026-01-02 00:00:00 London
        delivery_midnight = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
        cutoff = get_decision_cutoff(delivery_midnight)
        assert cutoff == datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc)


class TestForecastSelection:
    """Test forecast version eligibility and selection rules."""

    def test_latest_eligible_forecast_selected(self) -> None:
        delivery = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        f1 = WindForecast(
            start_time=delivery,
            publish_time=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
            generation=1000.0,
        )
        f2 = WindForecast(
            start_time=delivery,
            publish_time=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            generation=1200.0,
        )
        f3 = WindForecast(
            start_time=delivery,
            publish_time=datetime(2026, 1, 1, 14, 45, tzinfo=timezone.utc),
            generation=1350.0,
        )

        selected = select_forecast_for_delivery_hour(delivery, [f1, f2, f3])
        assert selected is not None
        assert selected.publish_time == datetime(2026, 1, 1, 14, 45, tzinfo=timezone.utc)
        assert selected.generation == 1350.0

    def test_forecast_exactly_at_cutoff_excluded(self) -> None:
        """Forecast published at exactly 15:00:00 on D-1 must be excluded."""
        delivery = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        f_before = WindForecast(
            start_time=delivery,
            publish_time=datetime(2026, 1, 1, 14, 59, 59, tzinfo=timezone.utc),
            generation=1100.0,
        )
        f_at_cutoff = WindForecast(
            start_time=delivery,
            publish_time=datetime(2026, 1, 1, 15, 0, 0, tzinfo=timezone.utc),
            generation=1500.0,
        )

        selected = select_forecast_for_delivery_hour(delivery, [f_before, f_at_cutoff])
        assert selected is not None
        assert selected.publish_time == datetime(2026, 1, 1, 14, 59, 59, tzinfo=timezone.utc)
        assert selected.generation == 1100.0

    def test_forecast_after_cutoff_excluded(self) -> None:
        """Forecasts published strictly after cutoff are not selected."""
        delivery = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        f_post = WindForecast(
            start_time=delivery,
            publish_time=datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc),
            generation=2000.0,
        )
        selected = select_forecast_for_delivery_hour(delivery, [f_post])
        assert selected is None

    def test_different_eligible_versions_across_delivery_hours(self) -> None:
        """Verify independent selection across distinct delivery hours."""
        h1 = datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc)
        h2 = datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)

        records = [
            WindForecast(start_time=h1, publish_time=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc), generation=500.0),
            WindForecast(start_time=h1, publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc), generation=600.0),
            WindForecast(start_time=h2, publish_time=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc), generation=700.0),
            WindForecast(start_time=h2, publish_time=datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc), generation=800.0),
        ]

        result = select_forecasts([h1, h2], records)
        assert len(result.selected) == 2
        assert result.selected[h1].generation == 600.0
        assert result.selected[h2].generation == 800.0
        assert result.missing_hours == []

    def test_missing_eligible_forecasts_reported(self) -> None:
        """Delivery hours with no eligible pre-cutoff forecast are reported."""
        h1 = datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc)
        h2 = datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)

        # h1 has an eligible forecast; h2 only has a post-cutoff forecast
        records = [
            WindForecast(start_time=h1, publish_time=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc), generation=500.0),
            WindForecast(start_time=h2, publish_time=datetime(2026, 1, 1, 16, 0, tzinfo=timezone.utc), generation=900.0),
        ]

        result = select_forecasts([h1, h2], records)
        assert len(result.selected) == 1
        assert h1 in result.selected
        assert result.missing_hours == [h2]

    def test_db_selection_preserves_versions(self, test_db_session) -> None:
        """Verify DB selection against real SQLite session without mutating source rows."""
        h = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
        f1 = WindForecast(start_time=h, publish_time=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc), generation=100.0)
        f2 = WindForecast(start_time=h, publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc), generation=200.0)
        f3 = WindForecast(start_time=h, publish_time=datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc), generation=300.0)

        test_db_session.add_all([f1, f2, f3])
        test_db_session.commit()

        res = select_forecasts_from_db(test_db_session, h, h)
        assert len(res.selected) == 1
        assert res.selected[h].generation == 200.0

        # Verify all 3 records still exist untouched in database
        count = test_db_session.query(WindForecast).count()
        assert count == 3

