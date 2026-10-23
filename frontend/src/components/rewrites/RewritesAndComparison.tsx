import React, { useState } from 'react';
import {
  Copy, Check, Scale, AlertCircle, CheckCircle2, XCircle,
  AlertTriangle, ShieldAlert, Play, RotateCcw, CheckSquare, ChevronDown, ChevronUp,
} from 'lucide-react';
import type { RewriteCandidate, PlanComparisonResult } from '../../types/analysis';
import type { CompareResultsResponse } from '../../types/equivalence';
import * as api from '../../services/api';

interface RewritesAndComparisonProps {
  candidates?: RewriteCandidate[];
  comparison?: PlanComparisonResult | null;
  originalSql?: string;
  onValidate?: (origSql: string, candSql: string, confirmed: boolean) => Promise<CompareResultsResponse>;
}

export const RewritesAndComparison: React.FC<RewritesAndComparisonProps> = ({
  candidates = [],
  comparison,
  originalSql = '',
  onValidate,
}) => {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [openValidationRuleId, setOpenValidationRuleId] = useState<string | null>(null);
  const [confirmedMap, setConfirmedMap] = useState<Record<string, boolean>>({});
  const [validatingMap, setValidatingMap] = useState<Record<string, boolean>>({});
  const [validationResultMap, setValidationResultMap] = useState<Record<string, CompareResultsResponse>>({});
  const [validationErrorMap, setValidationErrorMap] = useState<Record<string, string>>({});

  const handleCopy = async (key: string, text?: string | null) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    } catch {}
  };

  const toggleValidationPanel = (ruleId: string) => {
    setOpenValidationRuleId(openValidationRuleId === ruleId ? null : ruleId);
  };

  const handleRunValidation = async (ruleId: string, candidateSql: string) => {
    const isConfirmed = !!confirmedMap[ruleId];
    if (!isConfirmed) return;
    setValidatingMap((prev) => ({ ...prev, [ruleId]: true }));
    setValidationErrorMap((prev) => { const next = { ...prev }; delete next[ruleId]; return next; });
    try {
      const execute = onValidate || ((orig, cand, conf) => api.compareResults(orig, cand, conf));
      const res = await execute(originalSql, candidateSql, isConfirmed);
      setValidationResultMap((prev) => ({ ...prev, [ruleId]: res }));
    } catch (err) {
      const errorMsg = err instanceof api.ApiError ? err.detail : err instanceof Error ? err.message : 'Validation failed.';
      setValidationErrorMap((prev) => ({ ...prev, [ruleId]: errorMsg }));
    } finally {
      setValidatingMap((prev) => ({ ...prev, [ruleId]: false }));
    }
  };

  return (
    <div className="space-y-4">
      {/* Plan Comparison */}
      {comparison && (
        <div className="rounded-lg border border-border-primary bg-surface-800 overflow-hidden">
          <div className="border-b border-border-primary px-4 py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Scale className="w-3.5 h-3.5 text-accent-400" />
              <h2 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Plan Comparison</h2>
            </div>
            <span className="text-[10px] text-text-muted font-mono">Original vs Rewritten</span>
          </div>
          <div className="p-4 space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="bg-surface-700 border border-border-secondary rounded p-3">
                <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">Original</span>
                <span className="text-sm font-bold text-text-primary font-mono mt-0.5 block">{comparison.original_total_cost.toFixed(1)}</span>
                <span className="text-[10px] text-text-muted block truncate">{comparison.original_root_node}</span>
              </div>
              <div className="bg-surface-700 border border-border-secondary rounded p-3">
                <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">Candidate</span>
                <span className="text-sm font-bold text-text-primary font-mono mt-0.5 block">{comparison.candidate_total_cost.toFixed(1)}</span>
                <span className="text-[10px] text-text-muted block truncate">{comparison.candidate_root_node}</span>
              </div>
              <div className="bg-surface-700 border border-border-secondary rounded p-3">
                <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">Difference</span>
                <span className={`text-sm font-bold font-mono mt-0.5 block ${
                  comparison.cost_difference > 0 ? 'text-emerald-400' : comparison.cost_difference < 0 ? 'text-red-400' : 'text-text-primary'
                }`}>
                  {comparison.cost_difference > 0 ? '-' : ''}{Math.abs(comparison.cost_difference).toFixed(1)}
                </span>
                <span className="text-[10px] text-text-muted block">{comparison.percentage_change != null ? `${comparison.percentage_change}%` : '0%'}</span>
              </div>
              <div className="bg-surface-700 border border-border-secondary rounded p-3">
                <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">Rows</span>
                <span className="text-sm font-bold text-text-primary font-mono mt-0.5 block">{comparison.candidate_plan_rows.toLocaleString()}</span>
                <span className="text-[10px] text-text-muted block">vs {comparison.original_plan_rows.toLocaleString()}</span>
              </div>
            </div>
            <div className="bg-accent-50/30 border border-accent-200/15 rounded p-3 text-[11px] text-accent-500">
              <span className="font-semibold text-accent-400 mr-1">Interpretation:</span>
              {comparison.interpretation}
            </div>
          </div>
        </div>
      )}

      {/* Candidates */}
      <div className="rounded-lg border border-border-primary bg-surface-800 overflow-hidden">
        <div className="border-b border-border-primary px-4 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Rewrite Candidates</h2>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-400 text-text-tertiary">{candidates.length}</span>
          </div>
        </div>

        {candidates.length === 0 ? (
          <div className="p-6 text-center text-[11px] text-text-muted italic">No rewrite candidates identified.</div>
        ) : (
          <div className="divide-y divide-border-primary">
            {candidates.map((cand) => {
              const isSafe = cand.semantic_safety === 'verified_safe';
              const isOpen = openValidationRuleId === cand.rule_id;
              const isConfirmed = !!confirmedMap[cand.rule_id];
              const isValidating = !!validatingMap[cand.rule_id];
              const validationResult = validationResultMap[cand.rule_id];
              const validationError = validationErrorMap[cand.rule_id];

              return (
                <div key={cand.rule_id} className="p-4 space-y-3 hover:bg-surface-700/20 transition-colors">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-0.5 min-w-0">
                      <h3 className="text-[12px] font-semibold text-text-primary">{cand.title}</h3>
                      <p className="text-[11px] text-text-tertiary leading-relaxed">{cand.description}</p>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold shrink-0 border ${
                      isSafe ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}>
                      {isSafe ? 'Safe' : 'Heuristic'}
                    </span>
                  </div>

                  <div className="text-[11px] text-text-tertiary">
                    <strong className="text-text-secondary mr-1">Rationale:</strong> {cand.reason}
                  </div>

                  {cand.rewritten_sql ? (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-text-secondary font-medium">Rewritten SQL:</span>
                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleCopy(`rewrite-${cand.rule_id}`, cand.rewritten_sql)}
                            className="inline-flex items-center gap-1 text-[10px] text-text-tertiary hover:text-text-secondary bg-surface-700 border border-border-secondary px-2 py-1 rounded cursor-pointer transition-colors"
                          >
                            {copiedKey === `rewrite-${cand.rule_id}` ? (
                              <><Check className="w-3 h-3 text-status-success" /><span className="text-status-success">Copied</span></>
                            ) : (
                              <><Copy className="w-3 h-3" /><span>Copy</span></>
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => toggleValidationPanel(cand.rule_id)}
                            className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-accent-50 hover:bg-accent-100/50 text-accent-400 border border-accent-200/20 font-semibold transition-colors cursor-pointer"
                          >
                            <CheckSquare className="w-3 h-3" />
                            <span>Validate Results</span>
                            {isOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                          </button>
                        </div>
                      </div>

                      <pre className="bg-surface-900 text-text-primary p-3 rounded text-[11px] font-mono overflow-x-auto leading-relaxed border border-border-primary">
                        {cand.rewritten_sql}
                      </pre>

                      {/* Validation drawer */}
                      {isOpen && (
                        <div className="bg-surface-700 border border-border-secondary rounded-lg p-4 space-y-3 text-[11px] animate-fade-up">
                          <div className="flex items-center justify-between border-b border-border-primary pb-2">
                            <div className="flex items-center gap-1.5 font-semibold text-text-primary">
                              <CheckSquare className="w-3.5 h-3.5 text-accent-400" />
                              <span>Result Equivalence</span>
                            </div>
                            <span className="text-[10px] text-text-muted font-mono">READ ONLY · 1,000 rows max</span>
                          </div>

                          <div className="bg-amber-500/5 border border-amber-500/15 rounded p-3 text-amber-400 space-y-1">
                            <div className="font-semibold flex items-center gap-1 text-amber-300">
                              <AlertTriangle className="w-3 h-3 shrink-0" />
                              <span>Validation Execution Notice:</span>
                            </div>
                            <p className="text-[10px] text-amber-400/80 leading-relaxed">
                              Both queries will be executed in a <code className="bg-amber-500/10 px-1 rounded font-mono">REPEATABLE READ READ ONLY</code> transaction with a 3,000ms timeout.
                            </p>
                          </div>

                          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                            <label className="flex items-center gap-2 cursor-pointer select-none">
                              <input
                                type="checkbox"
                                checked={isConfirmed}
                                onChange={(e) => setConfirmedMap((prev) => ({ ...prev, [cand.rule_id]: e.target.checked }))}
                                disabled={isValidating}
                                aria-label="I confirm and authorize executing both queries to compare results"
                                className="rounded border-border-hover text-accent-300 focus:ring-accent-300 w-3.5 h-3.5 cursor-pointer bg-surface-600"
                              />
                              <span className="text-text-secondary">I confirm and authorize executing both queries to compare results</span>
                            </label>
                            <button
                              type="button"
                              onClick={() => handleRunValidation(cand.rule_id, cand.rewritten_sql!)}
                              disabled={!isConfirmed || isValidating}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-accent-200 hover:bg-accent-300 text-white rounded text-[11px] font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                            >
                              {isValidating ? (
                                <><RotateCcw className="w-3 h-3 animate-spin" /><span>Validating...</span></>
                              ) : (
                                <><Play className="w-3 h-3" /><span>Execute Validation</span></>
                              )}
                            </button>
                          </div>

                          {validationError && (
                            <div className="bg-red-500/5 border border-red-500/15 rounded p-3 text-red-400 flex items-start gap-2">
                              <XCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                              <div>
                                <p className="font-semibold text-[11px]">Error</p>
                                <p className="text-[10px] font-mono mt-0.5">{validationError}</p>
                              </div>
                            </div>
                          )}

                          {validationResult && (
                            <div className="space-y-3 pt-2 border-t border-border-primary">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2">
                                  <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Status:</span>
                                  {validationResult.status === 'equivalent' && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                      <CheckCircle2 className="w-3 h-3 mr-1" /> Equivalent Results
                                    </span>
                                  )}
                                  {validationResult.status === 'different' && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/10 text-red-400 border border-red-500/20">
                                      <XCircle className="w-3 h-3 mr-1" /> Different Results
                                    </span>
                                  )}
                                  {validationResult.status === 'inconclusive' && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                      <AlertTriangle className="w-3 h-3 mr-1" /> Inconclusive
                                    </span>
                                  )}
                                  {validationResult.status === 'rejected' && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-surface-400 text-text-secondary border border-border-secondary">
                                      <ShieldAlert className="w-3 h-3 mr-1" /> Rejected
                                    </span>
                                  )}
                                </div>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium border ${
                                  validationResult.is_complete_comparison
                                    ? 'bg-surface-400 text-text-tertiary border-border-secondary'
                                    : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                }`}>
                                  {validationResult.is_complete_comparison ? 'Complete Comparison' : `Truncated at ${validationResult.row_limit_applied} rows`}
                                </span>
                              </div>

                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                                {[
                                  { label: 'Orig Rows', val: validationResult.original_row_count },
                                  { label: 'Cand Rows', val: validationResult.candidate_row_count },
                                  { label: 'Ordering', val: validationResult.order_deterministic ? 'Deterministic' : validationResult.ordering_mode },
                                  { label: 'Cols Match', val: validationResult.column_compatibility ? (validationResult.column_compatibility.counts_match ? `Yes (${validationResult.column_compatibility.candidate_columns.length})` : 'No') : 'N/A' },
                                ].map(({ label, val }) => (
                                  <div key={label} className="bg-surface-800 border border-border-primary rounded p-2">
                                    <span className="text-[10px] text-text-muted uppercase block">{label}</span>
                                    <span className="text-[11px] font-bold font-mono text-text-primary">{val != null ? val.toLocaleString?.() ?? val : 'N/A'}</span>
                                  </div>
                                ))}
                              </div>

                              {validationResult.mismatch_reason && (
                                <div className={`p-2.5 rounded text-[10px] leading-relaxed border ${
                                  validationResult.status === 'equivalent' ? 'bg-emerald-500/5 border-emerald-500/15 text-emerald-400'
                                    : validationResult.status === 'different' ? 'bg-red-500/5 border-red-500/15 text-red-400'
                                    : 'bg-amber-500/5 border-amber-500/15 text-amber-400'
                                }`}>
                                  <strong>Details:</strong> {validationResult.mismatch_reason}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-[11px] text-amber-400 bg-amber-500/5 p-2.5 rounded border border-amber-500/15">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>Auto-generation skipped. Review suggestion manually.</span>
                    </div>
                  )}

                  <div className="text-[10px] text-text-muted">
                    <strong className="text-text-tertiary mr-1">Limitations:</strong> {cand.limitations}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
