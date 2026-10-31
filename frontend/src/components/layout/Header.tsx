import React from 'react';
import { Icon } from '../common/Icon';

interface HeaderProps {
  onToggleSidebar?: () => void;
  startDate?: string;
  endDate?: string;
  cutoffHour?: number;
  onCutoffChange?: (hour: number) => void;
}

export const Header: React.FC<HeaderProps> = ({
  onToggleSidebar,
  startDate = '2026-01-01',
  endDate = '2026-01-31',
  cutoffHour = 15,
  onCutoffChange,
}) => {
  return (
    <header className="fixed top-0 left-0 lg:left-60 right-0 h-[60px] bg-surface-card border-b border-border-subtle z-40 px-4 sm:px-6 flex items-center justify-between">
      {/* Left: Mobile Toggle & Workspace Title */}
      <div className="flex items-center gap-3">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            className="lg:hidden text-text-muted hover:text-text-primary p-1 -ml-1"
            aria-label="Toggle menu"
          >
            <Icon name="menu" className="text-[22px]" />
          </button>
        )}
        <span className="text-[14px] font-semibold text-text-primary uppercase tracking-tight">
          Analytical Workspace
        </span>
      </div>

      {/* Right: Operational Controls & Status */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Date Range Pill */}
        <div className="hidden sm:flex h-8 px-2.5 bg-surface-canvas border border-border-strong rounded items-center gap-2">
          <Icon name="calendar_today" className="text-[15px] text-text-muted" />
          <span className="text-[12px] font-medium text-text-primary tabular-nums">
            {startDate} – {endDate}
          </span>
        </div>

        {/* Cutoff Gate Selector / Pill */}
        <div className="h-8 px-2.5 bg-surface-canvas border border-border-strong rounded flex items-center gap-1.5">
          <Icon name="timelapse" className="text-[15px] text-chart-primary" />
          <span className="text-[12px] text-text-primary font-medium">
            Cutoff: {String(cutoffHour).padStart(2, '0')}:00 UK
          </span>
          {onCutoffChange && (
            <select
              aria-label="Select Decision Cutoff Hour"
              value={cutoffHour}
              onChange={(e) => onCutoffChange(Number(e.target.value))}
              className="bg-transparent text-[11px] text-text-muted cursor-pointer focus:outline-none ml-0.5"
            >
              <option value={11}>11:00</option>
              <option value={12}>12:00</option>
              <option value={15}>15:00 (D-1)</option>
              <option value={17}>17:00</option>
            </select>
          )}
        </div>

        {/* Desk Live Status Indicator */}
        <div className="hidden md:flex items-center gap-2 pl-2 border-l border-border-subtle">
          <div className="flex flex-col text-right leading-none">
            <span className="text-[11px] font-medium text-text-primary">
              GB Power Trading
            </span>
            <span className="text-[10px] text-text-muted mt-0.5">
              Desk Live
            </span>
          </div>
          <div className="w-7 h-7 rounded-full bg-sidebar-surface flex items-center justify-center shrink-0">
            <Icon name="person" className="text-sidebar-text text-[16px]" />
          </div>
        </div>
      </div>
    </header>
  );
};

