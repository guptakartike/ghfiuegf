from sqlalchemy import BigInteger, DateTime, Float, Integer, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class WindForecast(Base):
    __tablename__ = "wind_forecasts"

    __table_args__ = (
        UniqueConstraint(
            "publish_time",
            "start_time",
            name="uq_forecast_publish_delivery",
        ),
        Index("ix_forecast_start_time", "start_time"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    publish_time: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    start_time: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    generation: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )