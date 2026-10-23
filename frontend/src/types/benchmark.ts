export interface BenchmarkRunResult {
  run_order: number;
  status: 'success' | 'failed' | 'timeout';
  execution_time_ms?: number | null;
  planning_time_ms?: number | null;
  total_cost?: number | null;
  plan_rows?: number | null;
  actual_rows?: number | null;
  error_message?: string | null;
}

export interface BenchmarkResponse {
  id: string;
  sql: string;
  created_at: string;
  status: 'completed' | 'partial_failure' | 'failed';
  requested_repetitions: number;
  successful_runs: number;
  failed_runs: number;
  median_execution_time_ms?: number | null;
  median_planning_time_ms?: number | null;
  estimated_total_cost?: number | null;
  error_message?: string | null;
  runs: BenchmarkRunResult[];
  note: string;
}

export interface BenchmarkSummary {
  id: string;
  sql: string;
  created_at: string;
  status: string;
  requested_repetitions: number;
  successful_runs: number;
  failed_runs: number;
  median_execution_time_ms?: number | null;
  estimated_total_cost?: number | null;
}

export interface BenchmarkListResponse {
  items: BenchmarkSummary[];
  total: number;
  limit: number;
  offset: number;
}
