import React, { useState, useEffect } from 'react';
import { Header } from './components/layout/Header';
import { QueryEditor } from './components/editor/QueryEditor';
import { PlanSummaryCards } from './components/analysis/PlanSummaryCards';
import { PerformanceFindings } from './components/analysis/PerformanceFindings';
import { ExecutionPlanView } from './components/plan/ExecutionPlanView';
import { IndexRecommendationsView } from './components/recommendations/IndexRecommendationsView';
import { RewritesAndComparison } from './components/rewrites/RewritesAndComparison';
import { BenchmarkSection } from './components/benchmark/BenchmarkSection';
import { EvaluationSection } from './components/evaluation/EvaluationSection';
import * as api from './services/api';
import { analyzeQuery, checkBackendReadiness, ApiError } from './services/api';
import type { AnalyzeQueryResponse, ReadinessResponse } from './types/analysis';
import { AlertCircle, Terminal, Activity, Timer, Scale, Sparkles } from 'lucide-react';
import { EXAMPLE_QUERIES } from './data/exampleQueries';

const DEFAULT_SQL = "SELECT * FROM users WHERE first_name = 'Emily';";

export const App: React.FC = () => {
  const [sql, setSql] = useState<string>(DEFAULT_SQL);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeQueryResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'analysis' | 'benchmark' | 'evaluation'>('analysis');
  const [backendStatus, setBackendStatus] = useState<ReadinessResponse | null>(null);
  const [checkingStatus, setCheckingStatus] = useState<boolean>(false);

  const refreshStatus = async () => {
    setCheckingStatus(true);
    const status = await checkBackendReadiness();
    setBackendStatus(status);
    setCheckingStatus(false);
  };

  useEffect(() => { refreshStatus(); }, []);

  const handleAnalyze = async () => {
    if (!sql.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeQuery(sql);
      setResult(data);
      setActiveTab('analysis');
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else if (err instanceof Error) setError(err.message);
      else setError('An unexpected error occurred.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => { setSql(''); setError(null); setResult(null); };
  const handleSelectPreset = (presetSql: string) => { setSql(presetSql); setError(null); };

  const tabs = [
    { id: 'analysis' as const, label: 'Analysis', fullLabel: 'Query Analysis', icon: Activity },
    { id: 'benchmark' as const, label: 'Benchmark', fullLabel: 'Safe Execution Benchmark', icon: Timer },
    { id: 'evaluation' as const, label: 'Evaluation', fullLabel: 'Optimizer Evaluation', icon: Scale },
  ];

  return (
    <div className="min-h-screen bg-surface-900 flex flex-col">
      <Header backendStatus={backendStatus} checkingStatus={checkingStatus} onRefreshStatus={refreshStatus} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-5">
        {/* Editor */}
        <section>
          <QueryEditor sql={sql} onChange={setSql} onAnalyze={handleAnalyze} loading={loading} onClear={handleClear} />
        </section>

        {/* Tab Navigation */}
        <div className="flex items-center justify-between border-b border-border-primary">
          <nav className="flex gap-0.5" aria-label="Workspace Navigation">
            {tabs.map(({ id, label, fullLabel, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                aria-label={fullLabel}
                className={`inline-flex items-center gap-1.5 py-2 px-3.5 text-[11px] font-medium border-b-2 transition-all cursor-pointer ${
                  activeTab === id
                    ? 'border-accent-400 text-accent-400'
                    : 'border-transparent text-text-muted hover:text-text-secondary'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{label}</span>
              </button>
            ))}
          </nav>
          <span className="text-[10px] font-mono text-text-muted hidden sm:inline">
            PostgreSQL 16
          </span>
        </div>

        {/* Error */}
        {error && activeTab === 'analysis' && (
          <div className="bg-red-500/5 border border-red-500/15 rounded-lg p-3.5 flex items-start gap-2.5 text-red-400 animate-fade-up">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <h3 className="text-[11px] font-semibold uppercase tracking-wider">Analysis Request Failed</h3>
              <p className="text-[10px] font-mono whitespace-pre-wrap leading-relaxed opacity-80">{error}</p>
            </div>
          </div>
        )}

        {/* Tab Content */}
        {activeTab === 'evaluation' ? (
          <section className="animate-fade-up">
            <EvaluationSection
              currentOriginalSql={result?.validated_sql || sql}
              rewriteCandidates={result?.rewrite_candidates || []}
              onEvaluate={(origSql, candSql, confirmed, reps) => api.createEvaluation(origSql, candSql, confirmed, reps)}
            />
          </section>
        ) : activeTab === 'benchmark' ? (
          <section className="animate-fade-up">
            <BenchmarkSection currentSql={sql} onBenchmark={(benchSql, reps) => api.createBenchmark(benchSql, reps)} />
          </section>
        ) : (
          <>
            {/* Empty State */}
            {!result && !loading && !error && (
              <div className="rounded-lg border border-border-primary bg-surface-800 p-8 text-center space-y-4">
                <div className="w-9 h-9 bg-accent-50 text-accent-400 rounded-lg flex items-center justify-center mx-auto border border-accent-200/20">
                  <Terminal className="w-4.5 h-4.5" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-[12px] font-semibold text-text-primary">
                    Ready to Analyze
                  </h3>
                  <p className="text-[11px] text-text-tertiary max-w-md mx-auto leading-relaxed">
                    Choose an example or enter a PostgreSQL SELECT query. Click <strong className="text-text-secondary">Analyze</strong> to inspect execution costs, detect scans, and review rewrite candidates.
                  </p>
                </div>
                <div className="pt-2 flex flex-wrap items-center justify-center gap-2 max-w-2xl mx-auto">
                  {EXAMPLE_QUERIES.map((q) => (
                    <button
                      key={q.id}
                      type="button"
                      onClick={() => handleSelectPreset(q.sql)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-border-secondary hover:border-accent-200/30 bg-surface-700 hover:bg-surface-600 text-[11px] font-medium text-text-tertiary hover:text-accent-400 transition-colors cursor-pointer"
                    >
                      <Sparkles className="w-3 h-3 text-accent-400/60" />
                      <span>{q.title}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Results */}
            {result && (
              <div className="space-y-5 animate-fade-up">
                <section><PlanSummaryCards summary={result.plan_summary} /></section>
                <section><ExecutionPlanView scanNodes={result.scan_nodes} joinNodes={result.join_nodes} /></section>
                <section className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
                  <PerformanceFindings findings={result.findings} />
                  <IndexRecommendationsView recommendations={result.index_recommendations} />
                </section>
                <section>
                  <RewritesAndComparison
                    candidates={result.rewrite_candidates}
                    comparison={result.plan_comparison}
                    originalSql={result.validated_sql || sql}
                  />
                </section>
              </div>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border-primary py-3 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-[10px] text-text-muted gap-2">
          <div>SQL Query Optimizer &amp; Performance Intelligence Platform</div>
          <div className="flex items-center gap-2 font-mono">
            <span>PostgreSQL 16</span>
            <span className="text-border-secondary">·</span>
            <span>FastAPI</span>
            <span className="text-border-secondary">·</span>
            <span>React 19</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
