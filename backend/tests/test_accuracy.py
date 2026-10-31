from __future__ import annotations

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.matched_observation import MatchedHourlyObservation
from app.services.accuracy import (
    compute_accuracy_metrics,
    compute_daily_metrics,
    compute_distribution_bins,
    get_accuracy_summary,
    get_accuracy_timeseries,
    get_error_distribution_and_observations,
    get_top_errors,
)


@pytest.fixture
def sample_matched_records() -> list[MatchedHourlyObservation]:
    """Sample matched observations covering multiple hours and error signs."""
    # Day 1: 2026-01-02
    r1 = MatchedHourlyObservation(
        delivery_time=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
        forecast_publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
        forecast_generation=1500.0,
        actual_generation=1200.0,
        forecast_error=300.0,  # +300 MW (overforecast)
        cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
    )
    r2 = MatchedHourlyObservation(
        delivery_time=datetime(2026, 1, 2, 1, 0, tzinfo=timezone.utc),
        forecast_publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
        forecast_generation=1000.0,
        actual_generation=1400.0,
        forecast_error=-400.0,  # -400 MW (underforecast)
        cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
    )
    # Day 2: 2026-01-03
    r3 = MatchedHourlyObservation(
        delivery_time=datetime(2026, 1, 3, 0, 0, tzinfo=timezone.utc),
        forecast_publish_time=datetime(2026, 1, 2, 14, 0, tzinfo=timezone.utc),
        forecast_generation=2000.0,
        actual_generation=1500.0,
        forecast_error=500.0,  # +500 MW (overforecast)
        cutoff_time=datetime(2026, 1, 2, 15, 0, tzinfo=timezone.utc),
    )
    r4 = MatchedHourlyObservation(
        delivery_time=datetime(2026, 1, 3, 1, 0, tzinfo=timezone.utc),
        forecast_publish_time=datetime(2026, 1, 2, 14, 0, tzinfo=timezone.utc),
        forecast_generation=800.0,
        actual_generation=900.0,
        forecast_error=-100.0,  # -100 MW (underforecast)
        cutoff_time=datetime(2026, 1, 2, 15, 0, tzinfo=timezone.utc),
    )
    return [r1, r2, r3, r4]


class TestMetricFormulas:
    """Unit tests for MAE, RMSE, and Bias calculation logic."""

    def test_accuracy_metrics_calculation(self, sample_matched_records) -> None:
        # Errors: [300.0, -400.0, 500.0, -100.0]
        # |Errors|: [300.0, 400.0, 500.0, 100.0] -> sum = 1300 / 4 = 325.0
        # Errors^2: [90000, 160000, 250000, 10000] -> sum = 510000 / 4 = 127500 -> sqrt = 357.07
        # Bias: (300 - 400 + 500 - 100) / 4 = 300 / 4 = 75.0
        metrics = compute_accuracy_metrics(sample_matched_records)

        assert metrics.sample_count == 4
        assert metrics.mae == 325.0
        assert metrics.rmse == 357.07
        assert metrics.bias == 75.0
        assert metrics.min_error == -400.0
        assert metrics.max_error == 500.0
        assert metrics.avg_forecast == 1325.0
        assert metrics.avg_actual == 1250.0

    def test_positive_bias_indicates_overforecasting(self) -> None:
        records = [
            MatchedHourlyObservation(
                delivery_time=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
                forecast_publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
                forecast_generation=1500.0,
                actual_generation=1000.0,
                forecast_error=500.0,
                cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
        ]
        metrics = compute_accuracy_metrics(records)
        assert metrics.bias == 500.0
        assert metrics.bias > 0

    def test_negative_bias_indicates_underforecasting(self) -> None:
        records = [
            MatchedHourlyObservation(
                delivery_time=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
                forecast_publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
                forecast_generation=1000.0,
                actual_generation=1500.0,
                forecast_error=-500.0,
                cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
        ]
        metrics = compute_accuracy_metrics(records)
        assert metrics.bias == -500.0
        assert metrics.bias < 0

    def test_empty_dataset_returns_none_metrics_without_error(self) -> None:
        metrics = compute_accuracy_metrics([])
        assert metrics.sample_count == 0
        assert metrics.mae is None
        assert metrics.rmse is None
        assert metrics.bias is None


class TestAggregations:
    """Test daily grouping, error distribution, and top error ranking."""

    def test_daily_metrics_grouping(self, sample_matched_records) -> None:
        daily = compute_daily_metrics(sample_matched_records)
        assert len(daily) == 2
        assert daily[0].date == "2026-01-02"
        assert daily[0].sample_count == 2
        # Day 1: errors [300, -400] -> mae = 350.0, bias = -50.0
        assert daily[0].mae == 350.0
        assert daily[0].bias == -50.0

        assert daily[1].date == "2026-01-03"
        assert daily[1].sample_count == 2
        # Day 2: errors [500, -100] -> mae = 300.0, bias = 200.0
        assert daily[1].mae == 300.0
        assert daily[1].bias == 200.0

    def test_error_distribution_bins_and_stats(self) -> None:
        errors = [-500.0, -200.0, 0.0, 100.0, 300.0, 600.0]
        bins, stats = compute_distribution_bins(errors, num_bins=4)

        assert stats.min == -500.0
        assert stats.max == 600.0
        assert stats.median == 50.0
        assert len(bins) == 4
        total_counts = sum(b.count for b in bins)
        assert total_counts == len(errors)
        total_pct = sum(b.percentage for b in bins)
        assert round(total_pct) == 100

    def test_top_errors_ordering_absolute(self, sample_matched_records, test_db_session) -> None:
        test_db_session.add_all(sample_matched_records)
        test_db_session.commit()

        top = get_top_errors(test_db_session, limit=2, error_type="absolute")
        assert len(top.top_errors) == 2
        # Absolute errors: 500, 400, 300, 100 -> top 2 are 500 and -400
        assert top.top_errors[0].abs_error == 500.0
        assert top.top_errors[0].rank == 1
        assert top.top_errors[1].abs_error == 400.0
        assert top.top_errors[1].rank == 2

    def test_top_errors_ordering_overforecast(self, sample_matched_records, test_db_session) -> None:
        test_db_session.add_all(sample_matched_records)
        test_db_session.commit()

        top = get_top_errors(test_db_session, limit=2, error_type="overforecast")
        assert len(top.top_errors) == 2
        # Overforecast: +500, +300
        assert top.top_errors[0].forecast_error == 500.0
        assert top.top_errors[1].forecast_error == 300.0

    def test_top_errors_ordering_underforecast(self, sample_matched_records, test_db_session) -> None:
        test_db_session.add_all(sample_matched_records)
        test_db_session.commit()

        top = get_top_errors(test_db_session, limit=2, error_type="underforecast")
        assert len(top.top_errors) == 2
        # Underforecast: -400, -100
        assert top.top_errors[0].forecast_error == -400.0
        assert top.top_errors[1].forecast_error == -100.0


class TestAccuracyAPIEndpoints:
    """Integration tests for accuracy API routes using FastAPI TestClient."""

    @pytest.fixture(autouse=True)
    def setup_app_db(self, test_db_session):
        from app.database import get_db

        def override_get_db():
            yield test_db_session

        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    def test_get_accuracy_summary_empty(self) -> None:
        client = TestClient(app)
        res = client.get("/api/v1/accuracy")
        assert res.status_code == 200
        data = res.json()
        assert data["overall"]["sample_count"] == 0
        assert data["overall"]["mae"] is None
        assert data["daily"] == []

    def test_get_accuracy_summary_populated(self, sample_matched_records, test_db_session) -> None:
        test_db_session.add_all(sample_matched_records)
        test_db_session.commit()

        client = TestClient(app)
        res = client.get("/api/v1/accuracy")
        assert res.status_code == 200
        data = res.json()
        assert data["overall"]["sample_count"] == 4
        assert data["overall"]["mae"] == 325.0
        assert data["overall"]["rmse"] == 357.07
        assert data["overall"]["bias"] == 75.0
        assert len(data["daily"]) == 2

    def test_get_accuracy_date_range_filter(self, sample_matched_records, test_db_session) -> None:
        test_db_session.add_all(sample_matched_records)
        test_db_session.commit()

        client = TestClient(app)
        res = client.get("/api/v1/accuracy?start_date=2026-01-02&end_date=2026-01-02")
        assert res.status_code == 200
        data = res.json()
        assert data["overall"]["sample_count"] == 2
        assert len(data["daily"]) == 1
        assert data["daily"][0]["date"] == "2026-01-02"

    def test_invalid_date_range_returns_400(self) -> None:
        client = TestClient(app)
        res = client.get("/api/v1/accuracy?start_date=2026-01-05&end_date=2026-01-02")
        assert res.status_code == 400
        assert "must be before or equal to end_date" in res.json()["detail"]

    def test_invalid_date_format_returns_400(self) -> None:
        client = TestClient(app)
        res = client.get("/api/v1/accuracy?start_date=not-a-date")
        assert res.status_code == 400
        assert "Invalid start_date format" in res.json()["detail"]

    def test_get_timeseries_hourly(self, sample_matched_records, test_db_session) -> None:
        test_db_session.add_all(sample_matched_records)
        test_db_session.commit()

        client = TestClient(app)
        res = client.get("/api/v1/accuracy/timeseries?granularity=hourly")
        assert res.status_code == 200
        data = res.json()
        assert data["granularity"] == "hourly"
        assert data["sample_count"] == 4
        assert len(data["hourly_data"]) == 4
        # Verify ordering and fields
        first = data["hourly_data"][0]
        assert "delivery_time" in first
        assert "forecast_generation" in first
        assert "actual_generation" in first
        assert "forecast_error" in first
        assert "abs_error" in first

    def test_get_timeseries_daily(self, sample_matched_records, test_db_session) -> None:
        test_db_session.add_all(sample_matched_records)
        test_db_session.commit()

        client = TestClient(app)
        res = client.get("/api/v1/accuracy/timeseries?granularity=daily")
        assert res.status_code == 200
        data = res.json()
        assert data["granularity"] == "daily"
        assert len(data["daily_data"]) == 2

    def test_get_errors_distribution_and_pagination(self, sample_matched_records, test_db_session) -> None:
        test_db_session.add_all(sample_matched_records)
        test_db_session.commit()

        client = TestClient(app)
        res = client.get("/api/v1/accuracy/errors?page=1&limit=2")
        assert res.status_code == 200
        data = res.json()
        assert data["total_count"] == 4
        assert data["page"] == 1
        assert data["limit"] == 2
        assert data["total_pages"] == 2
        assert len(data["observations"]) == 2
        assert "stats" in data
        assert data["stats"]["min"] == -400.0
        assert data["stats"]["max"] == 500.0
        assert len(data["bins"]) > 0

    def test_get_top_errors_api(self, sample_matched_records, test_db_session) -> None:
        test_db_session.add_all(sample_matched_records)
        test_db_session.commit()

        client = TestClient(app)
        res = client.get("/api/v1/accuracy/top-errors?limit=3&error_type=absolute")
        assert res.status_code == 200
        data = res.json()
        assert data["error_type"] == "absolute"
        assert len(data["top_errors"]) == 3
        assert data["top_errors"][0]["rank"] == 1
        assert data["top_errors"][0]["abs_error"] == 500.0
        assert data["top_errors"][1]["rank"] == 2
        assert data["top_errors"][1]["abs_error"] == 400.0


class TestCutoffSeparationAndTimestamps:
    """Tests verifying complete cutoff_time timestamp filtering and separation."""

    @pytest.fixture(autouse=True)
    def setup_app_db(self, test_db_session):
        from app.database import get_db

        def override_get_db():
            yield test_db_session

        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    def test_12_vs_15_cutoff_separation(self, test_db_session) -> None:
        """Verify that 12:00 and 15:00 cutoffs for the same delivery hour yield strictly separated results."""
        delivery = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)

        # 12:00 cutoff record
        rec_12 = MatchedHourlyObservation(
            delivery_time=delivery,
            forecast_publish_time=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
            forecast_generation=2000.0,
            actual_generation=1800.0,
            forecast_error=200.0,
            cutoff_time=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        # 15:00 cutoff record
        rec_15 = MatchedHourlyObservation(
            delivery_time=delivery,
            forecast_publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
            forecast_generation=2400.0,
            actual_generation=1800.0,
            forecast_error=600.0,
            cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
        )
        test_db_session.add_all([rec_12, rec_15])
        test_db_session.commit()

        client = TestClient(app)

        # Query cutoff 12:00
        res_12 = client.get("/api/v1/accuracy?cutoff_hour=12")
        assert res_12.status_code == 200
        data_12 = res_12.json()
        assert data_12["cutoff_hour"] == 12
        assert data_12["overall"]["sample_count"] == 1
        assert data_12["overall"]["bias"] == 200.0
        assert data_12["overall"]["avg_forecast"] == 2000.0

        # Query cutoff 15:00
        res_15 = client.get("/api/v1/accuracy?cutoff_hour=15")
        assert res_15.status_code == 200
        data_15 = res_15.json()
        assert data_15["cutoff_hour"] == 15
        assert data_15["overall"]["sample_count"] == 1
        assert data_15["overall"]["bias"] == 600.0
        assert data_15["overall"]["avg_forecast"] == 2400.0

        # Query non-existent cutoff 10:00
        res_10 = client.get("/api/v1/accuracy?cutoff_hour=10")
        assert res_10.status_code == 200
        data_10 = res_10.json()
        assert data_10["cutoff_hour"] == 10
        assert data_10["overall"]["sample_count"] == 0

    def test_minute_level_cutoff_precision(self, test_db_session) -> None:
        """Verify that 15:30 cutoff is distinct from 15:00 cutoff and requires exact minute matching."""
        delivery = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)

        # 15:30 cutoff record
        rec_1530 = MatchedHourlyObservation(
            delivery_time=delivery,
            forecast_publish_time=datetime(2026, 1, 1, 15, 15, tzinfo=timezone.utc),
            forecast_generation=2100.0,
            actual_generation=1800.0,
            forecast_error=300.0,
            cutoff_time=datetime(2026, 1, 1, 15, 30, tzinfo=timezone.utc),
        )
        test_db_session.add(rec_1530)
        test_db_session.commit()

        client = TestClient(app)

        # Query 15:00 (default minute 0) -> should NOT match the 15:30 record
        res_1500 = client.get("/api/v1/accuracy?cutoff_hour=15&cutoff_minute=0")
        assert res_1500.status_code == 200
        assert res_1500.json()["overall"]["sample_count"] == 0

        # Query 15:30 -> exact match
        res_1530 = client.get("/api/v1/accuracy?cutoff_hour=15&cutoff_minute=30")
        assert res_1530.status_code == 200
        assert res_1530.json()["overall"]["sample_count"] == 1
        assert res_1530.json()["cutoff_hour"] == 15
        assert res_1530.json()["cutoff_minute"] == 30
        assert res_1530.json()["overall"]["bias"] == 300.0


class TestTimezoneAndDaylightSaving:
    """Tests for Europe/London timezone handling across GMT and BST seasons."""

    @pytest.fixture(autouse=True)
    def setup_app_db(self, test_db_session):
        from app.database import get_db

        def override_get_db():
            yield test_db_session

        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    def test_gmt_winter_cutoff_and_date_handling(self, test_db_session) -> None:
        """In January (GMT = UTC+0), cutoff 15:00 Europe/London corresponds to 15:00 UTC."""
        delivery = datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc)
        # In GMT: Jan 2 delivery -> D-1 is Jan 1 -> 15:00 London is 15:00 UTC
        rec = MatchedHourlyObservation(
            delivery_time=delivery,
            forecast_publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
            forecast_generation=1500.0,
            actual_generation=1400.0,
            forecast_error=100.0,
            cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
        )
        test_db_session.add(rec)
        test_db_session.commit()

        client = TestClient(app)
        res = client.get("/api/v1/accuracy?cutoff_hour=15&start_date=2026-01-02&end_date=2026-01-02")
        assert res.status_code == 200
        data = res.json()
        assert data["overall"]["sample_count"] == 1
        assert data["daily"][0]["date"] == "2026-01-02"

    def test_bst_summer_cutoff_and_date_handling(self, test_db_session) -> None:
        """In July (BST = UTC+1), cutoff 15:00 Europe/London corresponds to 14:00 UTC."""
        # July 2 10:00 London is July 2 09:00 UTC
        delivery_utc = datetime(2026, 7, 2, 9, 0, tzinfo=timezone.utc)
        # Decision date is July 1. 15:00 London is 14:00 UTC.
        cutoff_utc = datetime(2026, 7, 1, 14, 0, tzinfo=timezone.utc)

        rec = MatchedHourlyObservation(
            delivery_time=delivery_utc,
            forecast_publish_time=datetime(2026, 7, 1, 13, 0, tzinfo=timezone.utc),
            forecast_generation=3000.0,
            actual_generation=2800.0,
            forecast_error=200.0,
            cutoff_time=cutoff_utc,
        )
        test_db_session.add(rec)
        test_db_session.commit()

        client = TestClient(app)
        # Querying cutoff_hour=15 (which means 15:00 UK time) matches 14:00 UTC
        res = client.get("/api/v1/accuracy?cutoff_hour=15&start_date=2026-07-02&end_date=2026-07-02")
        assert res.status_code == 200
        data = res.json()
        assert data["overall"]["sample_count"] == 1
        assert data["overall"]["bias"] == 200.0
        assert data["daily"][0]["date"] == "2026-07-02"

    def test_delivery_crossing_utc_midnight_in_bst(self, test_db_session) -> None:
        """In BST, 23:00 UTC on 2026-07-01 is 00:00 Europe/London on 2026-07-02 (Settlement Period 1)."""
        delivery_utc = datetime(2026, 7, 1, 23, 0, tzinfo=timezone.utc)
        # UK market date is 2026-07-02. Decision date is 2026-07-01. Cutoff is 15:00 BST = 14:00 UTC.
        cutoff_utc = datetime(2026, 7, 1, 14, 0, tzinfo=timezone.utc)

        rec = MatchedHourlyObservation(
            delivery_time=delivery_utc,
            forecast_publish_time=datetime(2026, 7, 1, 13, 0, tzinfo=timezone.utc),
            forecast_generation=2500.0,
            actual_generation=2200.0,
            forecast_error=300.0,
            cutoff_time=cutoff_utc,
        )
        test_db_session.add(rec)
        test_db_session.commit()

        client = TestClient(app)

        # Querying start_date=2026-07-02 should include this observation (00:00 London is 23:00 UTC July 1)
        res = client.get("/api/v1/accuracy?start_date=2026-07-02&end_date=2026-07-02&cutoff_hour=15")
        assert res.status_code == 200
        data = res.json()
        assert data["overall"]["sample_count"] == 1
        assert data["daily"][0]["date"] == "2026-07-02"

        # Querying start_date=2026-07-01&end_date=2026-07-01 must NOT include this observation
        res_prev = client.get("/api/v1/accuracy?start_date=2026-07-01&end_date=2026-07-01&cutoff_hour=15")
        assert res_prev.status_code == 200
        assert res_prev.json()["overall"]["sample_count"] == 0


