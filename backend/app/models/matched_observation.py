from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MatchedHourlyObservation(Base):
    """Hourly matched forecast and actual generation observation.

    Stores the selected forecast (published strictly before the decision cutoff),
    the aggregated hourly actual generation (arithmetic mean of two half-hourly observations),
    and the calculated forecast error (forecast - actual).
    """

    __tablename__ = "matched_hourly_observations"

    __table_args__ = (
        UniqueConstraint(
            "delivery_time",
            "cutoff_time",
            name="uq_matched_delivery_cutoff",
        ),
        Index("ix_matched_delivery_cutoff", "delivery_time", "cutoff_time"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    delivery_time: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Start of the delivery hour in UTC",
    )

    forecast_publish_time: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Publication timestamp of the selected forecast version in UTC",
    )

    forecast_generation: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Forecast wind generation in MW",
    )

    actual_generation: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Aggregated hourly average actual wind generation in MW",
    )

    forecast_error: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Forecast error in MW: forecast_generation - actual_generation",
    )

    cutoff_time: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Decision cutoff timestamp applied for version eligibility in UTC",
    )

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

