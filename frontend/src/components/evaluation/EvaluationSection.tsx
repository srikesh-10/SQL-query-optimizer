import React, { useState, useEffect } from 'react';
import {
  CheckCircle2, XCircle, AlertTriangle, ShieldAlert, Play, RotateCcw,
  History, ChevronRight, Zap, Scale,
} from 'lucide-react';
import type { RewriteCandidate } from '../../types/analysis';
import type {
  EvaluationResponse, EvaluationSummary, CorrectnessStatus,
  PerformanceAssessment, EvaluationRecommendation,
} from '../../types/evaluation';
import * as api from '../../services/api';

interface EvaluationSectionProps {
  currentOriginalSql: string;
  rewriteCandidates?: RewriteCandidate[];
  onEvaluate?: (origSql: string, candSql: string, confirmed: boolean, repetitions: number) => Promise<EvaluationResponse>;
}

export const EvaluationSection: React.FC<EvaluationSectionProps> = ({
  currentOriginalSql, rewriteCandidates = [], onEvaluate,
}) => {
  const [originalSql, setOriginalSql] = useState<string>(currentOriginalSql || '');
  const [candidateSql, setCandidateSql] = useState<string>('');
  const [confirmed, setConfirmed] = useState<boolean>(false);
  const [repetitions, setRepetitions] = useState<number>(3);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [evaluationResult, setEvaluationResult] = useState<EvaluationResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [historyItems, setHistoryItems] = useState<EvaluationSummary[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  useEffect(() => { if (currentOriginalSql && !originalSql) setOriginalSql(currentOriginalSql); }, [currentOriginalSql, originalSql]);
  useEffect(() => { if (rewriteCandidates.length > 0 && !candidateSql) setCandidateSql(rewriteCandidates[0]?.rewritten_sql || ''); }, [rewriteCandidates, candidateSql]);

  const loadHistory = async () => {
    setLoadingHistory(true); setHistoryError(null);
    try { const res = await api.getEvaluationHistory(10, 0); setHistoryItems(res.items || []); }
    catch (err) { setHistoryError(err instanceof Error ? err.message : 'Failed'); }
    finally { setLoadingHistory(false); }
  };

  useEffect(() => { loadHistory(); }, []);

  const handleStartEvaluation = async () => {
    if (!originalSql.trim() || !candidateSql.trim() || !confirmed || evaluating) return;
    setEvaluating(true); setErrorMessage(null);
    try {
      const result = onEvaluate
        ? await onEvaluate(originalSql, candidateSql, confirmed, repetitions)
        : await api.createEvaluation(originalSql, candidateSql, confirmed, repetitions);
      setEvaluationResult(result); loadHistory();
    } catch (err) {
      if (err instanceof api.ApiError) setErrorMessage(err.detail);
      else if (err instanceof Error) setErrorMessage(err.message);
      else setErrorMessage('Evaluation failed.');
    } finally { setEvaluating(false); }
  };

  const handleSelectHistoryItem = async (id: string) => {
    try {
      const detail = await api.getEvaluationById(id);
      setEvaluationResult(detail); setOriginalSql(detail.original_sql); setCandidateSql(detail.candidate_sql);
      window.scrollTo({ top: 300, behavior: 'smooth' });
    } catch {}
  };

  const renderCorrectnessBadge = (status: CorrectnessStatus) => {
    const map: Record<string, { cls: string; icon: React.ReactNode; label: string }> = {
      validated: { cls: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', icon: <CheckCircle2 className="w-3 h-3" />, label: 'Validated Equivalent' },
      different: { cls: 'bg-red-500/10 text-red-400 border-red-500/20', icon: <XCircle className="w-3 h-3" />, label: 'Different Results' },
      inconclusive: { cls: 'bg-amber-500/10 text-amber-400 border-amber-500/20', icon: <AlertTriangle className="w-3 h-3" />, label: 'Inconclusive' },
    };
    const s = map[status] || { cls: 'bg-red-500/10 text-red-400 border-red-500/20', icon: <ShieldAlert className="w-3 h-3" />, label: 'Rejected' };
    return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${s.cls}`}>{s.icon}{s.label}</span>;
  };

  const renderPerformanceBadge = (perf: PerformanceAssessment) => {
    const map: Record<string, { cls: string; icon?: React.ReactNode; label: string }> = {
      faster: { cls: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', icon: <Zap className="w-3 h-3" />, label: 'Faster' },
      similar: { cls: 'bg-blue-500/10 text-blue-400 border-blue-500/20', label: 'Similar' },
      slower: { cls: 'bg-red-500/10 text-red-400 border-red-500/20', label: 'Slower' },
    };
    const s = map[perf] || { cls: 'bg-surface-400 text-text-tertiary border-border-secondary', label: 'Inconclusive' };
    return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border ${s.cls}`}>{s.icon}{s.label}</span>;
  };

  const renderRecommendationBanner = (rec: EvaluationRecommendation, rationale: string, correctness?: CorrectnessStatus) => {
    if (correctness && correctness !== 'validated' && rec === 'recommend_candidate') {
      rec = 'insufficient_evidence';
      rationale = 'Correctness could not be verified. Cannot recommend without validated equivalence.';
    }
    const styles: Record<string, { bg: string; icon: React.ReactNode; title: string }> = {
      recommend_candidate: { bg: 'bg-emerald-500/5 border-emerald-500/20', icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />, title: 'Recommendation: Adopt Candidate Rewrite' },
      keep_original: { bg: 'bg-amber-500/5 border-amber-500/20', icon: <AlertTriangle className="w-4 h-4 text-amber-400" />, title: 'Recommendation: Keep Original Query' },
      do_not_recommend: { bg: 'bg-red-500/5 border-red-500/20', icon: <XCircle className="w-4 h-4 text-red-400" />, title: 'Recommendation: Do Not Recommend Rewrite' },
      insufficient_evidence: { bg: 'bg-surface-700 border-border-secondary', icon: <ShieldAlert className="w-4 h-4 text-text-muted" />, title: 'Insufficient Evidence' },
    };
    const s = styles[rec] || styles.insufficient_evidence;
    return (
      <div className={`rounded-lg border p-4 ${s.bg}`}>
        <div className="flex items-center gap-2 mb-1.5">{s.icon}<h3 className="text-[12px] font-bold text-text-primary uppercase tracking-wider">{s.title}</h3></div>
        <p className="text-[11px] text-text-secondary leading-relaxed">{rationale}</p>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="rounded-lg border border-border-primary bg-surface-800 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-md bg-accent-50 text-accent-400 flex items-center justify-center border border-accent-200/20">
              <Scale className="w-3.5 h-3.5" />
            </div>
            <div>
              <h2 className="text-[12px] font-semibold text-text-primary">Optimizer Evaluation & Performance Scoring</h2>
              <p className="text-[11px] text-text-tertiary">Correctness → Performance → Recommendation</p>
            </div>
          </div>
          <button onClick={loadHistory} disabled={loadingHistory} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-text-tertiary hover:text-text-secondary bg-surface-700 hover:bg-surface-600 rounded transition-colors cursor-pointer">
            <RotateCcw className={`w-3 h-3 ${loadingHistory ? 'animate-spin' : ''}`} /><span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Setup */}
      <div className="rounded-lg border border-border-primary bg-surface-800 p-5 space-y-5">
        {rewriteCandidates.length > 0 && (
          <div className="p-3 bg-accent-50/30 border border-accent-200/15 rounded space-y-2">
            <span className="text-[10px] font-semibold text-accent-400 uppercase tracking-wider block">Load from analysis:</span>
            <div className="flex flex-wrap gap-1.5">
              {rewriteCandidates.map((c) => (
                <button key={c.rule_id} onClick={() => setCandidateSql(c.rewritten_sql || '')}
                  className={`text-[10px] px-2 py-1 rounded border font-medium transition-colors cursor-pointer ${
                    candidateSql === c.rewritten_sql
                      ? 'bg-accent-200 text-surface-900 border-accent-200'
                      : 'bg-surface-700 text-text-tertiary border-border-secondary hover:border-accent-200/30'
                  }`}>
                  {c.title}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Original</label>
              <span className="text-[10px] text-text-muted font-mono">SELECT only</span>
            </div>
            <textarea aria-label="Evaluation Original Query" value={originalSql} onChange={(e) => setOriginalSql(e.target.value)} placeholder="SELECT * FROM users WHERE ..." rows={5}
              className="w-full font-mono text-[11px] bg-surface-900 text-text-primary p-3 rounded border border-border-primary focus:outline-hidden focus:ring-1 focus:ring-accent-200/30 leading-relaxed" />
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Candidate</label>
              <span className="text-[10px] text-text-muted font-mono">Proposed rewrite</span>
            </div>
            <textarea aria-label="Evaluation Candidate Query" value={candidateSql} onChange={(e) => setCandidateSql(e.target.value)} placeholder="SELECT id, email FROM users WHERE ..." rows={5}
              className="w-full font-mono text-[11px] bg-surface-900 text-text-primary p-3 rounded border border-border-primary focus:outline-hidden focus:ring-1 focus:ring-accent-200/30 leading-relaxed" />
          </div>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-4 border-t border-border-primary">
          <div className="flex items-center gap-3">
            <label className="text-[11px] font-semibold text-text-secondary">Reps:</label>
            <div className="flex items-center gap-0.5">
              {[1,2,3,4,5].map((count) => (
                <button key={count} type="button" onClick={() => setRepetitions(count)}
                  className={`px-2 py-1 text-[10px] font-semibold rounded transition-colors cursor-pointer ${
                    repetitions === count ? 'bg-accent-200 text-surface-900' : 'bg-surface-600 text-text-tertiary hover:bg-surface-500'
                  }`}>
                  {count}x
                </button>
              ))}
            </div>
          </div>
          <div className="text-[10px] text-text-muted">Timeout: <span className="text-text-tertiary font-medium">3,000ms</span> · Rows: <span className="text-text-tertiary font-medium">1,000</span></div>
        </div>

        <div className="bg-amber-500/5 border border-amber-500/15 rounded-lg p-4 space-y-3">
          <div className="flex items-start gap-2.5">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-[11px] font-semibold text-amber-300 uppercase tracking-wider">Safety Notice</h4>
              <p className="text-[10px] text-amber-400/80 leading-relaxed">
                Both queries execute against PostgreSQL in read-only transactions. Correctness checked first; benchmarking only runs on matching results.
              </p>
            </div>
          </div>
          <div className="pt-2 border-t border-amber-500/10">
            <label className="flex items-center gap-2 text-[11px] font-medium text-text-secondary hover:text-text-primary select-none cursor-pointer">
              <input
                type="checkbox"
                checked={confirmed}
                aria-label="Authorize evaluation query execution"
                onChange={(e) => setConfirmed(e.target.checked)}
                className="rounded border-border-hover text-accent-300 focus:ring-accent-300 w-3.5 h-3.5 cursor-pointer bg-surface-600"
              />
              <span>I authorize executing both queries against PostgreSQL for unified evaluation.</span>
            </label>
          </div>
        </div>

        {errorMessage && (
          <div className="bg-red-500/5 border border-red-500/15 rounded p-3 flex items-start gap-2.5 text-red-400">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div><h4 className="text-[11px] font-semibold">Error</h4><p className="text-[10px] font-mono mt-1">{errorMessage}</p></div>
          </div>
        )}

        <div className="flex items-center justify-end">
          <button onClick={handleStartEvaluation}
            disabled={!confirmed || !originalSql.trim() || !candidateSql.trim() || evaluating}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded text-[11px] font-bold transition-all ${
              !confirmed || !originalSql.trim() || !candidateSql.trim() || evaluating
                ? 'bg-surface-500 text-text-muted cursor-not-allowed'
                : 'bg-accent-200 hover:bg-accent-300 text-white cursor-pointer'
            }`}>
            {evaluating ? (<><RotateCcw className="w-3.5 h-3.5 animate-spin" /><span>Evaluating...</span></>) : (<><Play className="w-3.5 h-3.5" /><span>Start Unified Evaluation</span></>)}
          </button>
        </div>
      </div>

      {/* Results */}
      {evaluationResult && (
        <div className="space-y-4 animate-fade-up">
          <section>{renderRecommendationBanner(evaluationResult.recommendation, evaluationResult.recommendation_rationale, evaluationResult.correctness_status)}</section>

          {/* Gate 1: Correctness */}
          <section className="rounded-lg border border-border-primary bg-surface-800 p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-border-primary">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-accent-50 text-accent-400 flex items-center justify-center text-[10px] font-bold">1</span>
                <h3 className="text-[11px] font-semibold text-text-primary uppercase tracking-wider">Correctness Gate</h3>
              </div>
              <div>{renderCorrectnessBadge(evaluationResult.correctness_status)}</div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {[
                { label: 'Original Rows', val: evaluationResult.original_row_count ?? 'N/A' },
                { label: 'Candidate Rows', val: evaluationResult.candidate_row_count ?? 'N/A' },
                { label: 'Completeness', val: evaluationResult.is_complete_comparison ? 'Complete' : 'Incomplete', cls: evaluationResult.is_complete_comparison ? 'text-emerald-400' : 'text-amber-400' },
              ].map(({ label, val, cls }) => (
                <div key={label} className="bg-surface-700 border border-border-secondary rounded p-3">
                  <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">{label}</span>
                  <span className={`text-sm font-bold font-mono ${cls || 'text-text-primary'}`}>{val?.toLocaleString?.() ?? val}</span>
                </div>
              ))}
            </div>
            {evaluationResult.mismatch_reason && (
              <div className="p-2.5 bg-red-500/5 border border-red-500/15 rounded text-[10px] font-mono text-red-400">
                <strong>Detail:</strong> {evaluationResult.mismatch_reason}
              </div>
            )}
          </section>

          {/* Gate 2: Performance */}
          <section className="rounded-lg border border-border-primary bg-surface-800 p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-border-primary">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-accent-50 text-accent-400 flex items-center justify-center text-[10px] font-bold">2</span>
                <h3 className="text-[11px] font-semibold text-text-primary uppercase tracking-wider">Performance</h3>
              </div>
              <div>{renderPerformanceBadge(evaluationResult.performance_assessment)}</div>
            </div>
            {evaluationResult.correctness_status !== 'validated' ? (
              <div className="p-4 bg-surface-700 border border-border-secondary rounded text-center text-[11px] text-text-muted">Performance benchmarking was skipped because query correctness was not validated.</div>
            ) : (
              <>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                  {[
                    { label: 'Original Median', val: evaluationResult.original_median_execution_time_ms, fmt: (v: number) => `${v.toFixed(2)} ms` },
                    { label: 'Candidate Median', val: evaluationResult.candidate_median_execution_time_ms, fmt: (v: number) => `${v.toFixed(2)} ms` },
                    { label: 'Difference', val: evaluationResult.runtime_difference_ms, fmt: (v: number) => `${v > 0 ? '-' : '+'}${Math.abs(v).toFixed(2)} ms`, cls: (v: number) => v > 0 ? 'text-emerald-400' : 'text-text-primary' },
                    { label: 'Improvement', val: evaluationResult.percentage_improvement, fmt: (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`, cls: (v: number) => v > 0 ? 'text-emerald-400' : v < 0 ? 'text-red-400' : 'text-text-primary' },
                  ].map(({ label, val, fmt, cls }) => (
                    <div key={label} className="bg-surface-700 border border-border-secondary rounded p-3">
                      <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">{label}</span>
                      <span className={`text-sm font-bold font-mono ${cls ? cls(val ?? 0) : 'text-text-primary'}`}>
                        {val != null ? (fmt ? fmt(val) : `${val.toFixed(2)}`) : 'N/A'}
                      </span>
                    </div>
                  ))}
                </div>
                {(evaluationResult.original_runs.length > 0 || evaluationResult.candidate_runs.length > 0) && (
                  <div className="space-y-2 pt-2">
                    <h4 className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Probes ({evaluationResult.successful_runs} runs)</h4>
                    <div className="overflow-x-auto border border-border-primary rounded">
                      <table className="min-w-full divide-y divide-border-primary text-[11px]">
                        <thead className="text-text-muted font-medium">
                          <tr><th className="px-3 py-2 text-left text-[10px]">Run</th><th className="px-3 py-2 text-left text-[10px]">Original</th><th className="px-3 py-2 text-left text-[10px]">Candidate</th><th className="px-3 py-2 text-left text-[10px]">Status</th></tr>
                        </thead>
                        <tbody className="divide-y divide-border-primary font-mono text-[10px]">
                          {Array.from({ length: Math.max(evaluationResult.original_runs.length, evaluationResult.candidate_runs.length) }).map((_, idx) => {
                            const o = evaluationResult.original_runs[idx];
                            const c = evaluationResult.candidate_runs[idx];
                            return (
                              <tr key={idx} className="hover:bg-surface-700/30">
                                <td className="px-3 py-2 font-bold text-text-secondary">#{idx + 1}</td>
                                <td className="px-3 py-2 text-text-primary">{o?.execution_time_ms != null ? `${o.execution_time_ms.toFixed(3)} ms` : 'N/A'}</td>
                                <td className="px-3 py-2 text-text-primary">{c?.execution_time_ms != null ? `${c.execution_time_ms.toFixed(3)} ms` : 'N/A'}</td>
                                <td className="px-3 py-2"><span className="text-emerald-400 font-sans font-semibold">OK</span></td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            )}
          </section>

          {/* Gate 3: Planner */}
          <section className="rounded-lg border border-border-primary bg-surface-800 p-5 space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-border-primary">
              <span className="w-5 h-5 rounded-full bg-accent-50 text-accent-400 flex items-center justify-center text-[10px] font-bold">3</span>
              <h3 className="text-[11px] font-semibold text-text-primary uppercase tracking-wider">Planner Estimates</h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { label: 'Original Cost', val: evaluationResult.original_total_cost },
                { label: 'Candidate Cost', val: evaluationResult.candidate_total_cost },
              ].map(({ label, val }) => (
                <div key={label} className="bg-surface-700 border border-border-secondary rounded p-3 space-y-1">
                  <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">{label}</span>
                  <div className="text-sm font-bold text-text-primary font-mono">{val != null ? `${val.toFixed(2)} units` : 'N/A'}</div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      {/* History */}
      <section className="rounded-lg border border-border-primary bg-surface-800 p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-border-primary">
          <div className="flex items-center gap-2">
            <History className="w-3.5 h-3.5 text-text-muted" />
            <h3 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">History</h3>
          </div>
          <span className="text-[10px] font-mono text-text-muted">{historyItems.length} records</span>
        </div>
        {historyError && <div className="text-[11px] text-red-400 p-2 bg-red-500/5 rounded">{historyError}</div>}
        {historyItems.length === 0 && !loadingHistory ? (
          <div className="text-center py-6 text-[11px] text-text-muted italic">No evaluations yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border-primary text-[11px]">
              <thead className="text-text-muted font-medium">
                <tr>
                  <th className="px-3 py-2 text-left text-[10px] uppercase tracking-wider">Time</th>
                  <th className="px-3 py-2 text-left text-[10px] uppercase tracking-wider">Correctness</th>
                  <th className="px-3 py-2 text-left text-[10px] uppercase tracking-wider">Recommendation</th>
                  <th className="px-3 py-2 text-left text-[10px] uppercase tracking-wider">Speedup</th>
                  <th className="px-3 py-2 text-right text-[10px] uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-primary">
                {historyItems.map((item) => (
                  <tr key={item.id} className="hover:bg-surface-700/30 transition-colors">
                    <td className="px-3 py-2 text-text-muted text-[10px] whitespace-nowrap font-mono">{new Date(item.created_at).toLocaleString()}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{renderCorrectnessBadge(item.correctness_status)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <span className={`text-[10px] uppercase tracking-wide font-mono font-semibold ${
                        item.recommendation === 'recommend_candidate' ? 'text-emerald-400' :
                        item.recommendation === 'keep_original' ? 'text-amber-400' :
                        item.recommendation === 'do_not_recommend' ? 'text-red-400' : 'text-text-muted'
                      }`}>{item.recommendation.replace('_', ' ')}</span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap font-mono">
                      {item.percentage_improvement != null ? (
                        <span className={item.percentage_improvement > 0 ? 'text-emerald-400 font-bold' : 'text-text-tertiary'}>
                          {item.percentage_improvement > 0 ? '+' : ''}{item.percentage_improvement.toFixed(1)}%
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-3 py-2 text-right whitespace-nowrap">
                      <button onClick={() => handleSelectHistoryItem(item.id)} className="inline-flex items-center gap-1 text-[10px] font-semibold text-accent-400 hover:text-accent-500 cursor-pointer">
                        <span>View</span><ChevronRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};
