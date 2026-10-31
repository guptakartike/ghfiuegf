from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AccuracyMetrics(BaseModel):
    """Aggregate accuracy metrics in MW."""

    mae: Optional[float] = Field(
        None,
        description="Mean Absolute Error in MW: AVG(|forecast - actual|)",
    )
    rmse: Optional[float] = Field(
        None,
        description="Root Mean Squared Error in MW: SQRT(AVG((forecast - actual)^2))",
    )
    bias: Optional[float] = Field(
        None,
        description="Mean Error / Bias in MW: AVG(forecast - actual). Positive = overforecast, negative = underforecast",
    )
    sample_count: int = Field(
        ...,
        description="Number of complete matched hourly observations evaluated",
    )
    avg_forecast: Optional[float] = Field(
        None,
        description="Average forecast generation in MW",
    )
    avg_actual: Optional[float] = Field(
        None,
        description="Average actual generation in MW",
    )
    min_error: Optional[float] = Field(
        None,
        description="Minimum error (maximum underforecast) in MW",
    )
    max_error: Optional[float] = Field(
        None,
        description="Maximum error (maximum overforecast) in MW",
    )


class DailyAccuracyMetric(BaseModel):
    """Accuracy metrics aggregated for a single UK delivery date."""

    date: str = Field(..., description="Delivery date in Europe/London (YYYY-MM-DD)")
    mae: Optional[float] = Field(None, description="Mean Absolute Error in MW")
    rmse: Optional[float] = Field(None, description="Root Mean Squared Error in MW")
    bias: Optional[float] = Field(None, description="Mean Error in MW")
    sample_count: int = Field(..., description="Number of complete hourly observations in the day")
    avg_forecast: Optional[float] = Field(None, description="Daily average forecast in MW")
    avg_actual: Optional[float] = Field(None, description="Daily average actual in MW")


class AccuracySummaryResponse(BaseModel):
    """Response for GET /api/v1/accuracy."""

    cutoff_hour: int = Field(
        ...,
        description="Decision cutoff hour applied (e.g. 15 for 15:00 Europe/London on D-1)",
    )
    cutoff_minute: int = Field(
        0,
        description="Decision cutoff minute applied (default: 0)",
    )
    delivery_from: Optional[datetime] = Field(None, description="Start delivery timestamp in UTC")
    delivery_to: Optional[datetime] = Field(None, description="End delivery timestamp in UTC")
    overall: AccuracyMetrics
    daily: List[DailyAccuracyMetric]


class HourlyTimeseriesPoint(BaseModel):
    """A single delivery hour observation in timeseries."""

    delivery_time: datetime = Field(..., description="Delivery hour start in UTC")
    forecast_publish_time: datetime = Field(..., description="Selected forecast publication timestamp in UTC")
    forecast_generation: float = Field(..., description="Forecast wind generation in MW")
    actual_generation: float = Field(..., description="Actual wind generation in MW")
    forecast_error: float = Field(..., description="Forecast error in MW: forecast - actual")
    abs_error: float = Field(..., description="Absolute forecast error in MW")
    cutoff_time: datetime = Field(..., description="Applied decision cutoff timestamp in UTC")


class DailyTimeseriesPoint(BaseModel):
    """A daily aggregated data point in timeseries."""

    date: str = Field(..., description="Delivery date (YYYY-MM-DD)")
    mae: Optional[float] = None
    rmse: Optional[float] = None
    bias: Optional[float] = None
    sample_count: int
    avg_forecast: Optional[float] = None
    avg_actual: Optional[float] = None


class TimeseriesResponse(BaseModel):
    """Response for GET /api/v1/accuracy/timeseries."""

    granularity: str = Field(..., description="'hourly' or 'daily'")
    cutoff_hour: int
    cutoff_minute: int = 0
    delivery_from: Optional[datetime] = None
    delivery_to: Optional[datetime] = None
    sample_count: int
    hourly_data: Optional[List[HourlyTimeseriesPoint]] = None
    daily_data: Optional[List[DailyTimeseriesPoint]] = None


class ErrorDistributionBin(BaseModel):
    """Histogram bin for error distribution."""

    bin_start: float = Field(..., description="Lower bound of error bin in MW")
    bin_end: float = Field(..., description="Upper bound of error bin in MW")
    bin_center: float = Field(..., description="Center of error bin in MW")
    count: int = Field(..., description="Observation count within bin")
    percentage: float = Field(..., description="Percentage of total samples")


class ErrorDistributionStats(BaseModel):
    """Summary statistics for error distribution."""

    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    p10: Optional[float] = None
    p25: Optional[float] = None
    p75: Optional[float] = None
    p90: Optional[float] = None


class ErrorObservationsResponse(BaseModel):
    """Response for GET /api/v1/accuracy/errors."""

    cutoff_hour: int
    cutoff_minute: int = 0
    delivery_from: Optional[datetime] = None
    delivery_to: Optional[datetime] = None
    total_count: int
    page: int
    limit: int
    total_pages: int
    stats: ErrorDistributionStats
    bins: List[ErrorDistributionBin]
    observations: List[HourlyTimeseriesPoint]


class TopErrorRecord(BaseModel):
    """Record representing a significant forecast error."""

    rank: int = Field(..., description="Rank ordered by error magnitude (1-indexed)")
    delivery_time: datetime
    forecast_publish_time: datetime
    forecast_generation: float
    actual_generation: float
    forecast_error: float
    abs_error: float
    cutoff_time: datetime


class TopErrorsResponse(BaseModel):
    """Response for GET /api/v1/accuracy/top-errors."""

    cutoff_hour: int
    cutoff_minute: int = 0
    delivery_from: Optional[datetime] = None
    delivery_to: Optional[datetime] = None
    error_type: str = Field(..., description="'absolute', 'overforecast', or 'underforecast'")
    total_evaluated_samples: int
    top_errors: List[TopErrorRecord]

