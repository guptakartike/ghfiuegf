from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.ingestion.client import get_windfor_records
from app.ingestion.persistence import insert_forecasts_batch
from app.ingestion.report import IngestionReportData
from app.ingestion.schemas import WindforRecord
from app.ingestion.validation import (
    check_date_range,
    detect_missing_forecast_intervals,
    validate_windfor_record,
)

logger = logging.getLogger(__name__)

DEFAULT_PUBLISH_FROM = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
DEFAULT_PUBLISH_TO = datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Elexon WINDFOR data ingestion")
    parser.add_argument(
        "--publish-from",
        type=lambda v: datetime.fromisoformat(
            v.replace("Z", "+00:00") if "T" in v else f"{v}T00:00:00+00:00"
        ),
        default=DEFAULT_PUBLISH_FROM,
        help="Lower bound for publishDateTime filter (ISO 8601, default: 2026-01-01T00:00:00Z)",
    )
    parser.add_argument(
        "--publish-to",
        type=lambda v: datetime.fromisoformat(
            v.replace("Z", "+00:00") if "T" in v else f"{v}T23:59:59+00:00"
        ),
        default=DEFAULT_PUBLISH_TO,
        help="Upper bound for publishDateTime filter (ISO 8601, default: 2026-01-31T23:59:59Z)",
    )
    return parser.parse_args()


async def _ingest_forecasts(
    publish_from: datetime,
    publish_to: datetime,
    client: Optional[httpx.AsyncClient] = None,
    session: Optional[Session] = None,
) -> IngestionReportData:
    """Asynchronous pipeline for WINDFOR forecast data ingestion."""
    if publish_from.tzinfo is None:
        publish_from = publish_from.replace(tzinfo=timezone.utc)
    else:
        publish_from = publish_from.astimezone(timezone.utc)

    if publish_to.tzinfo is None:
        publish_to = publish_to.replace(tzinfo=timezone.utc)
    else:
        publish_to = publish_to.astimezone(timezone.utc)

    report = IngestionReportData(
        source_dataset="WINDFOR",
        requested_date_range=f"{publish_from.isoformat()} to {publish_to.isoformat()}",
    )
    report.mark_started()

    try:
        raw_records = await get_windfor_records(publish_from, publish_to, client=client)
        report.retrieved_record_count = len(raw_records)
    except Exception as exc:
        logger.error("Failed to fetch WINDFOR records: %s", exc)
        report.ingestion_status = "failed"
        return report

    logger.info("Retrieved %d raw WINDFOR records", len(raw_records))

    valid_records: list[WindforRecord] = []
    invalid_count = 0
    earliest_ts: Optional[datetime] = None
    latest_ts: Optional[datetime] = None

    for raw in raw_records:
        validated, errors = validate_windfor_record(raw)
        if errors or validated is None:
            invalid_count += 1
            logger.warning("Invalid WINDFOR record: %s", errors)
            continue

        if earliest_ts is None or validated.publish_time < earliest_ts:
            earliest_ts = validated.publish_time
        if latest_ts is None or validated.publish_time > latest_ts:
            latest_ts = validated.publish_time

        valid_records.append(validated)

    # Persist valid records in batch using ON CONFLICT DO NOTHING
    inserted = 0
    skipped = 0
    if valid_records:
        try:
            inserted, skipped = insert_forecasts_batch(valid_records, session=session)
        except Exception as exc:
            logger.error("Failed to persist WINDFOR records batch: %s", exc)
            report.ingestion_status = "failed"
            return report

    # Detect missing intervals
    missing_count = 0
    if valid_records:
        missing_count = detect_missing_forecast_intervals(
            valid_records,
            start_time=publish_from,
            end_time=publish_to,
        )

    report.valid_record_count = len(valid_records)
    report.mark_completed(
        inserted=inserted,
        skipped=skipped,
        invalid=invalid_count,
        retrieved=len(raw_records),
        earliest=earliest_ts,
        latest=latest_ts,
        missing=missing_count,
    )
    return report


def ingest_forecasts(
    publish_from: datetime = DEFAULT_PUBLISH_FROM,
    publish_to: datetime = DEFAULT_PUBLISH_TO,
    client: Optional[httpx.AsyncClient] = None,
    session: Optional[Session] = None,
) -> IngestionReportData:
    """Synchronous entry point for WINDFOR ingestion."""
    return asyncio.run(
        _ingest_forecasts(
            publish_from=publish_from,
            publish_to=publish_to,
            client=client,
            session=session,
        )
    )


def run_ingestion() -> None:
    """CLI execution entry point."""
    args = _parse_args()
    report = ingest_forecasts(args.publish_from, args.publish_to)

    print("\n=== WINDFOR Ingestion Report ===")
    print(f"Source dataset: {report.source_dataset}")
    print(f"Requested date range: {report.requested_date_range}")
    print(f"Retrieved records: {report.retrieved_record_count}")
    print(f"Valid records: {report.valid_record_count}")
    print(f"  Inserted: {report.inserted_record_count}")
    print(f"  Skipped (duplicates): {report.skipped_duplicate_count}")
    print(f"Invalid records: {report.invalid_record_count}")
    print(f"Missing interval count: {report.missing_interval_count}")
    if report.earliest_timestamp:
        print(f"Earliest timestamp: {report.earliest_timestamp.isoformat()}")
    if report.latest_timestamp:
        print(f"Latest timestamp: {report.latest_timestamp.isoformat()}")
    print(f"Ingestion status: {report.ingestion_status}")
    print("===============================\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_ingestion()


if __name__ == "__main__":
    main()
