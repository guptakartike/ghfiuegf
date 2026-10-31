from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.services.actual_aggregation import (
    ActualAggregationResult,
    AggregatedActual,
    IncompleteHourReport,
    aggregate_actuals,
    aggregate_actuals_from_db,
)
from app.services.cutoff import (
    CutoffConfig,
    DEFAULT_CUTOFF_CONFIG,
    get_decision_cutoff,
)
from app.services.forecast_selection import (
    ForecastSelectionResult,
    SelectedForecast,
    select_forecast_for_delivery_hour,
    select_forecasts,
    select_forecasts_from_db,
)

if TYPE_CHECKING:
    from app.services.matching import (
        MatchedRecord,
        MatchingResult,
        match_forecasts_and_actuals,
        persist_matched_records,
        run_matching_pipeline,
    )

__all__ = [
    "CutoffConfig",
    "DEFAULT_CUTOFF_CONFIG",
    "get_decision_cutoff",
    "SelectedForecast",
    "ForecastSelectionResult",
    "select_forecast_for_delivery_hour",
    "select_forecasts",
    "select_forecasts_from_db",
    "AggregatedActual",
    "IncompleteHourReport",
    "ActualAggregationResult",
    "aggregate_actuals",
    "aggregate_actuals_from_db",
    "MatchedRecord",
    "MatchingResult",
    "match_forecasts_and_actuals",
    "persist_matched_records",
    "run_matching_pipeline",
]


def __getattr__(name: str) -> Any:
    if name in (
        "MatchedRecord",
        "MatchingResult",
        "match_forecasts_and_actuals",
        "persist_matched_records",
        "run_matching_pipeline",
    ):
        import app.services.matching as matching_mod

        return getattr(matching_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
