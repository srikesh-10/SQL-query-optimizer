import React, { useState, useEffect } from 'react';
import type { BenchmarkResponse, BenchmarkSummary } from '../../types/benchmark';
import * as api from '../../services/api';
import {
  Timer, Play, RotateCcw, AlertTriangle, CheckCircle2, XCircle,
  Clock, History, GitCompare, TrendingDown, TrendingUp, Minus,
} from 'lucide-react';

interface BenchmarkSectionProps {
  currentSql: string;
  onBenchmark?: (sql: string, repetitions: number) => Promise<BenchmarkResponse>;
}

export const BenchmarkSection: React.FC<BenchmarkSectionProps> = ({ currentSql, onBenchmark }) => {
  const [repetitions, setRepetitions] = useState<number>(3);
  const [confirmed, setConfirmed] = useState<boolean>(false);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [latestBenchmark, setLatestBenchmark] = useState<BenchmarkResponse | null>(null);
  const [history, setHistory] = useState<BenchmarkSummary[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [comparisonTarget, setComparisonTarget] = useState<BenchmarkResponse | null>(null);
  const [loadingTarget, setLoadingTarget] = useState<boolean>(false);

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try { const data = await api.getBenchmarkHistory(10, 0); setHistory(data.items); } catch {} finally { setLoadingHistory(false); }
  };

  useEffect(() => { fetchHistory(); }, []);

  const handleRunBenchmark = async () => {
    if (!currentSql.trim() || running) return;
    setRunning(true); setError(null);
    try {
      const execute = onBenchmark || api.createBenchmark;
      const result = await execute(currentSql, repetitions);
      setLatestBenchmark(result); fetchHistory();
    } catch (err) {
      if (err instanceof api.ApiError) setError(err.detail);
      else if (err instanceof Error) setError(err.message);
      else setError('Benchmarking failed.');
    } finally { setRunning(false); }
  };

  const handleSelectCompare = async (targetId: string) => {
    if (latestBenchmark && latestBenchmark.id === targetId) { setComparisonTarget(null); return; }
    setLoadingTarget(true);
    try { const target = await api.getBenchmarkById(targetId); setComparisonTarget(target); } catch { setComparisonTarget(null); } finally { setLoadingTarget(false); }
  };

  const computeTimeDelta = () => {
    if (!latestBenchmark?.median_execution_time_ms || !comparisonTarget?.median_execution_time_ms) return null;
    const current = latestBenchmark.median_execution_time_ms;
    const base = comparisonTarget.median_execution_time_ms;
    const diff = current - base;
    const pct = base > 0 ? (diff / base) * 100 : 0;
    return { diff, pct };
  };

  const delta = computeTimeDelta();

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="rounded-lg border border-border-primary bg-surface-800 p-5 space-y-4">
        <div className="flex items-center gap-3 pb-3 border-b border-border-primary">
          <div className="w-7 h-7 rounded-md bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20">
            <Timer className="w-3.5 h-3.5" />
          </div>
          <div>
            <h2 className="text-[12px] font-semibold text-text-primary">Safe Execution Benchmark</h2>
            <p className="text-[11px] text-text-tertiary">
              Measure actual execution using <code className="text-text-secondary bg-surface-600 px-1 py-0.5 rounded font-mono text-[10px]">EXPLAIN ANALYZE</code> in a read-only transaction.
            </p>
          </div>
        </div>

        <div className="bg-amber-500/5 border border-amber-500/15 rounded p-3 flex items-start gap-2.5 text-[11px] text-amber-400">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <strong className="font-semibold text-amber-300 block">Execution Safety Notice:</strong>
            <p className="text-amber-400/80 leading-relaxed">
              This <strong className="text-amber-300">executes the query</strong> inside a <code className="bg-amber-500/10 px-1 rounded font-mono text-[10px]">READ ONLY</code> transaction with a 3,000ms timeout.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <label htmlFor="repetitions-select" className="text-[11px] font-semibold text-text-secondary">Reps:</label>
              <select
                id="repetitions-select"
                value={repetitions}
                onChange={(e) => setRepetitions(Number(e.target.value))}
                disabled={running}
                className="bg-surface-700 border border-border-secondary text-text-primary text-[11px] rounded px-2 py-1 focus:ring-1 focus:ring-accent-300 focus:outline-hidden disabled:opacity-50 cursor-pointer"
              >
                <option value={1}>1x</option><option value={2}>2x</option><option value={3}>3x (recommended)</option><option value={4}>4x</option><option value={5}>5x</option>
              </select>
            </div>
            <label className="flex items-center gap-2 select-none cursor-pointer">
              <input id="confirm-benchmark-check" type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} disabled={running} className="rounded border-border-hover text-accent-300 focus:ring-accent-300 w-3.5 h-3.5 cursor-pointer bg-surface-600" />
              <span className="text-[11px] text-text-tertiary">I understand this executes the query</span>
            </label>
          </div>
          <button
            onClick={handleRunBenchmark}
            disabled={!confirmed || !currentSql.trim() || running}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-accent-200 hover:bg-accent-300 text-white text-[11px] font-semibold rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            {running ? (<><RotateCcw className="w-3 h-3 animate-spin" /><span>Benchmarking...</span></>) : (<><Play className="w-3 h-3" /><span>Run Benchmark</span></>)}
          </button>
        </div>

        {error && (
          <div className="bg-red-500/5 border border-red-500/15 rounded p-3 text-[11px] text-red-400 flex items-start gap-2 animate-fade-up">
            <XCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <div><p className="font-semibold">Failed</p><p className="font-mono text-[10px] mt-0.5">{error}</p></div>
          </div>
        )}
      </div>

      {/* Results */}
      {latestBenchmark && (
        <div className="space-y-4 animate-fade-up">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border-primary rounded-lg overflow-hidden border border-border-primary">
            <div className="bg-surface-800 p-4">
              <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">Execution Time</span>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="text-lg font-bold font-mono text-accent-400">
                  {latestBenchmark.median_execution_time_ms != null ? latestBenchmark.median_execution_time_ms.toFixed(3) : 'N/A'}
                </span>
                <span className="text-[10px] text-text-muted">ms</span>
              </div>
              <span className="text-[10px] text-text-muted block mt-0.5">median</span>
            </div>
            <div className="bg-surface-800 p-4">
              <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">Planning Time</span>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="text-lg font-bold font-mono text-text-primary">
                  {latestBenchmark.median_planning_time_ms != null ? latestBenchmark.median_planning_time_ms.toFixed(3) : 'N/A'}
                </span>
                <span className="text-[10px] text-text-muted">ms</span>
              </div>
              <span className="text-[10px] text-text-muted block mt-0.5">median</span>
            </div>
            <div className="bg-surface-800 p-4">
              <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">Planner Cost</span>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="text-lg font-bold font-mono text-text-primary">
                  {latestBenchmark.estimated_total_cost != null ? latestBenchmark.estimated_total_cost.toFixed(2) : 'N/A'}
                </span>
                <span className="text-[10px] text-text-muted">units</span>
              </div>
              <span className="text-[10px] text-amber-400 block mt-0.5">estimate</span>
            </div>
            <div className="bg-surface-800 p-4">
              <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">Status</span>
              <div className="mt-1.5">
                {latestBenchmark.status === 'completed' && <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><CheckCircle2 className="w-3 h-3 mr-1" />Done</span>}
                {latestBenchmark.status === 'partial_failure' && <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20"><AlertTriangle className="w-3 h-3 mr-1" />Partial</span>}
                {latestBenchmark.status === 'failed' && <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-red-500/10 text-red-400 border border-red-500/20"><XCircle className="w-3 h-3 mr-1" />Failed</span>}
              </div>
              <span className="text-[10px] text-text-muted mt-1 block">{latestBenchmark.successful_runs} / {latestBenchmark.requested_repetitions} succeeded</span>
            </div>
          </div>

          {/* Runs Table */}
          <div className="rounded-lg border border-border-primary bg-surface-800 overflow-hidden">
            <div className="border-b border-border-primary px-4 py-2.5 flex items-center justify-between">
              <h3 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-3 h-3 text-text-muted" /><span>Repetitions</span>
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[11px]">
                <thead>
                  <tr className="border-b border-border-primary text-text-muted font-medium">
                    <th className="py-2 px-4 text-[10px] uppercase tracking-wider">Run</th>
                    <th className="py-2 px-4 text-[10px] uppercase tracking-wider">Status</th>
                    <th className="py-2 px-4 text-[10px] uppercase tracking-wider">Exec Time</th>
                    <th className="py-2 px-4 text-[10px] uppercase tracking-wider">Plan Time</th>
                    <th className="py-2 px-4 text-[10px] uppercase tracking-wider">Cost</th>
                    <th className="py-2 px-4 text-[10px] uppercase tracking-wider">Rows</th>
                    <th className="py-2 px-4 text-[10px] uppercase tracking-wider">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-primary font-mono">
                  {latestBenchmark.runs.map((r) => (
                    <tr key={r.run_order} className="hover:bg-surface-700/30 transition-colors">
                      <td className="py-2 px-4 font-bold text-text-secondary">#{r.run_order}</td>
                      <td className="py-2 px-4">
                        {r.status === 'success' && <span className="text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded text-[10px] font-sans font-semibold">OK</span>}
                        {r.status === 'timeout' && <span className="text-amber-400 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded text-[10px] font-sans font-semibold">Timeout</span>}
                        {r.status === 'failed' && <span className="text-red-400 bg-red-500/10 border border-red-500/20 px-1.5 py-0.5 rounded text-[10px] font-sans font-semibold">Fail</span>}
                      </td>
                      <td className="py-2 px-4 font-bold text-accent-400">{r.execution_time_ms != null ? `${r.execution_time_ms.toFixed(3)} ms` : '—'}</td>
                      <td className="py-2 px-4 text-text-tertiary">{r.planning_time_ms != null ? `${r.planning_time_ms.toFixed(3)} ms` : '—'}</td>
                      <td className="py-2 px-4 text-text-tertiary">{r.total_cost != null ? r.total_cost.toFixed(2) : '—'}</td>
                      <td className="py-2 px-4 text-text-tertiary">{r.actual_rows ?? '—'}</td>
                      <td className="py-2 px-4 font-sans text-text-muted text-[10px]">{r.error_message || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Comparison */}
      {comparisonTarget && latestBenchmark && (
        <div className="rounded-lg border border-accent-200/20 bg-surface-800 p-5 space-y-3 animate-fade-up">
          <div className="flex items-center justify-between border-b border-border-primary pb-2.5">
            <h3 className="text-[11px] font-semibold text-text-primary uppercase tracking-wider flex items-center gap-1.5">
              <GitCompare className="w-3.5 h-3.5 text-accent-400" /><span>Comparison</span>
            </h3>
            <button onClick={() => setComparisonTarget(null)} className="text-[10px] text-text-muted hover:text-text-secondary cursor-pointer">Close</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
            <div className="p-3 bg-surface-700 rounded border border-border-secondary">
              <span className="font-medium text-text-muted block mb-1">Current</span>
              <p className="font-mono text-sm font-bold text-text-primary">{latestBenchmark.median_execution_time_ms != null ? `${latestBenchmark.median_execution_time_ms.toFixed(3)} ms` : 'N/A'}</p>
            </div>
            <div className="p-3 bg-surface-700 rounded border border-border-secondary">
              <span className="font-medium text-text-muted block mb-1">Target</span>
              <p className="font-mono text-sm font-bold text-text-primary">{comparisonTarget.median_execution_time_ms != null ? `${comparisonTarget.median_execution_time_ms.toFixed(3)} ms` : 'N/A'}</p>
            </div>
            <div className="p-3 bg-surface-700 rounded border border-border-secondary flex flex-col justify-center">
              <span className="font-medium text-text-muted block mb-1">Delta</span>
              {delta ? (
                <div className="flex items-center gap-1.5">
                  {delta.diff < 0 ? (<><TrendingDown className="w-3.5 h-3.5 text-emerald-400" /><span className="text-sm font-bold text-emerald-400 font-mono">{delta.diff.toFixed(3)} ms ({Math.abs(delta.pct).toFixed(1)}% faster)</span></>) :
                   delta.diff > 0 ? (<><TrendingUp className="w-3.5 h-3.5 text-red-400" /><span className="text-sm font-bold text-red-400 font-mono">+{delta.diff.toFixed(3)} ms ({delta.pct.toFixed(1)}% slower)</span></>) :
                   (<><Minus className="w-3.5 h-3.5 text-text-muted" /><span className="text-sm font-bold text-text-primary font-mono">Same</span></>)}
                </div>
              ) : <span className="text-text-muted">N/A</span>}
            </div>
          </div>
        </div>
      )}

      {/* History */}
      <div className="rounded-lg border border-border-primary bg-surface-800 overflow-hidden">
        <div className="border-b border-border-primary px-4 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-3.5 h-3.5 text-text-muted" />
            <h3 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">History</h3>
          </div>
          <button onClick={fetchHistory} disabled={loadingHistory} className="text-[10px] text-accent-400 hover:text-accent-500 font-medium inline-flex items-center gap-1 cursor-pointer">
            <RotateCcw className={`w-3 h-3 ${loadingHistory ? 'animate-spin' : ''}`} /><span>Refresh</span>
          </button>
        </div>
        {history.length === 0 ? (
          <div className="p-6 text-center text-[11px] text-text-muted italic">No runs yet.</div>
        ) : (
          <div className="divide-y divide-border-primary">
            {history.map((item) => (
              <div key={item.id} className="p-3 hover:bg-surface-700/30 transition-colors flex items-center justify-between gap-4">
                <div className="min-w-0 flex-1 space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-text-secondary truncate max-w-md block">{item.sql}</span>
                    <span className="text-[10px] text-text-muted shrink-0">
                      {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-text-muted">
                    <span>{item.requested_repetitions} reps</span>
                    <span>·</span>
                    <span className="text-text-tertiary font-medium">{item.status}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <div className="text-right">
                    <span className="text-[11px] font-bold font-mono text-accent-400 block">
                      {item.median_execution_time_ms != null ? `${item.median_execution_time_ms.toFixed(3)} ms` : '—'}
                    </span>
                  </div>
                  {latestBenchmark && latestBenchmark.id !== item.id && (
                    <button
                      onClick={() => handleSelectCompare(item.id)}
                      disabled={loadingTarget}
                      className="px-2 py-1 text-[10px] border border-border-secondary hover:border-accent-200/30 hover:text-accent-400 rounded font-medium text-text-tertiary transition-colors cursor-pointer"
                    >
                      Compare
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
