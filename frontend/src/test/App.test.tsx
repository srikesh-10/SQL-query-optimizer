import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import * as api from '../services/api';

describe('SQL Query Optimizer Frontend App', () => {
  it('renders application header and initial editor state', () => {
    render(<App />);
    expect(screen.getByText('SQL Query Optimizer')).toBeInTheDocument();
    expect(screen.getByText('SQL Query Input')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /analyze query/i })).toBeInTheDocument();
  });

  it('populates editor when example query is selected', () => {
    render(<App />);
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'user-first-name' } });

    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveValue("SELECT * FROM users WHERE first_name = 'Emily';");
  });

  it('displays loading state during analysis and renders results', async () => {
    const mockResponse: api.AnalyzeQueryResponse = {
      status: 'success',
      validated_sql: "SELECT * FROM users WHERE first_name = 'Emily'",
      plan_summary: {
        root_node_type: 'Seq Scan',
        total_cost: 236.0,
        startup_cost: 0.0,
        plan_rows: 248,
        plan_width: 64,
        planning_time_ms: 0.12,
        node_count: 1,
      },
      scan_nodes: [
        {
          node_type: 'Seq Scan',
          relation_name: 'users',
          alias: 'users',
          total_cost: 236.0,
          plan_rows: 248,
        },
      ],
      join_nodes: [],
      findings: [
        {
          code: 'PERF_SEQ_SCAN_SMALL_TABLE',
          title: "Sequential Scan on Table 'users'",
          severity: 'info',
          evidence: "Table 'users' scanned sequentially.",
          explanation: "Sequential scan chosen by optimizer.",
        },
      ],
      index_recommendations: [
        {
          recommendation_id: 'IDX_REC_001',
          table_name: 'users',
          columns: ['first_name'],
          index_type: 'btree',
          reason: "High-frequency filtering predicate on 'users.first_name'.",
          supporting_evidence: "Sequential Scan across users.",
          estimated_benefit: 'high',
          confidence: 'high',
          tradeoffs: 'Consumes index space.',
          suggested_ddl: 'CREATE INDEX idx_users_first_name ON users (first_name);',
        },
      ],
      rewrite_candidates: [
        {
          rule_id: 'REWRITE_EXPAND_SELECT_STAR',
          title: 'Explicit Column Projection Expansion',
          description: 'Replaces SELECT * with columns.',
          original_sql: "SELECT * FROM users WHERE first_name = 'Emily'",
          rewritten_sql: "SELECT id, email, first_name FROM users WHERE first_name = 'Emily'",
          reason: 'Retrieves only necessary columns.',
          confidence: 'high',
          semantic_safety: 'verified_safe',
          limitations: 'Single table only.',
        },
      ],
      plan_comparison: {
        original_sql: "SELECT * FROM users WHERE first_name = 'Emily'",
        candidate_sql: "SELECT id, email, first_name FROM users WHERE first_name = 'Emily'",
        original_total_cost: 236.0,
        candidate_total_cost: 236.0,
        original_plan_rows: 248,
        candidate_plan_rows: 248,
        original_root_node: 'Seq Scan',
        candidate_root_node: 'Seq Scan',
        cost_difference: 0.0,
        percentage_change: 0.0,
        interpretation: 'Planner estimated identical total cost.',
        note: 'Values are planner cost units.',
      },
      metadata: { engine: 'PostgreSQL' },
    };

    vi.spyOn(api, 'analyzeQuery').mockResolvedValueOnce(mockResponse);

    render(<App />);
    const analyzeButton = screen.getByRole('button', { name: /analyze query/i });
    fireEvent.click(analyzeButton);

    await waitFor(() => {
      expect(screen.getByText('Performance Findings')).toBeInTheDocument();
      expect(screen.getByText("Sequential Scan on Table 'users'")).toBeInTheDocument();
      expect(screen.getByText('Index Advisor Recommendations')).toBeInTheDocument();
      expect(screen.getByText('CREATE INDEX idx_users_first_name ON users (first_name);')).toBeInTheDocument();
    });
  });

  it('renders error message when API call fails', async () => {
    vi.spyOn(api, 'analyzeQuery').mockRejectedValueOnce(
      new api.ApiError(400, 'SQL Validation Failed: Unsupported statement type')
    );

    render(<App />);
    const analyzeButton = screen.getByRole('button', { name: /analyze query/i });
    fireEvent.click(analyzeButton);

    await waitFor(() => {
      expect(screen.getByText('Analysis Request Failed')).toBeInTheDocument();
      expect(screen.getByText(/Unsupported statement type/)).toBeInTheDocument();
    });
  });

  it('switches to Safe Execution Benchmark tab and requires confirmation', async () => {
    render(<App />);

    // Switch to Benchmark tab
    const benchmarkTab = screen.getByRole('button', { name: /safe execution benchmark/i });
    fireEvent.click(benchmarkTab);

    // Verify safety notice is displayed
    expect(screen.getByText(/Execution Safety Notice:/i)).toBeInTheDocument();

    const runBenchmarkBtn = screen.getByRole('button', { name: /run benchmark/i });
    expect(runBenchmarkBtn).toBeDisabled();

    // Check confirmation checkbox
    const confirmCheckbox = screen.getByRole('checkbox');
    fireEvent.click(confirmCheckbox);
    expect(runBenchmarkBtn).toBeEnabled();
  });

  it('executes benchmark and renders measured metrics', async () => {
    const mockBenchmarkResponse = {
      id: 'mock-bench-1',
      sql: "SELECT * FROM users WHERE first_name = 'Emily';",
      created_at: new Date().toISOString(),
      status: 'completed' as const,
      requested_repetitions: 3,
      successful_runs: 3,
      failed_runs: 0,
      median_execution_time_ms: 2.345,
      median_planning_time_ms: 0.150,
      estimated_total_cost: 236.0,
      error_message: null,
      runs: [
        {
          run_order: 1,
          status: 'success' as const,
          execution_time_ms: 2.1,
          planning_time_ms: 0.14,
          total_cost: 236.0,
          actual_rows: 248,
        },
        {
          run_order: 2,
          status: 'success' as const,
          execution_time_ms: 2.345,
          planning_time_ms: 0.15,
          total_cost: 236.0,
          actual_rows: 248,
        },
        {
          run_order: 3,
          status: 'success' as const,
          execution_time_ms: 2.5,
          planning_time_ms: 0.16,
          total_cost: 236.0,
          actual_rows: 248,
        },
      ],
      note: 'Execution times are actual measurements.',
    };

    const createBenchmarkSpy = vi
      .spyOn(api, 'createBenchmark')
      .mockResolvedValueOnce(mockBenchmarkResponse);
    vi.spyOn(api, 'getBenchmarkHistory').mockResolvedValue({ items: [], total: 0, limit: 10, offset: 0 });

    render(<App />);

    // Switch to Benchmark tab
    fireEvent.click(screen.getByRole('button', { name: /safe execution benchmark/i }));

    // Confirm and click run
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);

    const runBtn = screen.getByRole('button', { name: /run benchmark/i });
    expect(runBtn).not.toBeDisabled();
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(createBenchmarkSpy).toHaveBeenCalled();
      expect(screen.getAllByText('2.345').length).toBeGreaterThan(0);
      expect(screen.getAllByText('236.00').length).toBeGreaterThan(0);
      expect(screen.getByText(/3 \/ 3 succeeded/i)).toBeInTheDocument();
    });
  });

  it('ensures analyze action does not trigger benchmark execution or result validation', async () => {
    const createBenchmarkSpy = vi.spyOn(api, 'createBenchmark');
    const compareResultsSpy = vi.spyOn(api, 'compareResults');
    const mockAnalysisResponse = {
      status: 'success',
      validated_sql: 'SELECT 1',
      plan_summary: {
        root_node_type: 'Result',
        total_cost: 0.01,
        startup_cost: 0.0,
        plan_rows: 1,
        plan_width: 4,
        node_count: 1,
      },
      scan_nodes: [],
      join_nodes: [],
      findings: [],
      metadata: { engine: 'PostgreSQL' },
    };
    vi.spyOn(api, 'analyzeQuery').mockResolvedValueOnce(mockAnalysisResponse as any);

    render(<App />);
    const analyzeButton = screen.getByRole('button', { name: /analyze query/i });
    fireEvent.click(analyzeButton);

    await waitFor(() => {
      expect(screen.getByText('Result')).toBeInTheDocument();
    });
    // Neither benchmark nor compareResults should have been called
    expect(createBenchmarkSpy).not.toHaveBeenCalled();
    expect(compareResultsSpy).not.toHaveBeenCalled();
  });

  it('toggles Validate Results action on rewrite candidate and requires confirmation', async () => {
    const mockResponse: api.AnalyzeQueryResponse = {
      status: 'success',
      validated_sql: "SELECT * FROM users WHERE first_name = 'Emily'",
      plan_summary: {
        root_node_type: 'Seq Scan',
        total_cost: 236.0,
        startup_cost: 0.0,
        plan_rows: 248,
        plan_width: 64,
        planning_time_ms: 0.12,
        node_count: 1,
      },
      scan_nodes: [],
      join_nodes: [],
      findings: [],
      index_recommendations: [],
      rewrite_candidates: [
        {
          rule_id: 'REWRITE_EXPAND_SELECT_STAR',
          title: 'Explicit Column Projection Expansion',
          description: 'Replaces SELECT * with columns.',
          original_sql: "SELECT * FROM users WHERE first_name = 'Emily'",
          rewritten_sql: "SELECT id, email, first_name FROM users WHERE first_name = 'Emily'",
          reason: 'Retrieves only necessary columns.',
          confidence: 'high',
          semantic_safety: 'verified_safe',
          limitations: 'Single table only.',
        },
      ],
      metadata: { engine: 'PostgreSQL' },
    };

    vi.spyOn(api, 'analyzeQuery').mockResolvedValueOnce(mockResponse);

    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /analyze query/i }));

    await waitFor(() => {
      expect(screen.getByText('Validate Results')).toBeInTheDocument();
    });

    // Click Validate Results button to toggle panel
    fireEvent.click(screen.getByRole('button', { name: /validate results/i }));

    // Safety notice displayed
    expect(screen.getByText(/Validation Execution Notice:/i)).toBeInTheDocument();

    const executeBtn = screen.getByRole('button', { name: /execute validation/i });
    expect(executeBtn).toBeDisabled();

    // Confirm checkbox
    const confirmCheck = screen.getByRole('checkbox', {
      name: /i confirm and authorize executing both queries to compare results/i,
    });
    fireEvent.click(confirmCheck);
    expect(executeBtn).toBeEnabled();
  });

  it('executes compareResults and displays equivalent results', async () => {
    const mockResponse: api.AnalyzeQueryResponse = {
      status: 'success',
      validated_sql: "SELECT * FROM users WHERE first_name = 'Emily'",
      plan_summary: {
        root_node_type: 'Seq Scan',
        total_cost: 236.0,
        startup_cost: 0.0,
        plan_rows: 248,
        plan_width: 64,
        planning_time_ms: 0.12,
        node_count: 1,
      },
      scan_nodes: [],
      join_nodes: [],
      findings: [],
      index_recommendations: [],
      rewrite_candidates: [
        {
          rule_id: 'REWRITE_EXPAND_SELECT_STAR',
          title: 'Explicit Column Projection Expansion',
          description: 'Replaces SELECT * with columns.',
          original_sql: "SELECT * FROM users WHERE first_name = 'Emily'",
          rewritten_sql: "SELECT id, email, first_name FROM users WHERE first_name = 'Emily'",
          reason: 'Retrieves only necessary columns.',
          confidence: 'high',
          semantic_safety: 'verified_safe',
          limitations: 'Single table only.',
        },
      ],
      metadata: { engine: 'PostgreSQL' },
    };

    const mockValidationResult = {
      status: 'equivalent' as const,
      matched: true,
      original_row_count: 248,
      candidate_row_count: 248,
      is_complete_comparison: true,
      row_limit_applied: 1000,
      column_compatibility: {
        original_columns: ['id', 'email', 'first_name'],
        candidate_columns: ['id', 'email', 'first_name'],
        counts_match: true,
        names_match: true,
        compatible: true,
        details: null,
      },
      order_deterministic: false,
      ordering_mode: 'multiset',
      mismatch_reason: 'Results matched as multisets (neither query specifies ORDER BY).',
      error_message: null,
    };

    vi.spyOn(api, 'analyzeQuery').mockResolvedValueOnce(mockResponse);
    const compareSpy = vi.spyOn(api, 'compareResults').mockResolvedValueOnce(mockValidationResult);

    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /analyze query/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /validate results/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /validate results/i }));

    const confirmCheck = screen.getByRole('checkbox', {
      name: /i confirm and authorize executing both queries to compare results/i,
    });
    fireEvent.click(confirmCheck);

    const executeBtn = screen.getByRole('button', { name: /execute validation/i });
    fireEvent.click(executeBtn);

    await waitFor(() => {
      expect(compareSpy).toHaveBeenCalled();
      expect(screen.getByText('Equivalent Results')).toBeInTheDocument();
      expect(screen.getByText('Complete Comparison')).toBeInTheDocument();
      expect(screen.getAllByText('248').length).toBeGreaterThan(0);
    });
  });

  it('displays different and rejected validation results appropriately', async () => {
    const mockResponse: api.AnalyzeQueryResponse = {
      status: 'success',
      validated_sql: "SELECT * FROM users WHERE first_name = 'Emily'",
      plan_summary: {
        root_node_type: 'Seq Scan',
        total_cost: 236.0,
        startup_cost: 0.0,
        plan_rows: 248,
        plan_width: 64,
        planning_time_ms: 0.12,
        node_count: 1,
      },
      scan_nodes: [],
      join_nodes: [],
      findings: [],
      index_recommendations: [],
      rewrite_candidates: [
        {
          rule_id: 'REWRITE_EXPAND_SELECT_STAR',
          title: 'Explicit Column Projection Expansion',
          description: 'Replaces SELECT * with columns.',
          original_sql: "SELECT * FROM users WHERE first_name = 'Emily'",
          rewritten_sql: "SELECT id, email, first_name FROM users WHERE first_name = 'Emily'",
          reason: 'Retrieves only necessary columns.',
          confidence: 'high',
          semantic_safety: 'verified_safe',
          limitations: 'Single table only.',
        },
      ],
      metadata: { engine: 'PostgreSQL' },
    };

    const mockDifferentResult = {
      status: 'different' as const,
      matched: false,
      original_row_count: 248,
      candidate_row_count: 200,
      is_complete_comparison: true,
      row_limit_applied: 1000,
      column_compatibility: {
        original_columns: ['id', 'email', 'first_name'],
        candidate_columns: ['id', 'email', 'first_name'],
        counts_match: true,
        names_match: true,
        compatible: true,
        details: null,
      },
      order_deterministic: false,
      ordering_mode: 'multiset',
      mismatch_reason: 'Row count mismatch: original query returned 248 rows, candidate query returned 200 rows.',
      error_message: null,
    };

    vi.spyOn(api, 'analyzeQuery').mockResolvedValueOnce(mockResponse);
    vi.spyOn(api, 'compareResults').mockResolvedValueOnce(mockDifferentResult);

    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /analyze query/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /validate results/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /validate results/i }));
    fireEvent.click(
      screen.getByRole('checkbox', {
        name: /i confirm and authorize executing both queries to compare results/i,
      })
    );
    fireEvent.click(screen.getByRole('button', { name: /execute validation/i }));

    await waitFor(() => {
      expect(screen.getByText('Different Results')).toBeInTheDocument();
      expect(screen.getByText(/Row count mismatch: original query returned 248 rows/i)).toBeInTheDocument();
    });
  });

  it('switches to Optimizer Evaluation tab and enforces confirmation', async () => {
    vi.spyOn(api, 'getEvaluationHistory').mockResolvedValue({ items: [], total: 0, limit: 10, offset: 0 });

    render(<App />);

    const evalTab = screen.getByRole('button', { name: /optimizer evaluation/i });
    fireEvent.click(evalTab);

    expect(screen.getByText(/Optimizer Evaluation & Performance Scoring/i)).toBeInTheDocument();
    expect(
      screen.getByText(/I authorize executing both queries against PostgreSQL for unified evaluation/i)
    ).toBeInTheDocument();

    const startBtn = screen.getByRole('button', { name: /start unified evaluation/i });
    expect(startBtn).toBeDisabled();

    // Check confirmation checkbox
    const confirmCheckbox = screen.getByRole('checkbox', { name: /authorize evaluation query execution/i });
    fireEvent.click(confirmCheckbox);

    // Need both queries populated: set candidate query
    const candidateTextarea = screen.getByRole('textbox', { name: /evaluation candidate query/i });
    fireEvent.change(candidateTextarea, { target: { value: "SELECT id FROM users WHERE first_name = 'Emily';" } });

    expect(startBtn).not.toBeDisabled();
  });

  it('executes evaluation and renders correctness-first and faster recommendation', async () => {
    vi.spyOn(api, 'getEvaluationHistory').mockResolvedValue({ items: [], total: 0, limit: 10, offset: 0 });
    const mockEvalFaster: api.EvaluationResponse = {
      id: 'eval-1234',
      original_sql: "SELECT * FROM users WHERE first_name = 'Emily';",
      candidate_sql: "SELECT id, email FROM users WHERE first_name = 'Emily';",
      created_at: '2026-10-21T12:00:00Z',
      correctness_status: 'validated',
      is_complete_comparison: true,
      original_row_count: 248,
      candidate_row_count: 248,
      original_median_execution_time_ms: 10.0,
      candidate_median_execution_time_ms: 5.0,
      runtime_difference_ms: 5.0,
      percentage_improvement: 50.0,
      original_total_cost: 236.0,
      candidate_total_cost: 110.0,
      performance_assessment: 'faster',
      recommendation: 'recommend_candidate',
      recommendation_rationale: 'Candidate query demonstrated a 50.0% measured runtime improvement with verified result equivalence.',
      requested_repetitions: 3,
      successful_runs: 3,
      failed_runs: 0,
      original_runs: [],
      candidate_runs: [],
    };
    const createEvalSpy = vi.spyOn(api, 'createEvaluation').mockResolvedValueOnce(mockEvalFaster);

    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /optimizer evaluation/i }));

    const candidateTextarea = screen.getByRole('textbox', { name: /evaluation candidate query/i });
    fireEvent.change(candidateTextarea, { target: { value: "SELECT id, email FROM users WHERE first_name = 'Emily';" } });

    const confirmCheckbox = screen.getByRole('checkbox', { name: /authorize evaluation query execution/i });
    fireEvent.click(confirmCheckbox);
    fireEvent.click(screen.getByRole('button', { name: /start unified evaluation/i }));

    await waitFor(() => {
      expect(createEvalSpy).toHaveBeenCalled();
      expect(screen.getByText('Validated Equivalent')).toBeInTheDocument();
      expect(screen.getByText(/Recommendation: Adopt Candidate Rewrite/i)).toBeInTheDocument();
      expect(screen.getByText('+50.0%')).toBeInTheDocument();
      expect(screen.getByText('10.00 ms')).toBeInTheDocument();
      expect(screen.getByText('5.00 ms')).toBeInTheDocument();
    });
  });

  it('handles evaluation with different results and prevents recommendation', async () => {
    vi.spyOn(api, 'getEvaluationHistory').mockResolvedValue({ items: [], total: 0, limit: 10, offset: 0 });
    const mockEvalDifferent: api.EvaluationResponse = {
      id: 'eval-diff-5678',
      original_sql: "SELECT * FROM users WHERE first_name = 'Emily';",
      candidate_sql: "SELECT * FROM users WHERE first_name = 'Bob';",
      created_at: '2026-10-21T12:00:00Z',
      correctness_status: 'different',
      is_complete_comparison: true,
      original_row_count: 248,
      candidate_row_count: 10,
      mismatch_reason: 'Row count mismatch: 248 vs 10 rows',
      performance_assessment: 'inconclusive',
      recommendation: 'do_not_recommend',
      recommendation_rationale: 'Candidate query produces different results. Benchmarking was aborted to prevent optimizing an incorrect query.',
      requested_repetitions: 3,
      successful_runs: 0,
      failed_runs: 0,
      original_runs: [],
      candidate_runs: [],
    };
    vi.spyOn(api, 'createEvaluation').mockResolvedValueOnce(mockEvalDifferent);

    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /optimizer evaluation/i }));

    const candidateTextarea = screen.getByRole('textbox', { name: /evaluation candidate query/i });
    fireEvent.change(candidateTextarea, { target: { value: "SELECT * FROM users WHERE first_name = 'Bob';" } });

    const confirmCheckbox = screen.getByRole('checkbox', { name: /authorize evaluation query execution/i });
    fireEvent.click(confirmCheckbox);
    fireEvent.click(screen.getByRole('button', { name: /start unified evaluation/i }));

    await waitFor(() => {
      expect(screen.getByText('Different Results')).toBeInTheDocument();
      expect(screen.getByText(/Recommendation: Do Not Recommend Rewrite/i)).toBeInTheDocument();
      expect(screen.getByText(/Performance benchmarking was skipped because query correctness was not validated/i)).toBeInTheDocument();
    });
  });

  it('confirms ordinary analysis does not trigger evaluation API', async () => {
    const mockResponse: api.AnalyzeQueryResponse = {
      status: 'success',
      validated_sql: "SELECT * FROM users WHERE first_name = 'Emily'",
      plan_summary: {
        root_node_type: 'Seq Scan',
        total_cost: 236.0,
        startup_cost: 0.0,
        plan_rows: 248,
        plan_width: 64,
        planning_time_ms: 0.12,
        node_count: 1,
      },
      scan_nodes: [],
      join_nodes: [],
      findings: [],
      index_recommendations: [],
      rewrite_candidates: [],
      metadata: { engine: 'PostgreSQL' },
    };

    const analyzeSpy = vi.spyOn(api, 'analyzeQuery').mockResolvedValueOnce(mockResponse);
    const evalSpy = vi.spyOn(api, 'createEvaluation');

    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /analyze query/i }));

    await waitFor(() => {
      expect(analyzeSpy).toHaveBeenCalled();
      expect(evalSpy).not.toHaveBeenCalled();
    });
  });
});

