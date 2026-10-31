import React from 'react';
import type { NavigationPath } from '../../lib/types';
import { Icon } from '../common/Icon';

interface SidebarProps {
  currentPath: NavigationPath;
  onNavigate: (path: NavigationPath) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

interface NavItem {
  path: NavigationPath;
  label: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { path: 'overview', label: 'Overview', icon: 'grid_view' },
  { path: 'forecast-explorer', label: 'Forecast Explorer', icon: 'query_stats' },
  { path: 'accuracy-analysis', label: 'Accuracy Analysis', icon: 'ssid_chart' },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentPath,
  onNavigate,
  isOpen = false,
  onClose,
}) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-[#000000]/50 z-40 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* 240px Fixed Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-screen w-60 bg-sidebar-surface border-r border-sidebar-border z-50 flex flex-col justify-between transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col">
          {/* Header / Brand */}
          <div className="h-[60px] flex items-center justify-between px-4 border-b border-sidebar-border">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded bg-sidebar-surface-active border border-sidebar-border flex items-center justify-center shrink-0">
                <Icon name="air" className="text-chart-primary text-[20px]" />
              </div>
              <div className="flex flex-col">
                <span className="text-[14px] font-semibold text-sidebar-text tracking-tight leading-none">
                  Wind Analytics
                </span>
                <span className="text-[10px] text-sidebar-text-muted uppercase tracking-wider mt-1 leading-none">
                  UK Grid / BMRS
                </span>
              </div>
            </div>

            {/* Mobile close button */}
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                className="lg:hidden text-sidebar-text-muted hover:text-sidebar-text p-1"
                aria-label="Close sidebar"
              >
                <Icon name="close" className="text-[20px]" />
              </button>
            )}
          </div>

          {/* Navigation Links */}
          <div className="px-2 py-4">
            <div className="px-2.5 pb-2 text-[10px] uppercase tracking-wider text-sidebar-text-muted font-medium">
              Analytical Suite
            </div>
            <nav className="flex flex-col gap-0.5" aria-label="Main Navigation">
              {NAV_ITEMS.map((item) => {
                const isActive = currentPath === item.path;
                return (
                  <button
                    key={item.path}
                    type="button"
                    onClick={() => {
                      onNavigate(item.path);
                      if (onClose) onClose();
                    }}
                    className={`flex items-center gap-3 px-2.5 py-2 rounded transition-colors text-[13px] text-left w-full ${
                      isActive
                        ? 'bg-sidebar-surface-active text-sidebar-text border-l-2 border-chart-primary font-medium'
                        : 'text-sidebar-text-muted hover:bg-sidebar-surface-hover hover:text-sidebar-text border-l-2 border-transparent font-normal'
                    }`}
                  >
                    <Icon name={item.icon} className={isActive ? 'text-chart-primary' : ''} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Footer / Telemetry status */}
        <div className="p-3 border-t border-sidebar-border bg-sidebar-surface">
          <div className="flex items-center justify-between px-2.5 py-2 rounded bg-sidebar-surface-hover border border-sidebar-border/50">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-chart-primary shrink-0" />
              <span className="text-[11px] text-sidebar-text font-medium leading-none">
                Elexon BMRS Verified
              </span>
            </div>
            <span className="text-[10px] text-sidebar-text-muted font-mono leading-none">
              15:00 UK
            </span>
          </div>
        </div>
      </aside>
    </>
  );
};

