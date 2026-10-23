import React, { useState } from 'react';
import { AlertCircle, AlertTriangle, Info, CheckCircle, ChevronDown, ChevronUp, Lightbulb } from 'lucide-react';
import type { Finding } from '../../types/analysis';

interface PerformanceFindingsProps {
  findings: Finding[];
}

export const PerformanceFindings: React.FC<PerformanceFindingsProps> = ({ findings }) => {
  const [expandedIndices, setExpandedIndices] = useState<Record<number, boolean>>({ 0: true });

  const toggleExpand = (index: number) => {
    setExpandedIndices((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  if (!findings || findings.length === 0) {
    return (
      <div className="rounded-lg border border-border-primary bg-surface-800 p-6 text-center space-y-2">
        <div className="w-8 h-8 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto">
          <CheckCircle className="w-4 h-4" />
        </div>
        <h3 className="text-[11px] font-semibold text-text-primary uppercase tracking-wider">
          No Bottlenecks Detected
        </h3>
        <p className="text-[11px] text-text-tertiary max-w-xs mx-auto leading-relaxed">
          The plan executes within normal thresholds.
        </p>
      </div>
    );
  }

  const getSeverityStyle = (severity: Finding['severity']) => {
    switch (severity) {
      case 'high':
        return { badge: 'bg-red-500/10 text-red-400 border-red-500/20', icon: <AlertCircle className="w-3 h-3" />, label: 'High' };
      case 'warning':
        return { badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20', icon: <AlertTriangle className="w-3 h-3" />, label: 'Warning' };
      case 'info':
      default:
        return { badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20', icon: <Info className="w-3 h-3" />, label: 'Info' };
    }
  };

  return (
    <div className="rounded-lg border border-border-primary bg-surface-800 overflow-hidden">
      <div className="border-b border-border-primary px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
            Performance Findings
          </h2>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-400 text-text-tertiary">
            {findings.length}
          </span>
        </div>
      </div>

      <div className="divide-y divide-border-primary">
        {findings.map((finding, idx) => {
          const isExpanded = !!expandedIndices[idx];
          const style = getSeverityStyle(finding.severity);
          return (
            <div key={`${finding.code}-${idx}`} className="px-4 py-3 transition-colors hover:bg-surface-700/30">
              <div
                onClick={() => toggleExpand(idx)}
                className="flex items-start justify-between gap-3 cursor-pointer select-none"
              >
                <div className="space-y-1 flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[12px] font-semibold text-text-primary">{finding.title}</span>
                    <span className="font-mono text-[10px] text-text-muted bg-surface-600 px-1.5 py-0.5 rounded">
                      {finding.code}
                    </span>
                  </div>
                  <p className="text-[11px] text-text-tertiary leading-relaxed">{finding.explanation}</p>
                </div>

                <div className="flex items-center gap-2 shrink-0 pt-0.5">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border ${style.badge}`}>
                    {style.icon}
                    <span>{style.label}</span>
                  </span>
                  <button type="button" className="text-text-muted hover:text-text-secondary p-0.5">
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {isExpanded && (
                <div className="mt-3 pt-3 border-t border-border-primary space-y-2 animate-fade-up">
                  <div className="bg-surface-900 border border-border-secondary rounded p-2.5 font-mono text-[11px] text-text-secondary">
                    <span className="text-text-muted font-sans font-medium mr-1.5 uppercase text-[10px] tracking-wide">
                      Evidence:
                    </span>
                    {finding.evidence}
                  </div>
                  {finding.recommendation && (
                    <div className="bg-accent-50/50 border border-accent-200/20 rounded p-2.5 text-[11px] text-accent-500 flex items-start gap-2">
                      <Lightbulb className="w-3.5 h-3.5 text-accent-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-accent-400 mr-1.5">Tip:</span>
                        <span>{finding.recommendation}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
