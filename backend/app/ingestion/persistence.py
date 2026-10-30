from __future__ import annotations

from datetime import date, datetime, timezone
import logging
from typing import Any, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.ingestion.schemas import FuelhhRecord, WindforRecord
from app.models.actual import ActualGeneration
from app.models.forecast import WindForecast

logger = logging.getLogger(__name__)


def _get_session() -> Session:
    """Get a new SQLAlchemy session."""
    return SessionLocal()


def insert_forecasts_batch(
    records: list[WindforRecord],
    session: Optional[Session] = None,
) -> Tuple[int, int]:
    """Insert a batch of wind forecast records with ON CONFLICT DO NOTHING.

    Parameters
    ----------
    records : list[WindforRecord]
        List of validated forecast records to persist.
    session : Optional[Session]
        Existing database session, or None to create one.

    Returns
    -------
    Tuple[int, int]
        (inserted_count, skipped_duplicate_count).
    """
    if not records:
        return 0, 0

    db = session or _get_session()
    close_when_done = session is None

    try:
        payload = [
            {
                "publish_time": r.publish_time,
                "start_time": r.start_time,
                "generation": r.generation,
            }
            for r in records
        ]

        dialect_name = db.bind.dialect.name if db.bind else "postgresql"
        if dialect_name == "postgresql":
            stmt = (
                pg_insert(WindForecast)
                .values(payload)
                .on_conflict_do_nothing(
                    index_elements=["publish_time", "start_time"]
                )
                .returning(WindForecast.id)
            )
        elif dialect_name == "sqlite":
            stmt = (
                sqlite_insert(WindForecast)
                .values(payload)
                .on_conflict_do_nothing(
                    index_elements=["publish_time", "start_time"]
                )
                .returning(WindForecast.id)
            )
        else:
            stmt = (
                pg_insert(WindForecast)
                .values(payload)
                .on_conflict_do_nothing(
                    index_elements=["publish_time", "start_time"]
                )
                .returning(WindForecast.id)
            )

        result = db.execute(stmt)
        inserted = len(result.all())
        db.commit()
        skipped = len(payload) - inserted
        return inserted, skipped
    except Exception as exc:
        db.rollback()
        logger.error("Failed to insert forecasts batch: %s", exc)
        raise
    finally:
        if close_when_done:
            db.close()


def insert_actuals_batch(
    records: list[FuelhhRecord],
    session: Optional[Session] = None,
) -> Tuple[int, int]:
    """Insert a batch of actual generation records with ON CONFLICT DO NOTHING.

    Parameters
    ----------
    records : list[FuelhhRecord]
        List of validated actual records to persist.
    session : Optional[Session]
        Existing database session, or None to create one.

    Returns
    -------
    Tuple[int, int]
        (inserted_count, skipped_duplicate_count).
    """
    if not records:
        return 0, 0

    db = session or _get_session()
    close_when_done = session is None

    try:
        payload = [
            {
                "start_time": r.start_time,
                "settlement_date": r.settlement_date,
                "settlement_period": r.settlement_period,
                "generation": r.generation,
                "publish_time": r.publish_time,
            }
            for r in records
        ]

        dialect_name = db.bind.dialect.name if db.bind else "postgresql"
        if dialect_name == "postgresql":
            stmt = (
                pg_insert(ActualGeneration)
                .values(payload)
                .on_conflict_do_nothing(index_elements=["start_time"])
                .returning(ActualGeneration.id)
            )
        elif dialect_name == "sqlite":
            stmt = (
                sqlite_insert(ActualGeneration)
                .values(payload)
                .on_conflict_do_nothing(index_elements=["start_time"])
                .returning(ActualGeneration.id)
            )
        else:
            stmt = (
                pg_insert(ActualGeneration)
                .values(payload)
                .on_conflict_do_nothing(index_elements=["start_time"])
                .returning(ActualGeneration.id)
            )

        result = db.execute(stmt)
        inserted = len(result.all())
        db.commit()
        skipped = len(payload) - inserted
        return inserted, skipped
    except Exception as exc:
        db.rollback()
        logger.error("Failed to insert actuals batch: %s", exc)
        raise
    finally:
        if close_when_done:
            db.close()


def upsert_forecast(
    publish_time: datetime,
    start_time: datetime,
    generation: float,
    session: Optional[Session] = None,
) -> bool:
    """Insert a single wind forecast record idempotently."""
    rec = WindforRecord(
        dataset="WINDFOR",
        publishTime=publish_time,
        startTime=start_time,
        generation=generation,
    )
    inserted, _ = insert_forecasts_batch([rec], session=session)
    return inserted > 0


def upsert_actual(
    start_time: datetime,
    settlement_date: date | str,
    settlement_period: int,
    generation: float,
    publish_time: datetime,
    session: Optional[Session] = None,
) -> bool:
    """Insert a single actual generation record idempotently."""
    if isinstance(settlement_date, str):
        s_date = date.fromisoformat(settlement_date)
    else:
        s_date = settlement_date

    rec = FuelhhRecord(
        dataset="FUELHH",
        publishTime=publish_time,
        startTime=start_time,
        settlementDate=s_date,
        settlementPeriod=settlement_period,
        fuelType="WIND",
        generation=generation,
    )
    inserted, _ = insert_actuals_batch([rec], session=session)
    return inserted > 0


def get_forecast_count(
    publish_time_from: datetime,
    publish_time_to: datetime,
    session: Optional[Session] = None,
) -> int:
    """Get the count of wind forecasts in a date range."""
    db = session or _get_session()
    close_when_done = session is None
    try:
        stmt = select(WindForecast).where(
            WindForecast.publish_time >= publish_time_from,
            WindForecast.publish_time <= publish_time_to,
        )
        result = db.execute(stmt)
        return len(result.scalars().all())
    finally:
        if close_when_done:
            db.close()


def get_actual_count(
    start_time_from: datetime,
    start_time_to: datetime,
    session: Optional[Session] = None,
) -> int:
    """Get the count of actual generation records in a date range."""
    db = session or _get_session()
    close_when_done = session is None
    try:
        stmt = select(ActualGeneration).where(
            ActualGeneration.start_time >= start_time_from,
            ActualGeneration.start_time <= start_time_to,
        )
        result = db.execute(stmt)
        return len(result.scalars().all())
    finally:
        if close_when_done:
            db.close()
