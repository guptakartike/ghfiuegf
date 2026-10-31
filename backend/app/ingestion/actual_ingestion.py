from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.ingestion.client import get_fuelhh_records
from app.ingestion.persistence import insert_actuals_batch
from app.ingestion.report import IngestionReportData
from app.ingestion.schemas import FuelhhRecord
from app.ingestion.validation import (
    check_date_range,
    detect_missing_actual_intervals,
    has_sufficient_resolution,
    validate_fuelhh_record,
)

logger = logging.getLogger(__name__)

DEFAULT_SETTLEMENT_FROM = "2026-01-02"
DEFAULT_SETTLEMENT_TO = "2026-02-01"


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Elexon FUELHH data ingestion")
    parser.add_argument(
        "--settlement-from",
        type=lambda v: v.strip(),
        default=DEFAULT_SETTLEMENT_FROM,
        help="Lower bound for settlementDate filter (YYYY-MM-DD, default: 2026-01-02)",
    )
    parser.add_argument(
        "--settlement-to",
        type=lambda v: v.strip(),
        default=DEFAULT_SETTLEMENT_TO,
        help="Upper bound for settlementDate filter (YYYY-MM-DD, default: 2026-02-01)",
    )
    parser.add_argument(
        "--fuel-type",
        type=lambda v: v.strip(),
        default="WIND",
        help="Fuel type filter (default: WIND)",
    )
    return parser.parse_args()


async def _ingest_actuals(
    settlement_from: str,
    settlement_to: str,
    fuel_type: str = "WIND",
    client: Optional[httpx.AsyncClient] = None,
    session: Optional[Session] = None,
) -> IngestionReportData:
    """Asynchronous pipeline for FUELHH actual generation data ingestion."""
    start_date = date.fromisoformat(settlement_from)
    end_date = date.fromisoformat(settlement_to)

    report = IngestionReportData(
        source_dataset="FUELHH",
        requested_date_range=f"{settlement_from} to {settlement_to}",
    )
    report.mark_started()

    try:
        raw_records = await get_fuelhh_records(
            settlement_date_from=settlement_from,
            settlement_date_to=settlement_to,
            fuel_type=fuel_type,
            client=client,
        )
        report.retrieved_record_count = len(raw_records)
    except Exception as exc:
        logger.error("Failed to fetch FUELHH records: %s", exc)
        report.ingestion_status = "failed"
        return report

    logger.info("Retrieved %d raw FUELHH records", len(raw_records))

    valid_records: list[FuelhhRecord] = []
    invalid_count = 0
    earliest_ts: Optional[datetime] = None
    latest_ts: Optional[datetime] = None

    for raw in raw_records:
        validated, errors = validate_fuelhh_record(raw)
        if errors or validated is None:
            invalid_count += 1
            logger.warning("Invalid FUELHH record: %s", errors)
            continue

        res_ok, res_errors = has_sufficient_resolution(raw, "actual")
        if not res_ok:
            invalid_count += 1
            logger.warning("Resolution error in FUELHH record: %s", res_errors)
            continue

        if earliest_ts is None or validated.start_time < earliest_ts:
            earliest_ts = validated.start_time
        if latest_ts is None or validated.start_time > latest_ts:
            latest_ts = validated.start_time

        valid_records.append(validated)

    inserted = 0
    skipped = 0
    if valid_records:
        try:
            inserted, skipped = insert_actuals_batch(valid_records, session=session)
        except Exception as exc:
            logger.error("Failed to persist FUELHH records batch: %s", exc)
            report.ingestion_status = "failed"
            return report

    missing_count = 0
    if valid_records:
        missing_count = detect_missing_actual_intervals(
            valid_records,
            start_date=start_date,
            end_date=end_date,
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


def ingest_actuals(
    settlement_from: str = DEFAULT_SETTLEMENT_FROM,
    settlement_to: str = DEFAULT_SETTLEMENT_TO,
    fuel_type: str = "WIND",
    client: Optional[httpx.AsyncClient] = None,
    session: Optional[Session] = None,
) -> IngestionReportData:
    """Synchronous entry point for FUELHH actuals ingestion."""
    return asyncio.run(
        _ingest_actuals(
            settlement_from=settlement_from,
            settlement_to=settlement_to,
            fuel_type=fuel_type,
            client=client,
            session=session,
        )
    )


def run_ingestion() -> None:
    """CLI execution entry point."""
    args = _parse_args()
    report = ingest_actuals(args.settlement_from, args.settlement_to, args.fuel_type)

    print("\n=== FUELHH Ingestion Report ===")
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
