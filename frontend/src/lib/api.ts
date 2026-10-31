import type {
  AccuracySummaryResponse,
  ErrorObservationsResponse,
  HealthResponse,
  TimeseriesResponse,
  TopErrorsResponse,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export async function apiRequest<T>(endpoint: string): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url);

  if (!response.ok) {
    let errorDetail = `HTTP Error ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) {
        errorDetail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // response wasn't json
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export interface AccuracyQueryParams {
  startDate?: string;
  endDate?: string;
  cutoffHour?: number;
  cutoffMinute?: number;
}

function buildQueryString(params: Record<string, string | number | undefined>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

export async function fetchHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health');
}

export async function fetchAccuracySummary(
  params: AccuracyQueryParams = {}
): Promise<AccuracySummaryResponse> {
  const qs = buildQueryString({
    start_date: params.startDate,
    end_date: params.endDate,
    cutoff_hour: params.cutoffHour,
    cutoff_minute: params.cutoffMinute,
  });
  return apiRequest<AccuracySummaryResponse>(`/accuracy${qs}`);
}

export async function fetchTimeseries(
  params: AccuracyQueryParams & { granularity?: 'hourly' | 'daily' } = {}
): Promise<TimeseriesResponse> {
  const qs = buildQueryString({
    start_date: params.startDate,
    end_date: params.endDate,
    cutoff_hour: params.cutoffHour,
    cutoff_minute: params.cutoffMinute,
    granularity: params.granularity || 'hourly',
  });
  return apiRequest<TimeseriesResponse>(`/accuracy/timeseries${qs}`);
}

export async function fetchErrors(
  params: AccuracyQueryParams & {
    page?: number;
    limit?: number;
    binSize?: number;
  } = {}
): Promise<ErrorObservationsResponse> {
  const qs = buildQueryString({
    start_date: params.startDate,
    end_date: params.endDate,
    cutoff_hour: params.cutoffHour,
    cutoff_minute: params.cutoffMinute,
    page: params.page,
    limit: params.limit,
    bin_size: params.binSize,
  });
  return apiRequest<ErrorObservationsResponse>(`/accuracy/errors${qs}`);
}

export async function fetchTopErrors(
  params: AccuracyQueryParams & {
    limit?: number;
    errorType?: 'absolute' | 'overforecast' | 'underforecast';
  } = {}
): Promise<TopErrorsResponse> {
  const qs = buildQueryString({
    start_date: params.startDate,
    end_date: params.endDate,
    cutoff_hour: params.cutoffHour,
    cutoff_minute: params.cutoffMinute,
    limit: params.limit,
    error_type: params.errorType || 'absolute',
  });
  return apiRequest<TopErrorsResponse>(`/accuracy/top-errors${qs}`);
}
