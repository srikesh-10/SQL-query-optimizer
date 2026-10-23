export interface PlanSummary {
  root_node_type: string;
  total_cost: number;
  startup_cost: number;
  plan_rows: number;
  plan_width: number;
  planning_time_ms?: number | null;
  node_count: number;
}

export interface ScanNode {
  node_type: string;
  relation_name?: string | null;
  alias?: string | null;
  index_name?: string | null;
  filter_condition?: string | null;
  index_condition?: string | null;
  total_cost: number;
  plan_rows: number;
}

export interface JoinNode {
  node_type: string;
  join_type?: string | null;
  join_filter?: string | null;
  hash_condition?: string | null;
  total_cost: number;
  plan_rows: number;
}

export interface Finding {
  code: string;
  title: string;
  severity: 'info' | 'warning' | 'high';
  evidence: string;
  explanation: string;
  recommendation?: string | null;
}

export interface IndexRecommendation {
  recommendation_id: string;
  table_name: string;
  columns: string[];
  index_type: string;
  reason: string;
  supporting_evidence: string;
  estimated_benefit: string;
  confidence: string;
  tradeoffs: string;
  suggested_ddl?: string | null;
}

export interface RewriteCandidate {
  rule_id: string;
  title: string;
  description: string;
  original_sql: string;
  rewritten_sql?: string | null;
  reason: string;
  confidence: string;
  semantic_safety: string;
  limitations: string;
}

export interface PlanComparisonResult {
  original_sql: string;
  candidate_sql: string;
  original_total_cost: number;
  candidate_total_cost: number;
  original_plan_rows: number;
  candidate_plan_rows: number;
  original_root_node: string;
  candidate_root_node: string;
  cost_difference: number;
  percentage_change?: number | null;
  interpretation: string;
  note: string;
}

export interface AnalyzeQueryResponse {
  status: string;
  validated_sql: string;
  plan_summary: PlanSummary;
  scan_nodes: ScanNode[];
  join_nodes: JoinNode[];
  findings: Finding[];
  index_recommendations?: IndexRecommendation[];
  rewrite_candidates?: RewriteCandidate[];
  plan_comparison?: PlanComparisonResult | null;
  metadata: {
    engine?: string;
    plan_type?: string;
    is_runtime_benchmark?: boolean;
    note?: string;
    [key: string]: unknown;
  };
}

export interface HealthResponse {
  status: string;
  environment: string;
  version: string;
}

export interface ReadinessResponse {
  status: string;
  database: string;
  environment: string;
  version: string;
  detail?: string | null;
}
