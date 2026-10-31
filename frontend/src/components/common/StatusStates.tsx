import React from 'react';
import { Icon } from './Icon';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading analytical dataset...',
}) => {
  return (
    <div className="bg-surface-card border border-border-subtle rounded p-12 flex flex-col items-center justify-center text-center gap-3 min-h-[240px]">
      <div className="w-5 h-5 border-2 border-border-strong border-t-chart-primary rounded-full animate-spin" />
      <span className="text-[13px] text-text-muted font-medium">
        {message}
      </span>
    </div>
  );
};

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'API Connection Error',
  message,
  onRetry,
}) => {
  return (
    <div className="bg-surface-card border border-border-subtle border-l-2 border-l-text-primary rounded p-6 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Icon name="error_outline" className="text-text-primary text-[20px]" />
        <span className="text-[14px] font-semibold text-text-primary">
          {title}
        </span>
      </div>
      <p className="text-[13px] text-text-muted font-mono bg-surface-canvas p-3 rounded border border-border-subtle">
        {message}
      </p>
      {onRetry && (
        <div className="pt-2">
          <button
            type="button"
            onClick={onRetry}
            className="h-8 px-3 bg-sidebar-surface text-sidebar-text rounded text-[13px] font-medium hover:bg-sidebar-surface-hover transition-colors inline-flex items-center gap-1.5"
          >
            <Icon name="refresh" className="text-[16px]" />
            <span>Retry Query</span>
          </button>
        </div>
      )}
    </div>
  );
};

interface EmptyStateProps {
  title?: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Observations Available',
  description,
  actionText,
  onAction,
}) => {
  return (
    <div className="bg-surface-card border border-border-subtle rounded p-12 flex flex-col items-center justify-center text-center gap-2 min-h-[220px]">
      <Icon name="dataset" className="text-[28px] text-text-muted mb-1" />
      <span className="text-[14px] font-semibold text-text-primary">
        {title}
      </span>
      <p className="text-[13px] text-text-muted max-w-md">
        {description}
      </p>
      {actionText && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-2 h-8 px-3 bg-surface-card border border-border-strong text-text-primary rounded text-[13px] font-medium hover:bg-surface-canvas transition-colors"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};

