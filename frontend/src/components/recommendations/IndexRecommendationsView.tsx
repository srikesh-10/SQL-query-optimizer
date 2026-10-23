import React, { useState } from 'react';
import { Copy, Check, ShieldCheck, Database } from 'lucide-react';
import type { IndexRecommendation } from '../../types/analysis';

interface IndexRecommendationsViewProps {
  recommendations?: IndexRecommendation[];
}

export const IndexRecommendationsView: React.FC<IndexRecommendationsViewProps> = ({
  recommendations = [],
}) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="rounded-lg border border-border-primary bg-surface-800 p-6 text-center space-y-2">
        <div className="w-8 h-8 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto">
          <ShieldCheck className="w-4 h-4" />
        </div>
        <h3 className="text-[11px] font-semibold text-text-primary uppercase tracking-wider">
          No Missing Indexes
        </h3>
        <p className="text-[11px] text-text-tertiary max-w-xs mx-auto leading-relaxed">
          Existing indexes cover queried predicates and join keys.
        </p>
      </div>
    );
  }

  const handleCopyDDL = async (id: string, ddl?: string | null) => {
    if (!ddl) return;
    try {
      await navigator.clipboard.writeText(ddl);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div className="rounded-lg border border-border-primary bg-surface-800 overflow-hidden">
      <div className="border-b border-border-primary px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
            Index Advisor Recommendations
          </h2>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
            {recommendations.length} proposed
          </span>
        </div>
      </div>

      <div className="divide-y divide-border-primary">
        {recommendations.map((rec) => {
          const isCopied = copiedId === rec.recommendation_id;
          return (
            <div key={rec.recommendation_id} className="p-4 space-y-3 hover:bg-surface-700/30 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <div className="flex items-center gap-1 text-text-secondary">
                      <Database className="w-3 h-3 text-text-muted" />
                      <span className="text-[12px] font-semibold text-text-primary">{rec.table_name}</span>
                    </div>
                    <span className="text-[10px] font-mono text-accent-400 bg-accent-50/50 border border-accent-200/20 px-1.5 py-0.5 rounded">
                      ({rec.columns.join(', ')})
                    </span>
                  </div>
                  <p className="text-[11px] text-text-tertiary leading-relaxed">{rec.reason}</p>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-surface-400 text-text-tertiary">
                    {rec.index_type}
                  </span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                    rec.confidence === 'high'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                  }`}>
                    {rec.confidence}
                  </span>
                </div>
              </div>

              <div className="text-[11px] text-text-tertiary bg-surface-700 border border-border-secondary rounded p-2.5">
                <strong className="text-text-secondary mr-1">Evidence:</strong>
                {rec.supporting_evidence}
              </div>

              {rec.suggested_ddl && (
                <div className="relative group">
                  <pre className="bg-surface-900 text-accent-500 p-3 rounded text-[11px] font-mono overflow-x-auto leading-relaxed border border-border-primary">
                    {rec.suggested_ddl}
                  </pre>
                  <button
                    type="button"
                    onClick={() => handleCopyDDL(rec.recommendation_id, rec.suggested_ddl)}
                    className="absolute top-2 right-2 inline-flex items-center gap-1 text-[10px] bg-surface-600 hover:bg-surface-500 text-text-secondary px-2 py-1 rounded border border-border-secondary cursor-pointer transition-colors"
                  >
                    {isCopied ? (
                      <><Check className="w-3 h-3 text-status-success" /><span className="text-status-success">Copied</span></>
                    ) : (
                      <><Copy className="w-3 h-3" /><span>Copy</span></>
                    )}
                  </button>
                </div>
              )}

              <div className="text-[10px] text-text-muted bg-surface-700 border border-border-secondary rounded p-2.5">
                <strong className="text-text-tertiary mr-1">Tradeoffs:</strong>
                {rec.tradeoffs}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
