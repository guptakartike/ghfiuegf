from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.ingestion.schemas import IngestionReport as SchemaReport


@dataclass
class IngestionReportData:
    """Dataclass-based ingestion report."""

    source_dataset: str
    requested_date_range: str
    retrieved_record_count: int = 0
    valid_record_count: int = 0
    inserted_record_count: int = 0
    skipped_duplicate_count: int = 0
    invalid_record_count: int = 0
    missing_interval_count: int = 0
    earliest_timestamp: datetime | None = None
    latest_timestamp: datetime | None = None
    ingestion_status: str = "pending"

    def mark_started(self) -> None:
        self.ingestion_status = "in_progress"

    def mark_completed(
        self,
        inserted: int,
        skipped: int,
        invalid: int,
        retrieved: int,
        earliest: datetime | None,
        latest: datetime | None,
        missing: int = 0,
    ) -> None:
        self.inserted_record_count = inserted
        self.skipped_duplicate_count = skipped
        self.invalid_record_count = invalid
        self.retrieved_record_count = retrieved
        self.earliest_timestamp = earliest
        self.latest_timestamp = latest
        self.missing_interval_count = missing
        self.ingestion_status = "completed"

    def to_schema(self) -> SchemaReport:
        """Convert to Pydantic schema version."""
        return SchemaReport(
            source_dataset=self.source_dataset,
            requested_date_range=self.requested_date_range,
            retrieved_record_count=self.retrieved_record_count,
            valid_record_count=self.valid_record_count,
            inserted_record_count=self.inserted_record_count,
            skipped_duplicate_count=self.skipped_duplicate_count,
            invalid_record_count=self.invalid_record_count,
            missing_interval_count=self.missing_interval_count,
            earliest_timestamp=self.earliest_timestamp,
            latest_timestamp=self.latest_timestamp,
            ingestion_status=self.ingestion_status,
        )