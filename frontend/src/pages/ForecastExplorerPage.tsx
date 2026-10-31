import React, { useEffect, useState, useMemo } from 'react';
import {
  fetchTimeseries,
  type AccuracyQueryParams,
} from '../lib/api';
import type {
  TimeseriesResponse,
  HourlyTimeseriesPoint,
} from '../lib/types';
import { LoadingState, ErrorState } from '../components/common/StatusStates';
import { Icon } from '../components/common/Icon';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';

interface ForecastExplorerPageProps {
  cutoffHour: number;
  onCutoffChange: (hour: number) => void;
  startDate?: string;
  endDate?: string;
  onDateChange?: (start: string, end: string) => void;
}

type DirectionFilter = 'all' | 'over' | 'under' | 'extreme';

export const ForecastExplorerPage: React.FC<ForecastExplorerPageProps> = ({
  cutoffHour,
  onCutoffChange,
  startDate = '2026-01-01',
  endDate = '2026-01-31',
  onDateChange,
}) => {
  const [timeseries, setTimeseries] = useState<TimeseriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [directionFilter, setDirectionFilter] = useState<DirectionFilter>('all');
  const [selectedPoint, setSelectedPoint] = useState<HourlyTimeseriesPoint | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
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
        const res = await fetchTimeseries({ ...queryParams, granularity: 'hourly' });
        if (isCurrent) {
          setTimeseries(res);
          if (res.hourly_data && res.hourly_data.length > 0) {
            setSelectedPoint(res.hourly_data[0]);
          }
        }
      } catch (err: unknown) {
        if (isCurrent) {
          setError(err instanceof Error ? err.message : 'Failed to fetch forecast explorer data');
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

  // Filter observations
  const filteredRecords = useMemo(() => {
    if (!timeseries?.hourly_data) return [];
    let list = timeseries.hourly_data;

    // Direction filter
    if (directionFilter === 'over') {
      list = list.filter((r) => r.forecast_error > 0);
    } else if (directionFilter === 'under') {
      list = list.filter((r) => r.forecast_error < 0);
    } else if (directionFilter === 'extreme') {
      list = list.filter((r) => r.abs_error >= 2000);
    }

    // Search filter (date/hour)
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter((r) => r.delivery_time.toLowerCase().includes(q));
    }

    return list;
  }, [timeseries, directionFilter, searchTerm]);

  // Computed summary metrics for the filtered subset
  const filteredMetrics = useMemo(() => {
    if (filteredRecords.length === 0) return null;
    let sumAbs = 0;
    let sumErr = 0;
    for (const r of filteredRecords) {
      sumAbs += r.abs_error;
      sumErr += r.forecast_error;
    }
    const mae = sumAbs / filteredRecords.length;
    const bias = sumErr / filteredRecords.length;
    return {
      count: filteredRecords.length,
      mae: mae.toFixed(2),
      bias: (bias >= 0 ? '+' : '') + bias.toFixed(2),
    };
  }, [filteredRecords]);

  // Quick preset dates
  const handlePreset = (preset: 'all' | 'storm' | 'cold') => {
    if (!onDateChange) return;
    if (preset === 'all') {
      onDateChange('2026-01-01', '2026-01-31');
    } else if (preset === 'storm') {
      onDateChange('2026-01-16', '2026-01-20');
    } else if (preset === 'cold') {
      onDateChange('2026-01-21', '2026-01-25');
    }
  };

  const handleExportCsv = () => {
    if (filteredRecords.length === 0) return;
    const headers = [
      'Delivery Time (UTC)',
      'Selected Forecast (MW)',
      'Actual Outturn (MW)',
      'Forecast Error (MW)',
      'Absolute Error (MW)',
      'Run Publish Time (UTC)',
      'Applied Cutoff (UTC)',
    ];
    const rows = filteredRecords.map((p) => [
      p.delivery_time,
      p.forecast_generation.toFixed(2),
      p.actual_generation.toFixed(2),
      p.forecast_error.toFixed(2),
      p.abs_error.toFixed(2),
      p.forecast_publish_time,
      p.cutoff_time,
    ]);
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `forecast_explorer_${cutoffHour}h.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <LoadingState message="Loading Forecast Explorer & Settlement Audit..." />;
  }

  if (error) {
    return (
      <ErrorState
        title="Failed to Load Forecast Explorer"
        message={error}
        onRetry={handleReload}
      />
    );
  }

  return (
    <div className="flex flex-col gap-4 max-w-[1440px] mx-auto p-4 sm:p-7">
      {/* Breadcrumb & Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-1 gap-2">
        <div>
          <div className="flex items-center gap-2 text-[10px] text-text-muted uppercase tracking-wider mb-1 font-medium">
            <span>National Grid ESO / BMRS</span>
            <span className="text-border-strong">/</span>
            <span>Wind Power Outturn</span>
            <span className="text-border-strong">/</span>
            <span className="text-chart-primary font-semibold">
              Forecast Explorer
            </span>
          </div>
          <h1 className="text-[24px] sm:text-[28px] font-semibold text-text-primary tracking-tight">
            Forecast Explorer & Settlement Audit
          </h1>
          <p className="text-[13px] text-text-muted mt-0.5">
            Hourly settlement period breakdown, latest pre-cutoff forecast version selection, and metered actuals.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="bg-surface-card border border-border-subtle px-3 py-1.5 rounded flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-chart-primary" />
            <span className="text-[11px] font-semibold text-text-primary uppercase tracking-normal">
              BMRS Settled Outturn
            </span>
          </div>
          <div className="bg-surface-card border border-border-subtle px-3 py-1.5 rounded text-[11px] tabular-nums text-text-muted">
            Ref: <span className="font-semibold text-text-primary">ELEX-WF-744P</span>
          </div>
        </div>
      </div>

      {/* Filter & Control Strip */}
      <div className="bg-surface-card border border-border-subtle p-3.5 rounded flex flex-col gap-3">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
          {/* Preset Buttons */}
          <div className="md:col-span-5 flex flex-col gap-1">
            <label className="text-[10px] text-text-muted uppercase tracking-wider font-medium">
              Evaluation Slice Window
            </label>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => handlePreset('all')}
                className={`h-8 px-2.5 rounded text-[12px] font-medium border transition-colors ${
                  startDate === '2026-01-01' && endDate === '2026-01-31'
                    ? 'bg-sidebar-surface text-sidebar-text border-sidebar-surface'
                    : 'bg-surface-canvas text-text-muted border-border-strong hover:text-text-primary'
                }`}
              >
                Full Month (Jan 1–31)
              </button>
              <button
                type="button"
                onClick={() => handlePreset('storm')}
                className={`h-8 px-2.5 rounded text-[12px] font-medium border transition-colors ${
                  startDate === '2026-01-16' && endDate === '2026-01-20'
                    ? 'bg-sidebar-surface text-sidebar-text border-sidebar-surface'
                    : 'bg-surface-canvas text-text-muted border-border-strong hover:text-text-primary'
                }`}
              >
                Storm Ramp (Jan 16–20)
              </button>
              <button
                type="button"
                onClick={() => handlePreset('cold')}
                className={`h-8 px-2.5 rounded text-[12px] font-medium border transition-colors ${
                  startDate === '2026-01-21' && endDate === '2026-01-25'
                    ? 'bg-sidebar-surface text-sidebar-text border-sidebar-surface'
                    : 'bg-surface-canvas text-text-muted border-border-strong hover:text-text-primary'
                }`}
              >
                Trough (Jan 21–25)
              </button>
            </div>
          </div>

          {/* Cutoff Gate Timing Toggles */}
          <div className="md:col-span-4 flex flex-col gap-1">
            <label className="text-[10px] text-text-muted uppercase tracking-wider font-medium">
              Decision Cutoff Gate
            </label>
            <div className="grid grid-cols-4 h-8 bg-surface-canvas p-0.5 rounded border border-border-strong/40">
              {[11, 12, 15, 17].map((hour) => (
                <button
                  key={hour}
                  type="button"
                  onClick={() => onCutoffChange(hour)}
                  className={`text-[11px] font-medium rounded transition-colors text-center ${
                    cutoffHour === hour
                      ? 'bg-sidebar-surface text-sidebar-text font-semibold shadow-xs'
                      : 'text-text-muted hover:text-text-primary'
                  }`}
                >
                  {hour}:00 DA
                </button>
              ))}
            </div>
          </div>

          {/* Actions: CSV Export */}
          <div className="md:col-span-3 flex flex-col gap-1 md:items-end justify-end">
            <label className="text-[10px] text-text-muted uppercase tracking-wider font-medium">
              Actions
            </label>
            <button
              type="button"
              onClick={handleExportCsv}
              className="h-8 px-3 rounded bg-surface-canvas border border-border-strong text-text-primary text-[12px] font-medium hover:bg-surface-container flex items-center gap-1.5 cursor-pointer"
            >
              <Icon name="file_download" className="text-[16px] text-chart-primary" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>

        {/* Forecast Version Scope Notice */}
        <div className="bg-surface-canvas border border-border-subtle p-2 rounded text-[11px] text-text-muted flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon name="info" className="text-chart-primary text-[15px]" />
            <span>
              <strong>Scope Notice:</strong> Displaying verified matched observations for the active <strong>{cutoffHour}:00 UK</strong> decision cutoff. Side-by-side unaggregated multi-run WINDFOR version comparison requires a dedicated historical revisions API.
            </span>
          </div>
        </div>

        {/* Quick Triage Filter Strip */}
        <div className="flex flex-wrap items-center justify-between pt-2.5 border-t border-border-subtle gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[10px] text-text-muted uppercase tracking-wider font-medium mr-1">
              Triage Filter:
            </span>
            <button
              type="button"
              onClick={() => setDirectionFilter('all')}
              className={`h-6 px-2.5 rounded text-[11px] font-medium transition-colors ${
                directionFilter === 'all'
                  ? 'bg-sidebar-surface text-sidebar-text'
                  : 'bg-surface-canvas text-text-muted hover:text-text-primary'
              }`}
            >
              All Observations
            </button>
            <button
              type="button"
              onClick={() => setDirectionFilter('over')}
              className={`h-6 px-2.5 rounded text-[11px] font-medium transition-colors ${
                directionFilter === 'over'
                  ? 'bg-sidebar-surface text-sidebar-text'
                  : 'bg-surface-canvas text-text-muted hover:text-text-primary'
              }`}
            >
              Overforecast Only (+Δ)
            </button>
            <button
              type="button"
              onClick={() => setDirectionFilter('under')}
              className={`h-6 px-2.5 rounded text-[11px] font-medium transition-colors ${
                directionFilter === 'under'
                  ? 'bg-sidebar-surface text-sidebar-text'
                  : 'bg-surface-canvas text-text-muted hover:text-text-primary'
              }`}
            >
              Underforecast Only (−Δ)
            </button>
            <button
              type="button"
              onClick={() => setDirectionFilter('extreme')}
              className={`h-6 px-2.5 rounded text-[11px] font-medium transition-colors ${
                directionFilter === 'extreme'
                  ? 'bg-sidebar-surface text-sidebar-text'
                  : 'bg-surface-canvas text-text-muted hover:text-text-primary'
              }`}
            >
              Peak Errors (&ge;2,000 MW)
            </button>
          </div>

          {filteredMetrics && (
            <div className="flex items-center gap-4 text-text-muted text-[11px] tabular-nums">
              <span>
                Matching Hours:{' '}
                <strong className="text-text-primary font-semibold">
                  {filteredMetrics.count}
                </strong>
              </span>
              <span>
                MAE:{' '}
                <strong className="text-text-primary font-semibold">
                  {filteredMetrics.mae} MW
                </strong>
              </span>
              <span>
                Bias:{' '}
                <strong className="text-text-primary font-semibold">
                  {filteredMetrics.bias} MW
                </strong>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Visual Profile Trace Chart */}
      <div className="bg-surface-card border border-border-subtle rounded p-4 flex flex-col gap-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border-subtle">
          <div className="flex items-center gap-3">
            <span className="text-[14px] font-semibold text-text-primary">
              Profile Trace Timeline
            </span>
            <span className="text-[10px] bg-surface-canvas text-text-muted px-2 py-0.5 rounded font-mono">
              {startDate} 00:00 → {endDate} 23:00 UTC
            </span>
          </div>

          {/* Chart Legend */}
          <div className="flex items-center gap-5 text-[11px]">
            <div className="flex items-center gap-2">
              <span className="w-3 h-1 bg-chart-primary rounded-full" />
              <span className="text-text-primary font-medium">Actual Generation</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-1 bg-chart-secondary rounded-full" />
              <span className="text-text-primary font-medium">
                {cutoffHour}:00 D-1 Forecast
              </span>
            </div>
          </div>
        </div>

        {/* Selected Hour Inspection Banner */}
        {selectedPoint && (
          <div className="bg-surface-canvas border border-border-subtle p-2.5 rounded flex flex-col md:flex-row md:items-center justify-between text-text-primary text-[12px] tabular-nums gap-2">
            <div className="flex items-center gap-2">
              <Icon name="verified" className="text-chart-primary text-[16px]" />
              <span className="font-semibold text-text-primary">
                Inspecting Delivery:{' '}
                {new Date(selectedPoint.delivery_time).toLocaleDateString('en-GB', {
                  day: '2-digit',
                  month: 'short',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}{' '}
                UTC
              </span>
              <span className="text-text-muted">|</span>
              <span className="text-text-muted text-[11px]">
                Run ID: {new Date(selectedPoint.forecast_publish_time).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} UTC
              </span>
            </div>

            <div className="flex items-center gap-5">
              <div>
                Forecast: <strong className="font-semibold text-text-primary">{selectedPoint.forecast_generation.toFixed(1)} MW</strong>
              </div>
              <div>
                Actual: <strong className="font-semibold text-chart-primary">{selectedPoint.actual_generation.toFixed(1)} MW</strong>
              </div>
              <div>
                Error:{' '}
                <span className={`px-2 py-0.5 rounded font-semibold ${selectedPoint.forecast_error >= 0 ? 'bg-surface-card text-chart-primary' : 'bg-surface-card text-chart-tertiary'}`}>
                  {selectedPoint.forecast_error >= 0 ? '+' : ''}
                  {selectedPoint.forecast_error.toFixed(1)} MW
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Chart Viewport */}
        <div className="w-full h-[260px] pt-2">
          {timeseries?.hourly_data && timeseries.hourly_data.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={timeseries.hourly_data}
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                onClick={(state) => {
                  const payload = (state as { activePayload?: Array<{ payload?: HourlyTimeseriesPoint }> })?.activePayload;
                  if (payload && payload.length > 0 && payload[0].payload) {
                    setSelectedPoint(payload[0].payload);
                  }
                }}
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
                  tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 10, fill: '#526B7A' }}
                  axisLine={false}
                  tickLine={false}
                  width={38}
                />
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
                  dataKey="forecast_generation"
                  stroke="#142B3B"
                  strokeWidth={1.75}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="actual_generation"
                  stroke="#159A91"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-text-muted text-[13px]">
              No observations for current slice
            </div>
          )}
        </div>
      </div>

      {/* Detailed Settlement Period Breakdown Data Table */}
      <div className="bg-surface-card border border-border-subtle rounded flex flex-col overflow-hidden">
        <div className="p-3.5 border-b border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <span className="text-[14px] font-semibold text-text-primary">
              Delivery Hour Settlement Observations
            </span>
            <span className="text-[11px] text-text-muted tabular-nums">
              ({filteredRecords.length} records matching)
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <input
                type="text"
                placeholder="Search date (e.g. 2026-01-18)..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-7 px-2.5 text-[11px] bg-surface-canvas border border-border-strong rounded text-text-primary focus:outline-none focus:ring-1 focus:ring-chart-primary w-48 sm:w-60"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => setSearchTerm('')}
                  className="absolute right-2 top-1.5 text-text-muted hover:text-text-primary text-[12px]"
                >
                  ×
                </button>
              )}
            </div>
          </div>
        </div>

        {/* High Density Table */}
        <div className="overflow-x-auto max-h-[440px]">
          <table className="w-full border-collapse text-left">
            <thead className="sticky top-0 z-10 bg-surface-canvas border-b border-border-subtle text-text-muted text-[10px] uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-2.5 px-3 w-12 text-center">#</th>
                <th className="py-2.5 px-3">Delivery Interval (UTC)</th>
                <th className="py-2.5 px-3 text-right">Forecast (MW)</th>
                <th className="py-2.5 px-3 text-right">Actual Outturn (MW)</th>
                <th className="py-2.5 px-3 text-right">Forecast Error (Δ)</th>
                <th className="py-2.5 px-3 text-center">Direction</th>
                <th className="py-2.5 px-3">Selected Run Timestamp</th>
                <th className="py-2.5 px-3">Gate Cutoff</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle text-[12px] tabular-nums">
              {filteredRecords.length > 0 ? (
                filteredRecords.map((r, idx) => {
                  const isOver = r.forecast_error >= 0;
                  const isSelected = selectedPoint?.delivery_time === r.delivery_time;
                  return (
                    <tr
                      key={r.delivery_time}
                      onClick={() => setSelectedPoint(r)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-surface-canvas font-medium'
                          : 'hover:bg-surface-canvas/60'
                      }`}
                    >
                      <td className="py-2 px-3 text-center text-text-muted text-[11px]">
                        {idx + 1}
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
                        {isOver ? '+' : ''}
                        {r.forecast_error.toFixed(1)} MW
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
                      <td className="py-2 px-3 text-text-muted text-[11px]">
                        {new Date(r.forecast_publish_time).toLocaleDateString('en-GB', {
                          day: '2-digit',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}{' '}
                        UTC
                      </td>
                      <td className="py-2 px-3 text-text-faint text-[11px]">
                        {new Date(r.cutoff_time).toLocaleDateString('en-GB', {
                          day: '2-digit',
                          month: 'short',
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
                  <td colSpan={8} className="py-8 text-center text-text-muted text-[12px]">
                    No delivery observations matching filter criteria
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
