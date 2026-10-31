from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.ingestion.report import IngestionReportData
from app.ingestion.schemas import FuelhhRecord, IngestionReport, WindforRecord

if TYPE_CHECKING:
    from app.ingestion.actual_ingestion import ingest_actuals
    from app.ingestion.forecast_ingestion import ingest_forecasts

__all__ = [
    "ingest_forecasts",
    "ingest_actuals",
    "WindforRecord",
    "FuelhhRecord",
    "IngestionReport",
    "IngestionReportData",
]


def __getattr__(name: str) -> Any:
    if name == "ingest_forecasts":
        from app.ingestion.forecast_ingestion import ingest_forecasts

        return ingest_forecasts
    if name == "ingest_actuals":
        from app.ingestion.actual_ingestion import ingest_actuals

        return ingest_actuals
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