class TestConsistentFilteringAcrossAllEndpoints:
    """Tests verifying identical cutoff and date filtering logic across all four endpoints."""

    @pytest.fixture(autouse=True)
    def setup_app_db(self, test_db_session):
        from app.database import get_db

        def override_get_db():
            yield test_db_session

        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    @pytest.fixture
    def multi_cutoff_multi_day_dataset(self, test_db_session):
        """Create a multi-cutoff, multi-day dataset to test consistency."""
        # Day 1 (Jan 2), 15:00 cutoff (Jan 1 15:00 UTC)
        r1 = MatchedHourlyObservation(
            delivery_time=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
            forecast_publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
            forecast_generation=1500.0,
            actual_generation=1200.0,
            forecast_error=300.0,
            cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
        )
        r2 = MatchedHourlyObservation(
            delivery_time=datetime(2026, 1, 2, 11, 0, tzinfo=timezone.utc),
            forecast_publish_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
            forecast_generation=1000.0,
            actual_generation=1200.0,
            forecast_error=-200.0,
            cutoff_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
        )
        # Day 1 (Jan 2), 12:00 cutoff (Jan 1 12:00 UTC)
        r3 = MatchedHourlyObservation(
            delivery_time=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
            forecast_publish_time=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
            forecast_generation=1800.0,
            actual_generation=1200.0,
            forecast_error=600.0,
            cutoff_time=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        # Day 2 (Jan 3), 15:00 cutoff (Jan 2 15:00 UTC)
        r4 = MatchedHourlyObservation(
            delivery_time=datetime(2026, 1, 3, 10, 0, tzinfo=timezone.utc),
            forecast_publish_time=datetime(2026, 1, 2, 14, 0, tzinfo=timezone.utc),
            forecast_generation=2000.0,
            actual_generation=1900.0,
            forecast_error=100.0,
            cutoff_time=datetime(2026, 1, 2, 15, 0, tzinfo=timezone.utc),
        )
        test_db_session.add_all([r1, r2, r3, r4])
        test_db_session.commit()

    def test_all_endpoints_filter_jan2_cutoff15_consistently(self, multi_cutoff_multi_day_dataset) -> None:
        client = TestClient(app)
        params = "?start_date=2026-01-02&end_date=2026-01-02&cutoff_hour=15&cutoff_minute=0"

        # 1. /accuracy
        res_acc = client.get(f"/api/v1/accuracy{params}")
        assert res_acc.status_code == 200
        acc_data = res_acc.json()
        assert acc_data["overall"]["sample_count"] == 2
        assert acc_data["overall"]["mae"] == 250.0  # (|300| + |-200|) / 2 = 250
        assert acc_data["overall"]["bias"] == 50.0   # (300 - 200) / 2 = 50

        # 2. /accuracy/timeseries (hourly)
        res_ts = client.get(f"/api/v1/accuracy/timeseries{params}&granularity=hourly")
        assert res_ts.status_code == 200
        ts_data = res_ts.json()
        assert ts_data["sample_count"] == 2
        assert len(ts_data["hourly_data"]) == 2
        assert [p["forecast_error"] for p in ts_data["hourly_data"]] == [300.0, -200.0]

        # 3. /accuracy/errors
        res_err = client.get(f"/api/v1/accuracy/errors{params}")
        assert res_err.status_code == 200
        err_data = res_err.json()
        assert err_data["total_count"] == 2
        assert len(err_data["observations"]) == 2
        assert err_data["stats"]["min"] == -200.0
        assert err_data["stats"]["max"] == 300.0

        # 4. /accuracy/top-errors
        res_top = client.get(f"/api/v1/accuracy/top-errors{params}&limit=5")
        assert res_top.status_code == 200
        top_data = res_top.json()
        assert top_data["total_evaluated_samples"] == 2
        assert len(top_data["top_errors"]) == 2
        assert top_data["top_errors"][0]["abs_error"] == 300.0
        assert top_data["top_errors"][1]["abs_error"] == 200.0

    def test_all_endpoints_filter_jan2_cutoff12_consistently(self, multi_cutoff_multi_day_dataset) -> None:
        client = TestClient(app)
        params = "?start_date=2026-01-02&end_date=2026-01-02&cutoff_hour=12&cutoff_minute=0"

        # 1. /accuracy
        res_acc = client.get(f"/api/v1/accuracy{params}")
        assert res_acc.status_code == 200
        assert res_acc.json()["overall"]["sample_count"] == 1
        assert res_acc.json()["overall"]["bias"] == 600.0

        # 2. /accuracy/timeseries
        res_ts = client.get(f"/api/v1/accuracy/timeseries{params}&granularity=hourly")
        assert res_ts.status_code == 200
        assert res_ts.json()["sample_count"] == 1
        assert res_ts.json()["hourly_data"][0]["forecast_error"] == 600.0

        # 3. /accuracy/errors
        res_err = client.get(f"/api/v1/accuracy/errors{params}")
        assert res_err.status_code == 200
        assert res_err.json()["total_count"] == 1
        assert res_err.json()["observations"][0]["forecast_error"] == 600.0

        # 4. /accuracy/top-errors
        res_top = client.get(f"/api/v1/accuracy/top-errors{params}")
        assert res_top.status_code == 200
        assert res_top.json()["total_evaluated_samples"] == 1
        assert res_top.json()["top_errors"][0]["forecast_error"] == 600.0

    def test_all_endpoints_filter_unmatched_cutoff_consistently(self, multi_cutoff_multi_day_dataset) -> None:
        client = TestClient(app)
        params = "?cutoff_hour=18"

        # All 4 endpoints return 0 samples
        res_acc = client.get(f"/api/v1/accuracy{params}")
        assert res_acc.status_code == 200
        assert res_acc.json()["overall"]["sample_count"] == 0

        res_ts = client.get(f"/api/v1/accuracy/timeseries{params}")
        assert res_ts.status_code == 200
        assert res_ts.json()["sample_count"] == 0

        res_err = client.get(f"/api/v1/accuracy/errors{params}")
        assert res_err.status_code == 200
        assert res_err.json()["total_count"] == 0

        res_top = client.get(f"/api/v1/accuracy/top-errors{params}")
        assert res_top.status_code == 200
        assert res_top.json()["total_evaluated_samples"] == 0
        assert len(res_top.json()["top_errors"]) == 0

    def test_invalid_parameters_return_errors_consistently(self) -> None:
        client = TestClient(app)

        # Invalid cutoff_hour > 23 -> 422
        for ep in ["/api/v1/accuracy", "/api/v1/accuracy/timeseries", "/api/v1/accuracy/errors", "/api/v1/accuracy/top-errors"]:
            res = client.get(f"{ep}?cutoff_hour=24")
            assert res.status_code == 422, f"Expected 422 on {ep} for cutoff_hour=24"

        # Invalid cutoff_hour < 0 -> 422
        for ep in ["/api/v1/accuracy", "/api/v1/accuracy/timeseries", "/api/v1/accuracy/errors", "/api/v1/accuracy/top-errors"]:
            res = client.get(f"{ep}?cutoff_hour=-1")
            assert res.status_code == 422, f"Expected 422 on {ep} for cutoff_hour=-1"

        # Invalid cutoff_minute > 59 -> 422
        for ep in ["/api/v1/accuracy", "/api/v1/accuracy/timeseries", "/api/v1/accuracy/errors", "/api/v1/accuracy/top-errors"]:
            res = client.get(f"{ep}?cutoff_minute=60")
            assert res.status_code == 422, f"Expected 422 on {ep} for cutoff_minute=60"

        # start_date > end_date -> 400
        for ep in ["/api/v1/accuracy", "/api/v1/accuracy/timeseries", "/api/v1/accuracy/errors", "/api/v1/accuracy/top-errors"]:
            res = client.get(f"{ep}?start_date=2026-01-05&end_date=2026-01-02")
            assert res.status_code == 400, f"Expected 400 on {ep} for inverted date range"
            assert "start_date" in res.json()["detail"]

