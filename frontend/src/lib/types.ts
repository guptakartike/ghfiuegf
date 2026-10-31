export interface HealthResponse {
  status: string;
}

export interface AccuracyMetrics {
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  sample_count: number;
  avg_forecast: number | null;
  avg_actual: number | null;
  min_error: number | null;
  max_error: number | null;
}

export interface DailyAccuracyMetric {
  date: string;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  sample_count: number;
  avg_forecast: number | null;
  avg_actual: number | null;
}

export interface AccuracySummaryResponse {
  cutoff_hour: number;
  cutoff_minute: number;
  delivery_from: string | null;
  delivery_to: string | null;
  overall: AccuracyMetrics;
  daily: DailyAccuracyMetric[];
}

export interface HourlyTimeseriesPoint {
  delivery_time: string;
  forecast_publish_time: string;
  forecast_generation: number;
  actual_generation: number;
  forecast_error: number;
  abs_error: number;
  cutoff_time: string;
}

export interface DailyTimeseriesPoint {
  date: string;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  sample_count: number;
  avg_forecast: number | null;
  avg_actual: number | null;
}

export interface TimeseriesResponse {
  granularity: 'hourly' | 'daily';
  cutoff_hour: number;
  cutoff_minute: number;
  delivery_from: string | null;
  delivery_to: string | null;
  sample_count: number;
  hourly_data: HourlyTimeseriesPoint[] | null;
  daily_data: DailyTimeseriesPoint[] | null;
}

export interface ErrorDistributionBin {
  bin_start: number;
  bin_end: number;
  bin_center: number;
  count: number;
  percentage: number;
}

export interface ErrorDistributionStats {
  min: number | null;
  max: number | null;
  mean: number | null;
  median: number | null;
  std_dev: number | null;
  p10: number | null;
  p25: number | null;
  p75: number | null;
  p90: number | null;
}

export interface ErrorObservationsResponse {
  cutoff_hour: number;
  cutoff_minute: number;
  delivery_from: string | null;
  delivery_to: string | null;
  total_count: number;
  page: number;
  limit: number;
  total_pages: number;
  stats: ErrorDistributionStats;
  bins: ErrorDistributionBin[];
  observations: HourlyTimeseriesPoint[];
}

export interface TopErrorRecord {
  rank: number;
  delivery_time: string;
  forecast_publish_time: string;
  forecast_generation: number;
  actual_generation: number;
  forecast_error: number;
  abs_error: number;
  cutoff_time: string;
}

export interface TopErrorsResponse {
  cutoff_hour: number;
  cutoff_minute: number;
  delivery_from: string | null;
  delivery_to: string | null;
  error_type: 'absolute' | 'overforecast' | 'underforecast';
  total_evaluated_samples: number;
  top_errors: TopErrorRecord[];
}

export type NavigationPath = 'overview' | 'forecast-explorer' | 'accuracy-analysis';
