import React from 'react';
import type { PlanSummary } from '../../types/analysis';

interface PlanSummaryCardsProps {
  summary: PlanSummary;
}

export const PlanSummaryCards: React.FC<PlanSummaryCardsProps> = ({ summary }) => {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border-primary rounded-lg overflow-hidden border border-border-primary">
      {/* Root Strategy */}
      <div className="bg-surface-800 p-4 space-y-1.5">
        <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">
          Root Strategy
        </span>
        <span className="text-sm font-bold text-text-primary font-mono tracking-tight truncate block" title={summary.root_node_type}>
          {summary.root_node_type}
        </span>
        <span className="text-[10px] text-text-muted block">
          {summary.node_count === 1 ? 'Single-node plan' : `${summary.node_count} nodes`}
        </span>
      </div>

      {/* Total Cost */}
      <div className="bg-surface-800 p-4 space-y-1.5">
        <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">
          Est. Total Cost
        </span>
        <div className="flex items-baseline gap-1.5">
          <span className="text-sm font-bold text-accent-400 font-mono">
            {summary.total_cost.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })}
          </span>
          <span className="text-[10px] text-text-muted">units</span>
        </div>
        <span className="text-[10px] text-text-muted block">
          Startup: <span className="font-mono text-text-tertiary">{summary.startup_cost.toFixed(1)}</span>
        </span>
      </div>

      {/* Plan Rows */}
      <div className="bg-surface-800 p-4 space-y-1.5">
        <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">
          Est. Plan Rows
        </span>
        <div className="flex items-baseline gap-1.5">
          <span className="text-sm font-bold text-text-primary font-mono">
            {summary.plan_rows.toLocaleString()}
          </span>
          <span className="text-[10px] text-text-muted">rows</span>
        </div>
        <span className="text-[10px] text-text-muted block">
          Width: <span className="font-mono text-text-tertiary">{summary.plan_width}B</span>
        </span>
      </div>

      {/* Plan Nodes */}
      <div className="bg-surface-800 p-4 space-y-1.5">
        <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">
          Plan Nodes
        </span>
        <div className="flex items-baseline gap-1.5">
          <span className="text-sm font-bold text-text-primary font-mono">
            {summary.node_count}
          </span>
          <span className="text-[10px] text-text-muted">nodes</span>
        </div>
        <span className="text-[10px] text-text-muted block">
          {summary.planning_time_ms != null
            ? `Planning: ${summary.planning_time_ms.toFixed(2)}ms`
            : 'Static evaluation'}
        </span>
      </div>
    </div>
  );
};
