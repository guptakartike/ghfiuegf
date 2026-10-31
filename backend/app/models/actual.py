from sqlalchemy import (
    BigInteger, Date, DateTime, Float, Integer,
    UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ActualGeneration(Base):
    __tablename__ = "actual_generation"

    __table_args__ = (
        UniqueConstraint("start_time", name="uq_actual_start_time"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    start_time: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    settlement_date: Mapped[object] = mapped_column(
        Date, nullable=False
    )

    settlement_period: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    generation: Mapped[float] = mapped_column(Float, nullable=False)

    publish_time: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )