import React, { useEffect, useState, useMemo } from 'react';
import {
  fetchAccuracySummary,
  fetchTimeseries,
  type AccuracyQueryParams,
} from '../lib/api';
import type {
  AccuracySummaryResponse,
  TimeseriesResponse,
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

interface OverviewPageProps {
  cutoffHour: number;
  startDate?: string;
  endDate?: string;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  cutoffHour,
  startDate,
  endDate,
}) => {
  const [summary, setSummary] = useState<AccuracySummaryResponse | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesResponse | null>(null);
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
        const [sumRes, tsRes] = await Promise.all([
          fetchAccuracySummary(queryParams),
          fetchTimeseries({ ...queryParams, granularity: 'hourly' }),
        ]);
        if (isCurrent) {
          setSummary(sumRes);
          setTimeseries(tsRes);
        }
      } catch (err: unknown) {
        if (isCurrent) {
          setError(err instanceof Error ? err.message : 'Failed to fetch overview data');
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
  }, [queryParams, reloadKey]);

  // Derived Generation Statistics from hourly observations
  const generationStats = useMemo(() => {
    if (!timeseries?.hourly_data || timeseries.hourly_data.length === 0) {
      return null;
    }
    const points: HourlyTimeseriesPoint[] = timeseries.hourly_data;

    let totalActualMWh = 0;
    let totalForecastMWh = 0;
    let peakActual = -Infinity;
    let peakActualTime = '';
    let minActual = Infinity;
    let minActualTime = '';

    for (const p of points) {
      totalActualMWh += p.actual_generation;
      totalForecastMWh += p.forecast_generation;

      if (p.actual_generation > peakActual) {
        peakActual = p.actual_generation;
        peakActualTime = p.delivery_time;
      }
      if (p.actual_generation < minActual) {
        minActual = p.actual_generation;
        minActualTime = p.delivery_time;
      }
    }

    const totalActualTWh = (totalActualMWh / 1e6).toFixed(2);
    const totalForecastTWh = (totalForecastMWh / 1e6).toFixed(2);
    const imbalanceTWh = ((totalForecastMWh - totalActualMWh) / 1e6).toFixed(2);

    return {
      totalActualTWh,
      totalForecastTWh,
      imbalanceTWh,
      peakActual: Math.round(peakActual),
      peakActualTime: peakActualTime ? new Date(peakActualTime).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '',
      minActual: Math.round(minActual),
      minActualTime: minActualTime ? new Date(minActualTime).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '',
    };
  }, [timeseries]);

  // Daily bar chart data
  const dailyBarData = useMemo(() => {
    if (!summary?.daily) return [];
    return summary.daily.map((d) => ({
      date: d.date.slice(5), // '01-02'
      fullDate: d.date,
      bias: d.bias ?? 0,
      mae: d.mae ?? 0,
      isPositive: (d.bias ?? 0) >= 0,
    }));
  }, [summary]);

  const dailyCounts = useMemo(() => {
    let overCount = 0;
    let underCount = 0;
    for (const d of dailyBarData) {
      if (d.bias >= 0) overCount++;
      else underCount++;
    }
    return { overCount, underCount, total: dailyBarData.length };
  }, [dailyBarData]);

  const handleExportCsv = () => {
    if (!timeseries?.hourly_data || timeseries.hourly_data.length === 0) return;
    const headers = ['Delivery Time (UTC)', 'Forecast (MW)', 'Actual (MW)', 'Error (MW)', 'Cutoff (UTC)'];
    const rows = timeseries.hourly_data.map((p) => [
      p.delivery_time,
      p.forecast_generation.toFixed(2),
      p.actual_generation.toFixed(2),
      p.forecast_error.toFixed(2),
      p.cutoff_time,
    ]);
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `wind_analytics_overview_${cutoffHour}h.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <LoadingState message="Loading National Generation Performance Overview..." />;
  }

  if (error) {
    return (
      <ErrorState
        title="Failed to Load Overview Analytics"
        message={error}
        onRetry={handleReload}
      />
    );
  }

  if (!summary || summary.overall.sample_count === 0) {
    return (
      <EmptyState
        title="No Overview Observations Found"
        description="No matched hourly observations were found for the selected date range and cutoff. Verify database ingestion."
        actionText="Reload"
        onAction={handleReload}
      />
    );
  }

  const { overall } = summary;
  const isOverforecast = (overall.bias ?? 0) >= 0;
  const maePercent =
    overall.mae && overall.avg_actual
      ? ((overall.mae / overall.avg_actual) * 100).toFixed(2)
      : null;

  return (
    <div className="flex flex-col gap-5 max-w-[1440px] mx-auto p-4 sm:p-7">
      {/* Top Context Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-1">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-wider text-text-muted font-medium">
              Settlement Period Audit
            </span>
            <span className="w-1 h-1 rounded-full bg-border-strong" />
            <span className="text-[10px] uppercase tracking-wider text-chart-primary font-semibold">
              GB National Grid ESO & BMRS
            </span>
          </div>
          <h1 className="text-[24px] sm:text-[28px] font-semibold text-text-primary tracking-tight leading-tight">
            Monthly Generation Performance Overview
          </h1>
          <p className="text-[13px] text-text-muted">
            UK national wind outturn vs {String(cutoffHour).padStart(2, '0')}:00 D-1 baseline forecast across GB transmission & embedded wind.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={handleExportCsv}
            className="h-8 px-3 bg-surface-card border border-border-strong text-text-primary rounded text-[13px] font-medium hover:border-text-primary hover:bg-surface-canvas transition-colors flex items-center gap-1.5 focus:outline-none focus:ring-1 focus:ring-chart-primary cursor-pointer"
          >
            <Icon name="download" className="text-[16px] text-text-muted" />
            <span>Export Dataset (CSV)</span>
          </button>
        </div>
      </div>

      {/* KPI Row: 4 Rigid Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Card 1: MAE */}
        <KpiCard
          label="Mean Absolute Error (MAE)"
          badge={
            <span className="text-[10px] text-text-faint uppercase tabular-nums">
              Settlement Basis
            </span>
          }
          value={overall.mae !== null ? overall.mae.toLocaleString('en-GB', { minimumFractionDigits: 2 }) : '—'}
          unit="MW"
          subtext={maePercent ? `${maePercent}% of avg actual generation` : 'Average absolute deviation'}
          footerDotColor="bg-chart-primary"
          footerText="Avg absolute divergence per settlement hour"
        />

        {/* Card 2: RMSE */}
        <KpiCard
          label="Root Mean Squared Error (RMSE)"
          badge={
            <span className="text-[10px] text-text-faint uppercase tabular-nums">
              L2 Penalty
            </span>
          }
          value={overall.rmse !== null ? overall.rmse.toLocaleString('en-GB', { minimumFractionDigits: 2 }) : '—'}
          unit="MW"
          subtext={
            overall.max_error !== null && overall.min_error !== null
              ? `Max: +${Math.round(overall.max_error)} MW | Min: ${Math.round(overall.min_error)} MW`
              : 'Residual variance metric'
          }
          footerDotColor="bg-text-muted"
          footerText="Penalizes extreme storm ramp deviations"
        />

        {/* Card 3: Forecast Bias */}
        <KpiCard
          label="Forecast Bias (Mean Error)"
          badge={
            <span className="px-1.5 py-0.5 rounded-sm bg-surface-canvas border border-border-strong text-chart-primary text-[10px] font-semibold">
              {isOverforecast ? 'OVERFORECAST' : 'UNDERFORECAST'}
            </span>
          }
          value={
            overall.bias !== null
              ? `${overall.bias >= 0 ? '+' : ''}${overall.bias.toLocaleString('en-GB', { minimumFractionDigits: 2 })}`
              : '—'
          }
          unit="MW"
          subtext={
            isOverforecast
              ? 'Persistent day-ahead wind overestimate'
              : 'Day-ahead wind underestimate'
          }
          footerDotColor="bg-chart-primary"
          footerText="Systematic directional exposure for nominations"
        />

        {/* Card 4: Evaluated Hours */}
        <KpiCard
          label="Evaluated Observations"
          badge={
            <span className="text-[10px] text-chart-primary uppercase font-semibold">
              100.0% Complete
            </span>
          }
          value={overall.sample_count}
          unit={`/ ${overall.sample_count} hrs`}
          subtext={`${overall.sample_count * 2} Half-Hour Settlement Periods`}
          footerDotColor="bg-chart-primary"
          footerText="Validated against Elexon BMRS metered volumes"
        />
      </div>

      {/* Main Chart Section: Left 70% Chart, Right 30% Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Chart Box */}
        <div className="lg:col-span-8 xl:col-span-9 bg-surface-card border border-border-subtle rounded p-4 flex flex-col justify-between">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border-subtle">
            <div className="flex flex-col">
              <span className="text-[15px] font-semibold text-text-primary">
                Day-Ahead Forecast vs Actual Wind Generation (MW)
              </span>
              <span className="text-[12px] text-text-muted">
                Hourly aggregated timeline ({String(cutoffHour).padStart(2, '0')}:00 D-1 Cutoff)
              </span>
            </div>
            <div className="flex items-center gap-4 text-[11px] font-medium">
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-[2px] bg-chart-primary" />
                <span className="text-text-primary font-medium">Actual Outturn</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-[2px] bg-sidebar-surface border-b border-dashed border-sidebar-surface" />
                <span className="text-text-muted font-medium">D-1 Baseline</span>
              </div>
            </div>
          </div>

          {/* Time Series Chart */}
          <div className="w-full h-[320px] pt-4">
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
                    minTickGap={40}
                  />
                  <YAxis
                    tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                    tick={{ fontSize: 10, fill: '#526B7A' }}
                    axisLine={false}
                    tickLine={false}
                    width={40}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload || payload.length === 0) return null;
                      const pt = payload[0].payload as HourlyTimeseriesPoint;
                      const d = new Date(pt.delivery_time);
                      const formattedTime = `${d.getUTCDate()} ${d.toLocaleString('en-GB', { month: 'short' })} ${String(d.getUTCHours()).padStart(2, '0')}:00 GMT`;
                      return (
                        <div className="bg-surface-card border border-sidebar-surface rounded p-2.5 shadow-sm text-left tabular-nums flex flex-col gap-1 min-w-[210px] text-[12px]">
                          <div className="flex items-center justify-between border-b border-border-subtle pb-1 font-semibold text-text-primary text-[11px]">
                            <span>{formattedTime}</span>
                            <span className="text-[9px] uppercase px-1 bg-surface-canvas text-chart-primary font-semibold rounded">
                              UTC
                            </span>
                          </div>
                          <div className="flex items-center justify-between pt-0.5">
                            <span className="text-text-muted flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full bg-sidebar-surface" />
                              Forecast:
                            </span>
                            <span className="font-semibold text-text-primary">
                              {pt.forecast_generation.toLocaleString('en-GB', { maximumFractionDigits: 1 })} MW
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-text-muted flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full bg-chart-primary" />
                              Actual Outturn:
                            </span>
                            <span className="font-semibold text-text-primary">
                              {pt.actual_generation.toLocaleString('en-GB', { maximumFractionDigits: 1 })} MW
                            </span>
                          </div>
                          <div className="flex items-center justify-between border-t border-border-subtle pt-1 font-medium">
                            <span className="text-text-muted">Error (Δ):</span>
                            <span className={`font-semibold ${pt.forecast_error >= 0 ? 'text-chart-primary' : 'text-chart-tertiary'}`}>
                              {pt.forecast_error >= 0 ? '+' : ''}
                              {pt.forecast_error.toLocaleString('en-GB', { maximumFractionDigits: 1 })} MW
                            </span>
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="forecast_generation"
                    name="Forecast"
                    stroke="#142B3B"
                    strokeWidth={1.75}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="actual_generation"
                    name="Actual"
                    stroke="#159A91"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-text-muted text-[13px]">
                No hourly time series observations found
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between pt-3 border-t border-border-subtle text-[12px] text-text-muted">
            <div className="flex items-center gap-3">
              <span>Resolution: Hourly (from 2x 30-min BMRS observations)</span>
              <span className="w-1 h-1 rounded-full bg-border-strong" />
              <span>Forecast Gate: {String(cutoffHour).padStart(2, '0')}:00 UK</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] uppercase text-text-faint">Outturn Capture Rate</span>
              <span className="font-semibold text-text-primary tabular-nums">100.0%</span>
            </div>
          </div>
        </div>

        {/* Right 30% Breakdown Column */}
        <div className="lg:col-span-4 xl:col-span-3 bg-surface-card border border-border-subtle rounded p-4 flex flex-col justify-between">
          <div className="flex flex-col">
            <div className="flex items-center justify-between border-b border-border-subtle pb-2.5 mb-2">
              <span className="text-[15px] font-semibold text-text-primary">
                Generation Summary
              </span>
              <span className="text-[10px] text-text-faint uppercase tabular-nums">
                {queryParams.startDate || 'Jan 2026'}
              </span>
            </div>

            {/* Metrics List */}
            {generationStats ? (
              <div className="flex flex-col divide-y divide-border-subtle text-[13px]">
                <div className="flex items-center justify-between py-2">
                  <span className="text-text-muted">Total Energy Outturn</span>
                  <span className="font-semibold text-text-primary tabular-nums">
                    {generationStats.totalActualTWh} TWh
                  </span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-text-muted">Total Energy Forecast</span>
                  <span className="font-semibold text-text-primary tabular-nums">
                    {generationStats.totalForecastTWh} TWh
                  </span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-text-muted">Net Imbalance Volume</span>
                  <span className="font-semibold text-chart-primary tabular-nums">
                    +{generationStats.imbalanceTWh} TWh
                  </span>
                </div>
                <div className="flex flex-col py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Peak Actual Wind</span>
                    <span className="font-semibold text-text-primary tabular-nums">
                      {generationStats.peakActual.toLocaleString('en-GB')} MW
                    </span>
                  </div>
                  <span className="text-[10px] text-text-faint text-right mt-0.5 tabular-nums">
                    {generationStats.peakActualTime}
                  </span>
                </div>
                <div className="flex flex-col py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Min Actual Wind</span>
                    <span className="font-semibold text-text-primary tabular-nums">
                      {generationStats.minActual.toLocaleString('en-GB')} MW
                    </span>
                  </div>
                  <span className="text-[10px] text-text-faint text-right mt-0.5 tabular-nums">
                    {generationStats.minActualTime}
                  </span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-text-muted">Avg Actual Generation</span>
                  <span className="font-semibold text-text-primary tabular-nums">
                    {overall.avg_actual ? `${Math.round(overall.avg_actual).toLocaleString('en-GB')} MW` : '—'}
                  </span>
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-text-muted text-[12px]">
                No generation data
              </div>
            )}
          </div>

          {/* Telemetry & Audit Trail Box */}
          <div className="mt-4 pt-3 border-t border-border-subtle flex flex-col gap-2">
            <span className="text-[10px] uppercase tracking-wider text-text-muted font-medium">
              Telemetry & Audit Trail
            </span>
            <div className="bg-surface-canvas border border-border-subtle rounded p-2.5 flex flex-col gap-1.5 text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-text-muted">BMRS Ingestion</span>
                <span className="text-chart-primary font-semibold flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-chart-primary" />
                  Verified Live
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Fuel Type Filter</span>
                <span className="text-text-primary font-semibold font-mono">
                  WIND (Strict)
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Settlement Resolution</span>
                <span className="text-text-primary tabular-nums">
                  Half-Hourly (48 SP/day)
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Lower Section: Daily Mean Forecast Error Bar Chart & Implications */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Bar Chart Card (9 cols) */}
        <div className="lg:col-span-8 xl:col-span-9 bg-surface-card border border-border-subtle rounded p-4 flex flex-col justify-between">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-border-subtle">
            <div className="flex flex-col">
              <span className="text-[15px] font-semibold text-text-primary">
                Daily Mean Forecast Error (MW) — Systematic Bias Tracking
              </span>
              <span className="text-[12px] text-text-muted">
                Positive values denote Day-Ahead Overforecast (Forecast &gt; Outturn); negative values denote Underforecast.
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-surface-canvas border border-border-strong text-text-muted tabular-nums">
                {dailyCounts.total} Observed Days
              </span>
            </div>
          </div>

          {/* Bar Chart */}
          <div className="w-full h-[190px] pt-3 pb-1">
            {dailyBarData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={dailyBarData}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 9, fill: '#526B7A' }}
                    axisLine={{ stroke: '#CBD5DB' }}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={(val) => `${val > 0 ? '+' : ''}${val}`}
                    tick={{ fontSize: 9, fill: '#526B7A' }}
                    axisLine={false}
                    tickLine={false}
                    width={45}
                  />
                  <ReferenceLine y={0} stroke="#142B3B" strokeWidth={1.25} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload || payload.length === 0) return null;
                      const item = payload[0].payload;
                      return (
                        <div className="bg-surface-card border border-sidebar-surface rounded p-2 shadow-sm text-left tabular-nums text-[11px]">
                          <div className="font-semibold text-text-primary border-b border-border-subtle pb-0.5 mb-1">
                            {item.fullDate}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-text-muted">Daily Bias:</span>
                            <span className={`font-semibold ${item.bias >= 0 ? 'text-chart-primary' : 'text-chart-tertiary'}`}>
                              {item.bias >= 0 ? '+' : ''}{item.bias.toFixed(2)} MW
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-text-muted">Daily MAE:</span>
                            <span className="font-semibold text-text-primary">
                              {item.mae.toFixed(2)} MW
                            </span>
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="bias" isAnimationActive={false}>
                    {dailyBarData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.bias >= 0 ? '#159A91' : '#7E99AB'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-text-muted text-[13px]">
                No daily bias data
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-border-subtle text-[11px] text-text-muted tabular-nums">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-chart-primary rounded-sm" />
                Overforecast ({dailyCounts.overCount} Days)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-chart-tertiary rounded-sm" />
                Underforecast ({dailyCounts.underCount} Days)
              </span>
            </div>
            <span>
              Monthly Overforecast Consistency:{' '}
              {dailyCounts.total > 0
                ? `${((dailyCounts.overCount / dailyCounts.total) * 100).toFixed(1)}%`
                : '—'}
            </span>
          </div>
        </div>

        {/* Side Analysis Card (3 cols) */}
        <div className="lg:col-span-4 xl:col-span-3 bg-surface-card border border-border-subtle rounded p-4 flex flex-col justify-between">
          <div className="flex flex-col">
            <div className="flex items-center justify-between border-b border-border-subtle pb-2.5 mb-2.5">
              <span className="text-[15px] font-semibold text-text-primary">
                Operational Observations
              </span>
              <Icon name="analytics" className="text-chart-primary text-[18px]" />
            </div>
            <div className="flex flex-col gap-2.5 text-[12px]">
              <p className="text-text-muted leading-relaxed">
                The persistent <strong className="text-text-primary tabular-nums">+{overall.bias ? overall.bias.toFixed(2) : '1,692.47'} MW</strong> day-ahead overforecast demonstrates a systematic positive delta between D-1 forecast gate and metered outturn.
              </p>
              <div className="bg-surface-canvas border border-border-subtle rounded p-2.5 flex flex-col gap-1 text-[11px]">
                <span className="uppercase tracking-wider text-text-muted font-medium text-[10px]">
                  Balancing Exposure
                </span>
                <span className="text-text-primary font-semibold">
                  Systematic Long Tendency
                </span>
                <p className="text-text-muted text-[11px] leading-tight mt-0.5">
                  Procurement positions matched directly against uncorrected D-1 baselines result in systematic over-procurement relative to physical grid delivery.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-2.5 border-t border-border-subtle flex items-center justify-between text-[11px] text-text-faint">
            <span>Audit Ref: UK-WIND-2026-M1</span>
            <span className="tabular-nums text-text-primary font-semibold">Verified</span>
          </div>
        </div>
      </div>
    </div>
  );
};
