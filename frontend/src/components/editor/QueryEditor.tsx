import React, { useState, useMemo, useRef } from 'react';
import { Play, RotateCcw, Copy, Check, Sparkles } from 'lucide-react';
import { EXAMPLE_QUERIES } from '../../data/exampleQueries';

interface QueryEditorProps {
  sql: string;
  onChange: (value: string) => void;
  onAnalyze: () => void;
  loading: boolean;
  onClear: () => void;
}

export const QueryEditor: React.FC<QueryEditorProps> = ({
  sql,
  onChange,
  onAnalyze,
  loading,
  onClear,
}) => {
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleCopy = async () => {
    if (!sql) return;
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleSelectExample = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = EXAMPLE_QUERIES.find((q) => q.id === e.target.value);
    if (selected) {
      onChange(selected.sql);
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (!loading && sql.trim()) {
        onAnalyze();
      }
    }
  };

  const lines = useMemo(() => {
    const count = sql.split('\n').length;
    return Array.from({ length: Math.max(count, 4) }, (_, i) => i + 1);
  }, [sql]);

  return (
    <div className="rounded-lg border border-border-primary bg-surface-800 overflow-hidden transition-all">
      {/* Toolbar */}
      <div className="border-b border-border-primary px-4 py-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
            SQL Query Input
          </span>

          <div className="h-3 w-px bg-border-secondary" />

          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-accent-400" />
            <select
              onChange={handleSelectExample}
              defaultValue=""
              className="text-[11px] bg-surface-700 hover:bg-surface-600 border border-border-secondary text-text-secondary rounded px-2 py-1 focus:outline-hidden focus:ring-1 focus:ring-accent-300 cursor-pointer transition-colors"
            >
              <option value="" disabled>
                Load example...
              </option>
              {EXAMPLE_QUERIES.map((q) => (
                <option key={q.id} value={q.id}>
                  {q.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={handleCopy}
            disabled={!sql}
            title="Copy SQL"
            aria-label="Copy SQL"
            className="inline-flex items-center gap-1 text-[11px] text-text-tertiary hover:text-text-secondary bg-surface-700 hover:bg-surface-600 border border-border-secondary px-2 py-1 rounded disabled:opacity-30 transition-colors cursor-pointer"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-status-success" />
                <span className="text-status-success font-medium">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Copy</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={onClear}
            disabled={!sql || loading}
            aria-label="Clear SQL editor"
            className="inline-flex items-center gap-1 text-[11px] text-text-tertiary hover:text-text-secondary bg-surface-700 hover:bg-surface-600 border border-border-secondary px-2 py-1 rounded disabled:opacity-30 transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Clear</span>
          </button>

          <button
            type="button"
            onClick={onAnalyze}
            disabled={!sql.trim() || loading}
            className="inline-flex items-center gap-1.5 text-[11px] font-semibold bg-accent-200 hover:bg-accent-300 active:bg-accent-400 text-white disabled:bg-surface-400 disabled:text-text-muted disabled:cursor-not-allowed px-3 py-1 rounded transition-colors cursor-pointer"
          >
            <Play className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Analyzing...' : 'Analyze Query'}</span>
            <kbd className="hidden sm:inline-block ml-0.5 px-1 py-0.5 text-[9px] font-mono bg-accent-100/50 text-accent-500 rounded">
              ⌘↵
            </kbd>
          </button>
        </div>
      </div>

      {/* Editor */}
      <div className="relative flex min-h-[150px] max-h-[380px] overflow-hidden focus-within:ring-1 focus-within:ring-accent-200/30 transition-shadow">
        {/* Line numbers */}
        <div
          aria-hidden="true"
          className="select-none py-3 px-3 bg-surface-900 text-text-muted font-mono text-[12px] leading-[1.7] text-right border-r border-border-primary min-w-[38px]"
        >
          {lines.map((num) => (
            <div key={num}>{num}</div>
          ))}
        </div>

        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={sql}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="-- Enter a read-only SELECT query..."
            disabled={loading}
            rows={lines.length}
            spellCheck={false}
            className="w-full h-full py-3 px-4 font-mono text-[12px] text-text-primary bg-surface-900 resize-y focus:outline-hidden leading-[1.7] placeholder:text-text-muted"
          />
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border-primary px-4 py-1 flex items-center justify-between text-[10px] text-text-muted">
        <div className="flex items-center gap-2">
          <span>PostgreSQL 16</span>
          <span className="text-border-secondary">·</span>
          <span>Read-Only EXPLAIN</span>
        </div>
        <div className="flex items-center gap-2 font-mono">
          <span>{lines.length} lines</span>
          <span className="text-border-secondary">·</span>
          <span>{sql.trim().length} chars</span>
        </div>
      </div>
    </div>
  );
};
