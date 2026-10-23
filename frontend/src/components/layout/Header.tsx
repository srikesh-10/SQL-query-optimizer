import React, { useState } from 'react';
import { ExternalLink, RefreshCw, Sun, Moon } from 'lucide-react';
import type { ReadinessResponse } from '../../types/analysis';

interface HeaderProps {
  backendStatus: ReadinessResponse | null;
  checkingStatus: boolean;
  onRefreshStatus: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  backendStatus,
  checkingStatus,
  onRefreshStatus,
}) => {
  const isHealthy = backendStatus?.status === 'healthy' && backendStatus?.database === 'connected';
  const isOffline = !backendStatus || backendStatus.status === 'offline';

  const [isDark, setIsDark] = useState<boolean>(() => {
    if (typeof document !== 'undefined') {
      return document.documentElement.classList.contains('dark');
    }
    return false;
  });

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    if (next) {
      document.documentElement.classList.add('dark');
      try { localStorage.setItem('sql-theme', 'dark'); } catch (_) {}
    } else {
      document.documentElement.classList.remove('dark');
      try { localStorage.setItem('sql-theme', 'sandal'); } catch (_) {}
    }
  };

  return (
    <header className="sticky top-0 z-30 border-b border-border-primary bg-surface-800/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-md bg-accent-50 flex items-center justify-center ring-1 ring-accent-200/20">
            <svg className="w-4 h-4 text-accent-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M3 5V12C3 13.66 7.03 15 12 15C16.97 15 21 13.66 21 12V5" />
              <path d="M3 12V19C3 20.66 7.03 22 12 22C16.97 22 21 20.66 21 19V12" />
            </svg>
          </div>
          <div>
            <h1 className="text-[13px] font-semibold text-text-primary tracking-tight leading-none">
              SQL Query Optimizer
            </h1>
            <p className="text-[11px] text-text-tertiary mt-0.5 hidden sm:block">
              PostgreSQL performance intelligence
            </p>
          </div>
        </div>

        {/* Status & Controls */}
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-2 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${
              isHealthy
                ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-400'
                : isOffline
                ? 'border-red-500/20 bg-red-500/5 text-red-400'
                : 'border-amber-500/20 bg-amber-500/5 text-amber-400'
            }`}
          >
            <span className="relative flex h-1.5 w-1.5">
              {isHealthy && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
              )}
              <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${
                isHealthy ? 'bg-emerald-400' : isOffline ? 'bg-red-400' : 'bg-amber-400'
              }`} />
            </span>
            <span>
              {checkingStatus
                ? 'Checking...'
                : isHealthy
                ? 'Connected'
                : isOffline
                ? 'Offline'
                : 'DB Disconnected'}
            </span>
            <button
              onClick={onRefreshStatus}
              title="Refresh Status"
              aria-label="Refresh Health Status"
              className="text-text-muted hover:text-text-secondary p-0.5 rounded transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3 h-3 ${checkingStatus ? 'animate-spin' : ''}`} />
            </button>
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            aria-label="Toggle Sandal Theme Mode"
            title={isDark ? "Switch to Sandal Cream" : "Switch to Dark Sandalwood"}
            className="inline-flex items-center gap-1.5 text-text-tertiary hover:text-text-secondary border border-border-secondary hover:border-border-hover px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors cursor-pointer bg-surface-700/50"
          >
            {isDark ? (
              <>
                <Sun className="w-3 h-3 text-accent-400" />
                <span className="hidden sm:inline">Sandal Cream</span>
              </>
            ) : (
              <>
                <Moon className="w-3 h-3 text-accent-400" />
                <span className="hidden sm:inline">Dark Sandal</span>
              </>
            )}
          </button>

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-text-tertiary hover:text-text-secondary border border-border-secondary hover:border-border-hover px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors"
          >
            <span>API Docs</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </header>
  );
};
