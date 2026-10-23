export interface ColumnCompatibility {
  original_columns: string[];
  candidate_columns: string[];
  counts_match: boolean;
  names_match: boolean;
  compatible: boolean;
  details?: string | null;
}

export type EquivalenceStatus = 'equivalent' | 'different' | 'inconclusive' | 'rejected';

export interface CompareResultsRequest {
  original_sql: string;
  candidate_sql: string;
  confirmed: boolean;
  row_limit?: number;
}

export interface CompareResultsResponse {
  status: EquivalenceStatus;
  matched?: boolean | null;
  original_row_count?: number | null;
  candidate_row_count?: number | null;
  is_complete_comparison: boolean;
  row_limit_applied: number;
  column_compatibility?: ColumnCompatibility | null;
  order_deterministic: boolean;
  ordering_mode: 'ordered' | 'multiset' | 'none' | string;
  mismatch_reason?: string | null;
  error_message?: string | null;
  metadata?: Record<string, unknown>;
}
