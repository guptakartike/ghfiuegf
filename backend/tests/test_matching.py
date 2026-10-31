from __future__ import annotations

from datetime import date, datetime, timezone
import pytest

from app.models.actual import ActualGeneration
from app.models.forecast import WindForecast
from app.models.matched_observation import MatchedHourlyObservation
from app.services.actual_aggregation import AggregatedActual
from app.services.forecast_selection import SelectedForecast
from app.services.matching import (
    MatchedRecord,
    match_forecasts_and_actuals,
    persist_matched_records,
    run_matching_pipeline,
)


class TestMatchingLogic:
    """Test forecast-actual alignment and error calculation."""

    def test_overforecast_positive_error_sign(self) -> None:
        """Forecast > Actual -> Positive error (overforecast)."""
        h = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
        selected = {
            h: SelectedForecast(
                delivery_time=h,
                publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
                generation=1500.0,
                cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
        }
        actuals = {
            h: AggregatedActual(
                delivery_time=h,
                generation=1200.0,
                interval_00_generation=1100.0,
                interval_30_generation=1300.0,
            )
        }

        res = match_forecasts_and_actuals([h], selected, actuals)
        assert res.matched_count == 1
        record = res.matched[0]
        assert record.forecast_generation == 1500.0
        assert record.actual_generation == 1200.0
        assert record.forecast_error == 300.0  # +300 MW (overforecast)

    def test_underforecast_negative_error_sign(self) -> None:
        """Forecast < Actual -> Negative error (underforecast)."""
        h = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
        selected = {
            h: SelectedForecast(
                delivery_time=h,
                publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
                generation=800.0,
                cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
        }
        actuals = {
            h: AggregatedActual(
                delivery_time=h,
                generation=1000.0,
                interval_00_generation=950.0,
                interval_30_generation=1050.0,
            )
        }

        res = match_forecasts_and_actuals([h], selected, actuals)
        assert res.matched_count == 1
        record = res.matched[0]
        assert record.forecast_generation == 800.0
        assert record.actual_generation == 1000.0
        assert record.forecast_error == -200.0  # -200 MW (underforecast)

    def test_unmatched_observations_tracked(self) -> None:
        """Unmatched hours are not silently discarded."""
        h1 = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        h2 = datetime(2026, 1, 2, 11, 0, tzinfo=timezone.utc)
        h3 = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)

        # h1 has forecast only; h2 has actual only; h3 has neither
        selected = {
            h1: SelectedForecast(
                delivery_time=h1,
                publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
                generation=500.0,
                cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
        }
        actuals = {
            h2: AggregatedActual(
                delivery_time=h2,
                generation=600.0,
                interval_00_generation=600.0,
                interval_30_generation=600.0,
            )
        }

        res = match_forecasts_and_actuals([h1, h2, h3], selected, actuals)
        assert res.matched_count == 0
        assert res.unmatched_forecasts == [h1]
        assert res.unmatched_actuals == [h2]
        assert res.missing_both == [h3]
        assert res.unmatched_count == 3


class TestMatchingPersistence:
    """Test database persistence and idempotency."""

    def test_repeated_processing_idempotent(self, test_db_session) -> None:
        """Running persistence multiple times updates/maintains records without duplicates."""
        h = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        record = MatchedRecord(
            delivery_time=h,
            forecast_publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
            forecast_generation=1200.0,
            actual_generation=1100.0,
            forecast_error=100.0,
            cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
        )

        # First run
        count1 = persist_matched_records(test_db_session, [record])
        assert count1 == 1
        assert test_db_session.query(MatchedHourlyObservation).count() == 1

        # Second run with exact same record
        count2 = persist_matched_records(test_db_session, [record])
        assert count2 == 1
        # Total in DB must remain 1
        assert test_db_session.query(MatchedHourlyObservation).count() == 1

    def test_different_cutoff_creates_separate_record(self, test_db_session) -> None:
        """A different cutoff creates a separate record for the same delivery hour."""
        h = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        record_cutoff_15 = MatchedRecord(
            delivery_time=h,
            forecast_publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
            forecast_generation=1200.0,
            actual_generation=1100.0,
            forecast_error=100.0,
            cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
        )
        record_cutoff_12 = MatchedRecord(
            delivery_time=h,
            forecast_publish_time=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
            forecast_generation=1150.0,
            actual_generation=1100.0,
            forecast_error=50.0,
            cutoff_time=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        persist_matched_records(test_db_session, [record_cutoff_15])
        assert test_db_session.query(MatchedHourlyObservation).count() == 1

        persist_matched_records(test_db_session, [record_cutoff_12])
        # Two distinct records for different cutoffs must coexist
        assert test_db_session.query(MatchedHourlyObservation).count() == 2

        # Rerunning either cutoff is idempotent
        persist_matched_records(test_db_session, [record_cutoff_15])
        assert test_db_session.query(MatchedHourlyObservation).count() == 2

    def test_unmatched_records_not_silently_discarded_or_zero_filled(self) -> None:
        """Verify unmatched records are explicitly counted and never zero-filled into matched."""
        h1 = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)  # Matched
        h2 = datetime(2026, 1, 2, 11, 0, tzinfo=timezone.utc)  # Forecast only
        h3 = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)  # Actual only
        h4 = datetime(2026, 1, 2, 13, 0, tzinfo=timezone.utc)  # Missing both

        selected = {
            h1: SelectedForecast(h1, datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc), 1000.0, datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc)),
            h2: SelectedForecast(h2, datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc), 1200.0, datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc)),
        }
        actuals = {
            h1: AggregatedActual(h1, 950.0, 900.0, 1000.0),
            h3: AggregatedActual(h3, 1100.0, 1050.0, 1150.0),
        }

        res = match_forecasts_and_actuals([h1, h2, h3, h4], selected, actuals)
        assert res.matched_count == 1
        assert res.matched[0].delivery_time == h1
        # Confirm unmatched are explicitly tracked in separate lists
        assert res.unmatched_forecasts == [h2]
        assert res.unmatched_actuals == [h3]
        assert res.missing_both == [h4]
        assert res.unmatched_count == 3
        # Ensure h2 was NOT fabricated as matched with 0 actual
        matched_delivery_times = [m.delivery_time for m in res.matched]
        assert h2 not in matched_delivery_times
        assert h3 not in matched_delivery_times
        assert h4 not in matched_delivery_times

    def test_run_matching_pipeline_end_to_end(self, test_db_session) -> None:
        """Complete end-to-end run querying DB forecasts and actuals and persisting match."""
        h = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)

        # Insert eligible forecast and post-cutoff forecast
        f_eligible = WindForecast(
            start_time=h,
            publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
            generation=1500.0,
        )
        f_post = WindForecast(
            start_time=h,
            publish_time=datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc),
            generation=1800.0,
        )
        test_db_session.add_all([f_eligible, f_post])

        # Insert two actuals
        a1 = ActualGeneration(
            start_time=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
            settlement_date=date(2026, 1, 2),
            settlement_period=21,
            generation=1300.0,
            publish_time=datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc),
        )
        a2 = ActualGeneration(
            start_time=datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc),
            settlement_date=date(2026, 1, 2),
            settlement_period=22,
            generation=1400.0,
            publish_time=datetime(2026, 1, 2, 11, 0, tzinfo=timezone.utc),
        )
        test_db_session.add_all([a1, a2])
        test_db_session.commit()

        # Run pipeline
        res = run_matching_pipeline(test_db_session, start_delivery=h, end_delivery=h, persist=True)

        assert res.matched_count == 1
        assert res.unmatched_count == 0

        # Verify persisted record
        saved = test_db_session.query(MatchedHourlyObservation).first()
        assert saved is not None
        saved_delivery = (
            saved.delivery_time.replace(tzinfo=timezone.utc)
            if saved.delivery_time.tzinfo is None
            else saved.delivery_time.astimezone(timezone.utc)
        )
        saved_publish = (
            saved.forecast_publish_time.replace(tzinfo=timezone.utc)
            if saved.forecast_publish_time.tzinfo is None
            else saved.forecast_publish_time.astimezone(timezone.utc)
        )
        assert saved_delivery == h
        assert saved_publish == datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc)
        assert saved.forecast_generation == 1500.0
        assert saved.actual_generation == 1350.0  # (1300 + 1400) / 2
        assert saved.forecast_error == 150.0      # 1500 - 1350
