import React, { useState } from 'react';
import { Search, Shuffle, Database, Eye } from 'lucide-react';
import type { ScanNode, JoinNode } from '../../types/analysis';

interface ExecutionPlanViewProps {
  scanNodes: ScanNode[];
  joinNodes: JoinNode[];
}

export const ExecutionPlanView: React.FC<ExecutionPlanViewProps> = ({ scanNodes, joinNodes }) => {
  const [activeTab, setActiveTab] = useState<'tree' | 'nodes'>('tree');
  const [selectedNodeIndex, setSelectedNodeIndex] = useState<{ type: 'scan' | 'join'; index: number } | null>(
    scanNodes.length > 0 ? { type: 'scan', index: 0 } : null
  );

  const totalOps = scanNodes.length + joinNodes.length;

  const getNodeColor = (nodeType: string) => {
    switch (nodeType) {
      case 'Seq Scan':
        return { badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20', dot: 'bg-amber-400' };
      case 'Index Scan':
      case 'Index Only Scan':
      case 'Bitmap Index Scan':
        return { badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', dot: 'bg-emerald-400' };
      case 'Hash Join':
        return { badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20', dot: 'bg-blue-400' };
      case 'Nested Loop':
        return { badge: 'bg-purple-500/10 text-purple-400 border-purple-500/20', dot: 'bg-purple-400' };
      default:
        return { badge: 'bg-surface-400/50 text-text-secondary border-border-secondary', dot: 'bg-text-muted' };
    }
  };

  const selectedScan = selectedNodeIndex?.type === 'scan' ? scanNodes[selectedNodeIndex.index] : null;
  const selectedJoin = selectedNodeIndex?.type === 'join' ? joinNodes[selectedNodeIndex.index] : null;

  return (
    <div className="rounded-lg border border-border-primary bg-surface-800 overflow-hidden">
      {/* Header */}
      <div className="border-b border-border-primary px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h2 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
            Execution Plan
          </h2>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-400 text-text-tertiary">
            {totalOps} ops
          </span>
        </div>

        <div className="flex items-center gap-0.5 bg-surface-700 p-0.5 rounded text-[11px]">
          <button
            type="button"
            onClick={() => setActiveTab('tree')}
            className={`px-2.5 py-1 rounded font-medium transition-colors cursor-pointer ${
              activeTab === 'tree'
                ? 'bg-surface-500 text-text-primary'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            Tree View
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('nodes')}
            className={`px-2.5 py-1 rounded font-medium transition-colors cursor-pointer ${
              activeTab === 'nodes'
                ? 'bg-surface-500 text-text-primary'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            Table View
          </button>
        </div>
      </div>

      {activeTab === 'tree' ? (
        <div className="p-5 space-y-4">
          <div className="bg-surface-900 border border-border-primary rounded-lg p-4 overflow-x-auto">
            <div className="min-w-[500px] flex flex-col items-center">
              {joinNodes.length > 0 ? (
                <>
                  {joinNodes.map((join, jIdx) => {
                    const colors = getNodeColor(join.node_type);
                    const isSelected = selectedNodeIndex?.type === 'join' && selectedNodeIndex.index === jIdx;
                    return (
                      <div key={`tree-join-${jIdx}`} className="flex flex-col items-center">
                        <button
                          type="button"
                          onClick={() => setSelectedNodeIndex({ type: 'join', index: jIdx })}
                          className={`text-left p-3 rounded-lg border bg-surface-800 transition-all cursor-pointer min-w-[220px] max-w-[300px] ${
                            isSelected
                              ? 'ring-1 ring-accent-300 border-accent-200/30'
                              : 'border-border-secondary hover:border-border-hover'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${colors.badge}`}>
                              {join.node_type}
                            </span>
                            <span className="font-mono text-[11px] text-accent-400 font-bold">
                              {join.total_cost.toFixed(1)}
                            </span>
                          </div>
                          <div className="text-[11px] text-text-secondary truncate">
                            {join.join_type ? `${join.join_type} join` : 'Join coordinator'}
                          </div>
                          <div className="text-[10px] text-text-muted mt-0.5">
                            {join.plan_rows.toLocaleString()} est. rows
                          </div>
                        </button>

                        <svg className="w-full h-8" viewBox="0 0 400 32" preserveAspectRatio="none">
                          <line x1="200" y1="0" x2="200" y2="16" stroke="var(--color-border-secondary)" strokeWidth="2" strokeDasharray="3 3" />
                          {scanNodes.length > 1 && (
                            <>
                              <line x1="80" y1="16" x2="320" y2="16" stroke="var(--color-border-secondary)" strokeWidth="2" />
                              <line x1="80" y1="16" x2="80" y2="32" stroke="var(--color-border-secondary)" strokeWidth="2" />
                              <line x1="320" y1="16" x2="320" y2="32" stroke="var(--color-border-secondary)" strokeWidth="2" />
                            </>
                          )}
                          {scanNodes.length === 1 && (
                            <line x1="200" y1="16" x2="200" y2="32" stroke="var(--color-border-secondary)" strokeWidth="2" />
                          )}
                        </svg>
                      </div>
                    );
                  })}
                </>
              ) : null}

              <div className="flex flex-wrap items-center justify-center gap-3">
                {scanNodes.map((scan, sIdx) => {
                  const colors = getNodeColor(scan.node_type);
                  const isSelected = selectedNodeIndex?.type === 'scan' && selectedNodeIndex.index === sIdx;
                  return (
                    <button
                      key={`tree-scan-${sIdx}`}
                      type="button"
                      onClick={() => setSelectedNodeIndex({ type: 'scan', index: sIdx })}
                      className={`text-left p-3 rounded-lg border bg-surface-800 transition-all cursor-pointer min-w-[180px] max-w-[240px] ${
                        isSelected
                          ? 'ring-1 ring-accent-300 border-accent-200/30'
                          : 'border-border-secondary hover:border-border-hover'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${colors.badge}`}>
                          {scan.node_type}
                        </span>
                        <span className="font-mono text-[11px] text-text-secondary font-bold">
                          {scan.total_cost.toFixed(1)}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-text-primary truncate">
                        <Database className="w-3 h-3 text-text-muted shrink-0" />
                        <span>{scan.relation_name || 'Scan Op'}</span>
                      </div>
                      {scan.index_name && (
                        <div className="text-[10px] text-accent-400 font-mono mt-1 truncate">
                          idx: {scan.index_name}
                        </div>
                      )}
                      <div className="text-[10px] text-text-muted mt-0.5">
                        {scan.plan_rows.toLocaleString()} rows
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Inspector */}
          {(selectedScan || selectedJoin) && (
            <div className="bg-surface-700 border border-border-secondary rounded-lg p-4 space-y-3 animate-fade-up">
              <div className="flex items-center justify-between border-b border-border-primary pb-2">
                <div className="flex items-center gap-2">
                  <Eye className="w-3.5 h-3.5 text-accent-400" />
                  <span className="text-[11px] font-semibold text-text-primary uppercase tracking-wider">
                    {selectedScan ? selectedScan.node_type : selectedJoin?.node_type}
                  </span>
                </div>
                <span className="text-[10px] font-mono text-text-muted">
                  {selectedScan?.relation_name || selectedJoin?.join_type || 'Internal'}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px]">
                <div className="bg-surface-800 border border-border-primary rounded p-2.5">
                  <span className="text-[10px] uppercase font-medium text-text-muted block mb-0.5">Cost</span>
                  <span className="font-mono font-bold text-text-primary">
                    {selectedScan?.total_cost.toFixed(1) || selectedJoin?.total_cost.toFixed(1)} units
                  </span>
                </div>
                <div className="bg-surface-800 border border-border-primary rounded p-2.5">
                  <span className="text-[10px] uppercase font-medium text-text-muted block mb-0.5">Rows</span>
                  <span className="font-mono font-bold text-text-primary">
                    {(selectedScan?.plan_rows || selectedJoin?.plan_rows)?.toLocaleString()}
                  </span>
                </div>
                <div className="bg-surface-800 border border-border-primary rounded p-2.5">
                  <span className="text-[10px] uppercase font-medium text-text-muted block mb-0.5">Target</span>
                  <span className="font-mono text-text-secondary">
                    {selectedScan?.relation_name || selectedJoin?.join_type || 'N/A'}
                    {selectedScan?.alias && selectedScan.alias !== selectedScan.relation_name ? ` (${selectedScan.alias})` : ''}
                  </span>
                </div>
              </div>

              {selectedScan?.filter_condition && (
                <div className="bg-surface-800 border border-border-primary rounded p-2.5 text-[11px] font-mono text-text-secondary">
                  <span className="text-text-muted font-sans font-medium mr-1.5">Filter:</span>
                  {selectedScan.filter_condition}
                </div>
              )}
              {selectedScan?.index_name && (
                <div className="bg-surface-800 border border-border-primary rounded p-2.5 text-[11px] font-mono text-accent-400">
                  <span className="text-text-muted font-sans font-medium mr-1.5">Index:</span>
                  {selectedScan.index_name}
                </div>
              )}
              {selectedJoin?.hash_condition && (
                <div className="bg-surface-800 border border-border-primary rounded p-2.5 text-[11px] font-mono text-text-secondary">
                  <span className="text-text-muted font-sans font-medium mr-1.5">Hash:</span>
                  {selectedJoin.hash_condition}
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Scans */}
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
              <Search className="w-3 h-3 text-accent-400" />
              <span>Scans ({scanNodes.length})</span>
            </div>
            {scanNodes.length === 0 ? (
              <p className="text-[11px] text-text-muted italic p-3 bg-surface-700 rounded">No scans.</p>
            ) : (
              scanNodes.map((scan, idx) => {
                const colors = getNodeColor(scan.node_type);
                return (
                  <div key={`scan-${idx}`} className="border border-border-secondary rounded-lg p-3 text-[11px] space-y-1.5 bg-surface-700">
                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${colors.badge}`}>{scan.node_type}</span>
                      <span className="text-text-muted font-mono">
                        Cost: <strong className="text-text-primary">{scan.total_cost.toFixed(1)}</strong>
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-text-secondary">
                      <Database className="w-3 h-3 text-text-muted" />
                      <span>
                        <strong className="text-text-primary">{scan.relation_name || 'N/A'}</strong>
                        {scan.alias && scan.alias !== scan.relation_name && (
                          <span className="text-text-muted"> ({scan.alias})</span>
                        )}
                      </span>
                    </div>
                    {scan.index_name && (
                      <div className="text-accent-400 font-mono text-[10px]">Index: <span className="font-semibold">{scan.index_name}</span></div>
                    )}
                    {scan.filter_condition && (
                      <div className="bg-surface-800 p-1.5 rounded font-mono text-[10px] text-text-secondary truncate">
                        <span className="text-text-muted font-sans">Filter: </span>{scan.filter_condition}
                      </div>
                    )}
                    <div className="text-[10px] text-text-muted">
                      Est. Rows: <span className="text-text-tertiary font-medium font-mono">{scan.plan_rows.toLocaleString()}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Joins */}
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
              <Shuffle className="w-3 h-3 text-blue-400" />
              <span>Joins ({joinNodes.length})</span>
            </div>
            {joinNodes.length === 0 ? (
              <p className="text-[11px] text-text-muted italic p-3 bg-surface-700 rounded">No joins (single-table query).</p>
            ) : (
              joinNodes.map((join, idx) => (
                <div key={`join-${idx}`} className="border border-border-secondary bg-surface-700 rounded-lg p-3 text-[11px] space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded text-[10px] font-semibold">
                      {join.node_type}
                    </span>
                    <span className="text-text-muted font-mono">
                      Cost: <strong className="text-text-primary">{join.total_cost.toFixed(1)}</strong>
                    </span>
                  </div>
                  {join.join_type && (
                    <div className="text-text-secondary">
                      Type: <span className="font-medium text-text-primary capitalize">{join.join_type}</span> Join
                    </div>
                  )}
                  {join.hash_condition && (
                    <div className="bg-surface-800 p-1.5 rounded font-mono text-[10px] text-text-secondary">
                      <span className="text-text-muted font-sans">Condition: </span>{join.hash_condition}
                    </div>
                  )}
                  {join.join_filter && (
                    <div className="bg-surface-800 p-1.5 rounded font-mono text-[10px] text-text-secondary">
                      <span className="text-text-muted font-sans">Filter: </span>{join.join_filter}
                    </div>
                  )}
                  <div className="text-[10px] text-text-muted">
                    Est. Rows: <span className="text-text-tertiary font-medium font-mono">{join.plan_rows.toLocaleString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
