from __future__ import annotations

from datetime import date, datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.ingestion.schemas import FuelhhRecord, WindforRecord
from app.models.actual import ActualGeneration
from app.models.forecast import WindForecast
from app.models.matched_observation import MatchedHourlyObservation


@pytest.fixture
def sample_windfor_record() -> dict:
    """Sample WINDFOR record from Elexon API."""
    return {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-01T12:00:00Z",
        "startTime": "2026-01-02T00:00:00Z",
        "generation": 1250.5,
    }


@pytest.fixture
def sample_fuelhh_record() -> dict:
    """Sample FUELHH record from Elexon API."""
    return {
        "dataset": "FUELHH",
        "publishTime": "2026-01-02T00:30:00Z",
        "startTime": "2026-01-02T00:00:00Z",
        "settlementDate": "2026-01-02",
        "settlementPeriod": 1,
        "fuelType": "WIND",
        "generation": 1200.0,
    }


@pytest.fixture
def sample_windfor_record_multiple() -> dict:
    """Another WINDFOR record with same start time but different publish time (versioning test)."""
    return {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-02T12:00:00Z",
        "startTime": "2026-01-03T00:00:00Z",
        "generation": 1300.0,
    }


@pytest.fixture
def sample_windfor_invalid() -> dict:
    """WINDFOR record with invalid generation."""
    return {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-01T12:00:00Z",
        "startTime": "2026-01-02T00:00:00Z",
        "generation": -50.0,
    }


@pytest.fixture
def sample_fuelhh_invalid_fuel() -> dict:
    """FUELHH record with non-WIND fuel type."""
    return {
        "dataset": "FUELHH",
        "publishTime": "2026-01-02T00:30:00Z",
        "startTime": "2026-01-02T00:00:00Z",
        "settlementDate": "2026-01-02",
        "settlementPeriod": 1,
        "fuelType": "GAS",
        "generation": 500.0,
    }


@pytest.fixture
def sample_fuelhh_invalid_period() -> dict:
    """FUELHH record with invalid settlement period."""
    return {
        "dataset": "FUELHH",
        "publishTime": "2026-01-02T00:30:00Z",
        "startTime": "2026-01-02T00:00:00Z",
        "settlementDate": "2026-01-02",
        "settlementPeriod": 50,
        "fuelType": "WIND",
        "generation": 500.0,
    }


@pytest.fixture
def sample_fuelhh_missing_field() -> dict:
    """FUELHH record missing a required field."""
    return {
        "dataset": "FUELHH",
        "publishTime": "2026-01-02T00:30:00Z",
        "startTime": "2026-01-02T00:00:00Z",
        "settlementDate": "2026-01-02",
    }


@pytest.fixture
def sample_windfor_records() -> list[dict]:
    """Multiple sample WINDFOR records."""
    return [
        {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T12:00:00Z",
            "startTime": "2026-01-02T00:00:00Z",
            "generation": 1250.5,
        },
        {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-02T12:00:00Z",
            "startTime": "2026-01-03T00:00:00Z",
            "generation": 1300.0,
        },
    ]


@pytest.fixture
def sample_fuelhh_records() -> list[dict]:
    """Multiple sample FUELHH records."""
    return [
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-02T00:30:00Z",
            "startTime": "2026-01-02T00:00:00Z",
            "settlementDate": "2026-01-02",
            "settlementPeriod": 1,
            "fuelType": "WIND",
            "generation": 1200.0,
        },
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-02T01:00:00Z",
            "startTime": "2026-01-02T00:30:00Z",
            "settlementDate": "2026-01-02",
            "settlementPeriod": 2,
            "fuelType": "WIND",
            "generation": 1150.0,
        },
    ]


@pytest.fixture
def expected_windfor_validated() -> WindforRecord:
    """Expected validated WINDFOR record."""
    return WindforRecord(
        dataset="WINDFOR",
        publishTime="2026-01-01T12:00:00+00:00",
        startTime="2026-01-02T00:00:00+00:00",
        generation=1250.5,
    )


@pytest.fixture
def expected_fuelhh_validated() -> FuelhhRecord:
    """Expected validated FUELHH record."""
    return FuelhhRecord(
        dataset="FUELHH",
        publishTime="2026-01-02T00:30:00+00:00",
        startTime="2026-01-02T00:00:00+00:00",
        settlementDate="2026-01-02",
        settlementPeriod=1,
        fuelType="WIND",
        generation=1200.0,
    )


@pytest.fixture
def test_db_session():
    """Create a temporary in-memory SQLite database and session with all tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
