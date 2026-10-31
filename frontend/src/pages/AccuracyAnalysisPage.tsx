import React, { useEffect, useState, useMemo } from 'react';
import {
  fetchAccuracySummary,
  fetchTimeseries,
  fetchErrors,
  fetchTopErrors,
  type AccuracyQueryParams,
} from '../lib/api';
import type {
  AccuracySummaryResponse,
  TimeseriesResponse,
  ErrorObservationsResponse,
  TopErrorsResponse,
  HourlyTimeseriesPoint,
} from '../lib/types';
import { KpiCard } from '../components/common/KpiCard';
import { LoadingState, ErrorState, EmptyState } from '../components/common/StatusStates';
import { Icon } from '../components/common/Icon';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  Cell,
  ReferenceLine,
} from 'recharts';

interface AccuracyAnalysisPageProps {
  cutoffHour: number;
  startDate?: string;
  endDate?: string;
}

export const AccuracyAnalysisPage: React.FC<AccuracyAnalysisPageProps> = ({
  cutoffHour,
  startDate,
  endDate,
}) => {
  const [summary, setSummary] = useState<AccuracySummaryResponse | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesResponse | null>(null);
  const [errorDist, setErrorDist] = useState<ErrorObservationsResponse | null>(null);
  const [topErrors, setTopErrors] = useState<TopErrorsResponse | null>(null);
  const [granularity, setGranularity] = useState<'hourly' | 'daily'>('hourly');
  const [errorTypeFilter, setErrorTypeFilter] = useState<'absolute' | 'overforecast' | 'underforecast'>('absolute');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const handleReload = () => setReloadKey((k) => k + 1);

  const queryParams = useMemo<AccuracyQueryParams>(
    () => ({
      cutoffHour,
      startDate,
      endDate,
    }),
    [cutoffHour, startDate, endDate]
  );

  useEffect(() => {
    let isCurrent = true;
    const loadData = async () => {
      try {
        const [sumRes, tsRes, errRes, topRes] = await Promise.all([
          fetchAccuracySummary(queryParams),
          fetchTimeseries({ ...queryParams, granularity }),
          fetchErrors(queryParams),
          fetchTopErrors({ ...queryParams, limit: 10, errorType: errorTypeFilter }),
        ]);
        if (isCurrent) {
          setSummary(sumRes);
          setTimeseries(tsRes);
          setErrorDist(errRes);
          setTopErrors(topRes);
        }
      } catch (err: unknown) {
        if (isCurrent) {
          setError(err instanceof Error ? err.message : 'Failed to fetch accuracy analysis');
        }
      } finally {
        if (isCurrent) {
          setLoading(false);
        }
      }
    };

    void loadData();

    return () => {
      isCurrent = false;
    };
  }, [queryParams, granularity, errorTypeFilter, reloadKey]);

  // Ratio of Over vs Under observations
  const ratioMetrics = useMemo(() => {
    if (!timeseries?.hourly_data || timeseries.hourly_data.length === 0) {
      return { overCount: 0, underCount: 0, overPct: 0, underPct: 0, total: 0 };
    }
    let over = 0;
    let under = 0;
    for (const r of timeseries.hourly_data) {
      if (r.forecast_error >= 0) over++;
      else under++;
    }
    const total = timeseries.hourly_data.length;
    return {
      overCount: over,
      underCount: under,
      overPct: Number(((over / total) * 100).toFixed(1)),
      underPct: Number(((under / total) * 100).toFixed(1)),
      total,
    };
  }, [timeseries]);

  // 7-day trailing rolling MAE calculation
  const rollingDailyData = useMemo(() => {
    if (!summary?.daily || summary.daily.length === 0) return [];
    return summary.daily.map((d, idx, arr) => {
      // average MAE over preceding 7 days
      const windowStart = Math.max(0, idx - 6);
      const windowSlice = arr.slice(windowStart, idx + 1);
      const validMaes = windowSlice.map((w) => w.mae ?? 0);
      const rollingMae = validMaes.reduce((acc, v) => acc + v, 0) / validMaes.length;
      return {
        date: d.date.slice(5),
        fullDate: d.date,
        dailyMae: d.mae ?? 0,
        rollingMae: Math.round(rollingMae),
      };
    });
  }, [summary]);

  if (loading) {
    return <LoadingState message="Calculating Accuracy Analytics & Bias Distributions..." />;
  }

  if (error) {
    return (
      <ErrorState
        title="Failed to Load Accuracy Analytics"
        message={error}
        onRetry={handleReload}
      />
    );
  }

  if (!summary || summary.overall.sample_count === 0) {
    return (
      <EmptyState
        title="No Accuracy Data Found"
        description="No matched hourly observations found for the selected cutoff and dates."
        actionText="Reload"
        onAction={handleReload}
      />
    );
  }

  const { overall } = summary;

  return (
    <div className="flex flex-col gap-6 max-w-[1440px] mx-auto p-4 sm:p-7">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-wider text-chart-primary font-semibold">
              Analytical Verification
            </span>
            <span className="w-1 h-1 rounded-full bg-border-strong" />
            <span className="text-[10px] uppercase tracking-wider text-text-muted font-medium">
              UK BMRS & National Grid ESO Outturn
            </span>
          </div>
          <h1 className="text-[24px] sm:text-[28px] font-semibold text-text-primary tracking-tight">
            Forecast Accuracy & Bias Analysis
          </h1>
          <p className="text-[13px] text-text-muted">
            Statistical verification of wind forecasts against UK balancing market outturn across {overall.sample_count} settlement hours.
          </p>
        </div>

        {/* Time Resolution Selector */}
        <div className="flex items-center self-start md:self-auto bg-surface-card p-1 rounded border border-border-subtle">
          <button
            type="button"
            onClick={() => setGranularity('hourly')}
            className={`px-3 py-1.5 rounded text-[12px] font-medium transition-colors ${
              granularity === 'hourly'
                ? 'bg-sidebar-surface text-sidebar-text font-semibold'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            Hourly Observations
          </button>
          <button
            type="button"
            onClick={() => setGranularity('daily')}
            className={`px-3 py-1.5 rounded text-[12px] font-medium transition-colors ${
              granularity === 'daily'
                ? 'bg-sidebar-surface text-sidebar-text font-semibold'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            Daily Aggregation
          </button>
        </div>
      </div>

      {/* Systematic Sign Notation Alert Bar */}
      <div className="bg-surface-card border-l-2 border-chart-primary p-3 rounded flex flex-wrap items-center justify-between gap-3 text-[12px] text-text-muted border border-border-subtle">
        <div className="flex flex-wrap items-center gap-2">
          <Icon name="info" className="text-[18px] text-chart-primary" />
          <span className="font-semibold text-text-primary">Sign Convention:</span>
          <span>Forecast Error = Forecast − Actual Outturn.</span>
          <span className="bg-surface-canvas px-2 py-0.5 rounded text-text-primary font-medium">
            Positive (+Δ) = Overforecast (Forecast &gt; Actual)
          </span>
          <span className="bg-surface-canvas px-2 py-0.5 rounded text-text-primary font-medium">
            Negative (−Δ) = Underforecast (Forecast &lt; Actual)
          </span>
        </div>
        <div className="text-[11px] font-mono text-text-faint">
          Cutoff: {String(cutoffHour).padStart(2, '0')}:00 UK D-1 | Resolution: Hourly
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: MAE */}
        <KpiCard
          label="Mean Absolute Error (MAE)"
          badge={
            <span className="text-[10px] text-text-faint uppercase tabular-nums">
              AVG(|Error|)
            </span>
          }
          value={overall.mae !== null ? overall.mae.toLocaleString('en-GB', { minimumFractionDigits: 2 }) : '—'}
          unit="MW"
          subtext="Mean absolute deviation magnitude"
          footerDotColor="bg-chart-primary"
          footerText={`Calculated across ${overall.sample_count} evaluated hours`}
        />

        {/* Card 2: RMSE */}
        <KpiCard
          label="Root Mean Squared (RMSE)"
          badge={
            <span className="text-[10px] text-text-faint uppercase tabular-nums">
              SQRT(AVG(Error²))
            </span>
          }
          value={overall.rmse !== null ? overall.rmse.toLocaleString('en-GB', { minimumFractionDigits: 2 }) : '—'}
          unit="MW"
          subtext="L2 quadratic penalty metric"
          footerDotColor="bg-text-muted"
          footerText={
            overall.mae && overall.rmse
              ? `RMSE/MAE Ratio: ${(overall.rmse / overall.mae).toFixed(2)}`
              : 'Variance of residuals'
          }
        />

        {/* Card 3: Forecast Bias */}
        <KpiCard
          label="Forecast Bias (Mean Error)"
          badge={
            <span className="text-[10px] text-chart-primary font-semibold uppercase">
              {(overall.bias ?? 0) >= 0 ? 'SYSTEMATIC OVER (+Δ)' : 'UNDER (−Δ)'}
            </span>
          }
          value={
            overall.bias !== null
              ? `${overall.bias >= 0 ? '+' : ''}${overall.bias.toLocaleString('en-GB', { minimumFractionDigits: 2 })}`
              : '—'
          }
          unit="MW"
          subtext="Directional bias tendency"
          footerDotColor="bg-chart-primary"
          footerText={
            (overall.bias ?? 0) >= 0
              ? 'Positive mean delta = Overforecasting'
              : 'Negative mean delta = Underforecasting'
          }
        />

        {/* Card 4: Over vs Under Ratio */}
        <div className="bg-surface-card border border-border-subtle p-4 rounded flex flex-col justify-between min-h-[132px]">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] uppercase tracking-wider text-text-muted font-medium">
              Over vs Under Ratio
            </span>
            <span className="text-[10px] text-text-faint uppercase tabular-nums">
              {ratioMetrics.total} Hours
            </span>
          </div>
          <div className="my-1 flex items-baseline gap-1.5">
            <span className="text-[24px] font-semibold text-text-primary tabular-nums">
              {ratioMetrics.overPct}%
            </span>
            <span className="text-[14px] text-text-faint">/</span>
            <span className="text-[20px] font-semibold text-chart-tertiary tabular-nums">
              {ratioMetrics.underPct}%
            </span>
          </div>
          <div className="pt-2 border-t border-border-subtle flex flex-col gap-1 text-[11px]">
            <span className="text-text-muted truncate">
              {ratioMetrics.overCount} hrs Over (+Δ) | {ratioMetrics.underCount} hrs Under (−Δ)
            </span>
            <div className="w-full bg-surface-canvas h-1.5 rounded overflow-hidden flex">
              <div className="bg-chart-primary h-full" style={{ width: `${ratioMetrics.overPct}%` }} />
              <div className="bg-sidebar-surface h-full" style={{ width: `${ratioMetrics.underPct}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Mid Section: 2-Column Analytical Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Error Distribution Histogram */}
        <div className="lg:col-span-5 bg-surface-card border border-border-subtle p-5 rounded flex flex-col justify-between">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h2 className="text-[14px] font-semibold text-text-primary">
                Error Distribution Histogram
              </h2>
              <p className="text-[12px] text-text-muted">
                Settlement hours binned by forecast error intervals (MW)
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-text-muted bg-surface-canvas px-2 py-0.5 rounded border border-border-strong/40">
              <span className="w-2 h-2 rounded-full bg-chart-primary" />
              <span>Hours / Bin</span>
            </div>
          </div>

          {/* Histogram Chart */}
          <div className="w-full h-[260px]">
            {errorDist?.bins && errorDist.bins.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={errorDist.bins}
                  margin={{ top: 10, right: 10, left: 0, bottom: 20 }}
                >
                  <XAxis
                    dataKey="bin_center"
                    tickFormatter={(val) => `${val > 0 ? '+' : ''}${Math.round(val)}`}
                    tick={{ fontSize: 9, fill: '#526B7A' }}
                    axisLine={{ stroke: '#CBD5DB' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 9, fill: '#526B7A' }}
                    axisLine={false}
                    tickLine={false}
                    width={32}
                  />
                  <ReferenceLine x={0} stroke="#142B3B" strokeDasharray="3 3" />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload || payload.length === 0) return null;
                      const b = payload[0].payload;
                      return (
                        <div className="bg-surface-card border border-sidebar-surface rounded p-2 text-left tabular-nums text-[11px]">
                          <div className="font-semibold text-text-primary border-b border-border-subtle pb-0.5 mb-1">
                            [{b.bin_start} to {b.bin_end} MW]
                          </div>
                          <div>Count: <strong>{b.count} hours</strong></div>
                          <div>Share: <strong>{b.percentage}%</strong></div>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="count" isAnimationActive={false}>
                    {errorDist.bins.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.bin_center >= 0 ? '#159A91' : '#7E99AB'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-text-muted text-[13px]">
                No distribution data
              </div>
            )}
          </div>

          {/* Histogram Stats Summary */}
          {errorDist?.stats && (
            <div className="mt-4 pt-3 border-t border-border-subtle flex flex-col gap-1 text-[11px]">
              <div className="flex items-center justify-between text-text-muted">
                <span>Median Error: <strong className="text-text-primary tabular-nums">{errorDist.stats.median !== null ? `${errorDist.stats.median} MW` : '—'}</strong></span>
                <span>Std Dev: <strong className="text-text-primary tabular-nums">{errorDist.stats.std_dev !== null ? `${errorDist.stats.std_dev} MW` : '—'}</strong></span>
                <span>P10: <strong className="text-text-primary tabular-nums">{errorDist.stats.p10} MW</strong></span>
                <span>P90: <strong className="text-text-primary tabular-nums">{errorDist.stats.p90} MW</strong></span>
              </div>
            </div>
          )}
        </div>

        {/* Right: Hourly Forecast Error Time Series */}
        <div className="lg:col-span-7 bg-surface-card border border-border-subtle p-5 rounded flex flex-col justify-between">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
            <div>
              <h2 className="text-[14px] font-semibold text-text-primary">
                Hourly Forecast Error Time Series ({overall.sample_count} Hours)
              </h2>
              <p className="text-[12px] text-text-muted">
                Net delta vector (Forecast − Actual) across January 2026
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px]">
              <div className="flex items-center gap-1.5 text-text-muted">
                <span className="w-3 h-0.5 bg-chart-primary" />
                <span>Over (+Δ)</span>
              </div>
              <div className="flex items-center gap-1.5 text-text-muted">
                <span className="w-3 h-0.5 bg-chart-tertiary" />
                <span>Under (−Δ)</span>
              </div>
            </div>
          </div>

          {/* Error Vector Time Series Chart */}
          <div className="w-full h-[260px]">
            {timeseries?.hourly_data && timeseries.hourly_data.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={timeseries.hourly_data}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <XAxis
                    dataKey="delivery_time"
                    tickFormatter={(val) => {
                      const d = new Date(val);
                      return `${d.getUTCDate()} ${d.toLocaleString('en-GB', { month: 'short' })}`;
                    }}
                    tick={{ fontSize: 10, fill: '#526B7A' }}
                    axisLine={{ stroke: '#CBD5DB' }}
                    tickLine={false}
                    minTickGap={35}
                  />
                  <YAxis
                    tickFormatter={(val) => `${val > 0 ? '+' : ''}${(val / 1000).toFixed(1)}k`}
                    tick={{ fontSize: 10, fill: '#526B7A' }}
                    axisLine={false}
                    tickLine={false}
                    width={45}
                  />
                  <ReferenceLine y={0} stroke="#142B3B" strokeWidth={1.5} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload || payload.length === 0) return null;
                      const pt = payload[0].payload as HourlyTimeseriesPoint;
                      const d = new Date(pt.delivery_time);
                      return (
                        <div className="bg-surface-card border border-sidebar-surface rounded p-2 text-left tabular-nums text-[11px]">
                          <div className="font-semibold text-text-primary border-b border-border-subtle pb-0.5 mb-1">
                            {d.getUTCDate()} {d.toLocaleString('en-GB', { month: 'short' })} {String(d.getUTCHours()).padStart(2, '0')}:00 UTC
                          </div>
                          <div>Forecast: {pt.forecast_generation.toFixed(1)} MW</div>
                          <div>Actual: {pt.actual_generation.toFixed(1)} MW</div>
                          <div className={`font-semibold ${pt.forecast_error >= 0 ? 'text-chart-primary' : 'text-chart-tertiary'}`}>
                            Error: {pt.forecast_error >= 0 ? '+' : ''}{pt.forecast_error.toFixed(1)} MW
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="forecast_error"
                    stroke="#159A91"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-text-muted text-[13px]">
                No timeseries data
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-border-subtle flex flex-wrap items-center justify-between text-[11px] text-text-muted tabular-nums">
            <span>
              Peak Overforecast:{' '}
              <strong className="text-chart-primary font-semibold">
                +{overall.max_error ? overall.max_error.toFixed(1) : '—'} MW
              </strong>
            </span>
            <span>
              Peak Underforecast:{' '}
              <strong className="text-chart-tertiary font-semibold">
                {overall.min_error ? overall.min_error.toFixed(1) : '—'} MW
              </strong>
            </span>
            <span>
              Total Error Spread:{' '}
              <strong className="text-text-primary font-semibold">
                {overall.max_error && overall.min_error
                  ? `${Math.round(overall.max_error - overall.min_error).toLocaleString('en-GB')} MW`
                  : '—'}
              </strong>
            </span>
          </div>
        </div>
      </div>

      {/* Lower Section: Daily Accuracy Trend & Largest Forecast Errors Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Daily Accuracy Trend & 7-Day Rolling MAE */}
        <div className="lg:col-span-5 bg-surface-card border border-border-subtle p-5 rounded flex flex-col justify-between">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h2 className="text-[14px] font-semibold text-text-primary">
                Daily Accuracy Trend & Rolling MAE
              </h2>
              <p className="text-[12px] text-text-muted">
                Daily discrete MAE vs. smoothed 7-day trailing MAE
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px]">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-sidebar-surface" />
                <span className="text-text-muted">Daily</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-chart-primary" />
                <span className="text-chart-primary font-medium">7-Day MAE</span>
              </div>
            </div>
          </div>

          {/* Trend Chart */}
          <div className="w-full h-[220px]">
            {rollingDailyData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={rollingDailyData}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 9, fill: '#526B7A' }}
                    axisLine={{ stroke: '#CBD5DB' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 9, fill: '#526B7A' }}
                    axisLine={false}
                    tickLine={false}
                    width={38}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload || payload.length === 0) return null;
                      const item = payload[0].payload;
                      return (
                        <div className="bg-surface-card border border-sidebar-surface rounded p-2 text-left tabular-nums text-[11px]">
                          <div className="font-semibold text-text-primary mb-1">
                            {item.fullDate}
                          </div>
                          <div>Daily MAE: {item.dailyMae} MW</div>
                          <div className="text-chart-primary font-medium">
                            7-Day Rolling: {item.rollingMae} MW
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="dailyMae"
                    stroke="#142B3B"
                    strokeWidth={1.5}
                    strokeDasharray="3 3"
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="rollingMae"
                    stroke="#159A91"
                    strokeWidth={2.25}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-text-muted text-[13px]">
                No daily trend observations
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-border-subtle flex items-start gap-2 text-[11px] text-text-muted">
            <Icon name="trending_up" className="text-chart-primary text-[15px] shrink-0 mt-0.5" />
            <p>
              Smoothed 7-day rolling window tracks multi-day weather regime transitions and model divergence trends.
            </p>
          </div>
        </div>

        {/* Right: Largest Forecast Error Events Table */}
        <div className="lg:col-span-7 bg-surface-card border border-border-subtle rounded flex flex-col justify-between overflow-hidden">
          <div className="p-4 border-b border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-[14px] font-semibold text-text-primary">
                Largest Forecast Error Events (Top Tail Deviations)
              </h2>
              <p className="text-[12px] text-text-muted">
                Ranked tail deviations evaluated for the applied {cutoffHour}:00 cutoff
              </p>
            </div>

            {/* Error Type Filter */}
            <div className="flex items-center gap-1 bg-surface-canvas p-0.5 rounded border border-border-strong/40">
              <button
                type="button"
                onClick={() => setErrorTypeFilter('absolute')}
                className={`px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                  errorTypeFilter === 'absolute'
                    ? 'bg-sidebar-surface text-sidebar-text font-semibold'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                |Absolute|
              </button>
              <button
                type="button"
                onClick={() => setErrorTypeFilter('overforecast')}
                className={`px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                  errorTypeFilter === 'overforecast'
                    ? 'bg-sidebar-surface text-sidebar-text font-semibold'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                Over (+Δ)
              </button>
              <button
                type="button"
                onClick={() => setErrorTypeFilter('underforecast')}
                className={`px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                  errorTypeFilter === 'underforecast'
                    ? 'bg-sidebar-surface text-sidebar-text font-semibold'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                Under (−Δ)
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="bg-surface-canvas border-b border-border-subtle text-text-muted text-[10px] uppercase tracking-wider font-semibold">
                  <th className="py-2.5 px-3 w-10 text-center">#</th>
                  <th className="py-2.5 px-3">Delivery Interval (UTC)</th>
                  <th className="py-2.5 px-3 text-right">Forecast (MW)</th>
                  <th className="py-2.5 px-3 text-right">Actual Outturn (MW)</th>
                  <th className="py-2.5 px-3 text-right">Error (Δ MW)</th>
                  <th className="py-2.5 px-3 text-center">Direction</th>
                  <th className="py-2.5 px-3">Run ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle text-[12px] tabular-nums">
                {topErrors?.top_errors && topErrors.top_errors.length > 0 ? (
                  topErrors.top_errors.map((r) => {
                    const isOver = r.forecast_error >= 0;
                    return (
                      <tr key={r.rank} className="hover:bg-surface-canvas/80 transition-colors">
                        <td className="py-2 px-3 text-center text-text-muted font-medium text-[11px]">
                          {r.rank}
                        </td>
                        <td className="py-2 px-3 text-text-primary font-medium">
                          {new Date(r.delivery_time).toLocaleDateString('en-GB', {
                            day: '2-digit',
                            month: 'short',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}{' '}
                          UTC
                        </td>
                        <td className="py-2 px-3 text-right text-text-muted">
                          {r.forecast_generation.toFixed(1)}
                        </td>
                        <td className="py-2 px-3 text-right text-text-muted">
                          {r.actual_generation.toFixed(1)}
                        </td>
                        <td className="py-2 px-3 text-right font-semibold text-text-primary">
                          {isOver ? '+' : ''}{r.forecast_error.toFixed(1)} MW
                        </td>
                        <td className="py-2 px-3 text-center">
                          <span
                            className={`inline-block px-1.5 py-0.5 rounded-sm text-[10px] font-semibold ${
                              isOver
                                ? 'bg-surface-canvas text-chart-primary'
                                : 'bg-surface-canvas text-chart-tertiary'
                            }`}
                          >
                            {isOver ? 'OVER' : 'UNDER'}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-text-faint text-[11px]">
                          {new Date(r.forecast_publish_time).toLocaleTimeString('en-GB', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}{' '}
                          UTC
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-text-muted text-[12px]">
                      No error records available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
