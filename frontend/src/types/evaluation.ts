import type { BenchmarkRunResult } from './benchmark';

export type CorrectnessStatus = 'validated' | 'different' | 'inconclusive' | 'rejected';
export type PerformanceAssessment = 'faster' | 'similar' | 'slower' | 'inconclusive';
export type EvaluationRecommendation =
  | 'recommend_candidate'
  | 'keep_original'
  | 'do_not_recommend'
  | 'insufficient_evidence';

export interface EvaluationRequest {
  original_sql: string;
  candidate_sql: string;
  confirmed: boolean;
  repetitions?: number;
  row_limit?: number;
}

export interface EvaluationResponse {
  id: string;
  original_sql: string;
  candidate_sql: string;
  created_at: string;

  // 1. Correctness Dimension
  correctness_status: CorrectnessStatus;
  is_complete_comparison: boolean;
  original_row_count?: number | null;
  candidate_row_count?: number | null;
  mismatch_reason?: string | null;

  // 2. Performance Dimension
  original_median_execution_time_ms?: number | null;
  candidate_median_execution_time_ms?: number | null;
  runtime_difference_ms?: number | null;
  percentage_improvement?: number | null;
  original_total_cost?: number | null;
  candidate_total_cost?: number | null;
  performance_assessment: PerformanceAssessment;

  // 3. Recommendation Dimension
  recommendation: EvaluationRecommendation;
  recommendation_rationale: string;

  // Execution Telemetry
  requested_repetitions: number;
  successful_runs: number;
  failed_runs: number;
  original_runs: BenchmarkRunResult[];
  candidate_runs: BenchmarkRunResult[];
  original_benchmark_id?: string | null;
  candidate_benchmark_id?: string | null;
  error_message?: string | null;
  metadata?: Record<string, unknown>;
}

export interface EvaluationSummary {
  id: string;
  original_sql: string;
  candidate_sql: string;
  created_at: string;
  correctness_status: CorrectnessStatus;
  is_complete_comparison: boolean;
  performance_assessment: PerformanceAssessment;
  recommendation: EvaluationRecommendation;
  percentage_improvement?: number | null;
  original_median_execution_time_ms?: number | null;
  candidate_median_execution_time_ms?: number | null;
}

export interface EvaluationListResponse {
  items: EvaluationSummary[];
  total: number;
  limit: number;
  offset: number;
}
