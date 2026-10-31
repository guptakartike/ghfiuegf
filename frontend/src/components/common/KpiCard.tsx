import React from 'react';

export interface KpiCardProps {
  label: string;
  badge?: React.ReactNode;
  value: string | number;
  unit?: string;
  subtext?: string;
  footerDotColor?: string;
  footerText?: string;
  className?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  label,
  badge,
  value,
  unit,
  subtext,
  footerDotColor = 'bg-chart-primary',
  footerText,
  className = '',
}) => {
  return (
    <div
      className={`bg-surface-card border border-border-subtle rounded p-4 flex flex-col justify-between min-h-[132px] ${className}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wider text-text-muted font-medium">
          {label}
        </span>
        {badge && <div>{badge}</div>}
      </div>

      <div className="flex flex-col my-1">
        <span className="text-[24px] font-semibold text-text-primary tabular-nums tracking-tight">
          {value}{' '}
          {unit && (
            <span className="text-[14px] text-text-muted font-normal">
              {unit}
            </span>
          )}
        </span>
        {subtext && (
          <span className="text-[12px] text-text-muted mt-0.5">
            {subtext}
          </span>
        )}
      </div>

      {footerText && (
        <div className="flex items-center gap-1.5 pt-1.5 border-t border-border-subtle">
          <span
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${footerDotColor}`}
          />
          <span className="text-[11px] text-text-muted truncate">
            {footerText}
          </span>
        </div>
      )}
    </div>
  );
};

