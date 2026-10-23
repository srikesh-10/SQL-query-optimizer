"""
Pydantic Schemas for Optimizer Evaluation & Performance Scoring.
Combines correctness gating, empirical performance benchmarking, and transparent recommendations.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.benchmark import BenchmarkRunResult


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    original_sql: str = Field(..., description="The baseline read-only SELECT query.")
    candidate_sql: str = Field(..., description="The candidate rewritten SELECT query to evaluate.")
    confirmed: bool = Field(..., description="Explicit confirmation that user authorizes executing both queries.")
    repetitions: int = Field(default=3, ge=1, le=5, description="Number of benchmark repetitions per query (1 to 5).")
    row_limit: int = Field(default=1000, ge=1, le=5000, description="Maximum rows to compare for correctness validation.")


class EvaluationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_sql: str
    candidate_sql: str
    created_at: datetime
    correctness_status: Literal["validated", "different", "inconclusive", "rejected"]
    is_complete_comparison: bool
    performance_assessment: Literal["faster", "similar", "slower", "inconclusive"]
    recommendation: Literal["recommend_candidate", "keep_original", "do_not_recommend", "insufficient_evidence"]
    original_median_execution_time_ms: Optional[float] = None
    candidate_median_execution_time_ms: Optional[float] = None
    percentage_improvement: Optional[float] = None
    original_total_cost: Optional[float] = None
    candidate_total_cost: Optional[float] = None
    recommendation_rationale: str


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_sql: str
    candidate_sql: str
    created_at: datetime

    # 1. Correctness Dimension
    correctness_status: Literal["validated", "different", "inconclusive", "rejected"]
    is_complete_comparison: bool
    original_row_count: Optional[int] = None
    candidate_row_count: Optional[int] = None
    mismatch_reason: Optional[str] = None

    # 2. Performance Dimension
    original_median_execution_time_ms: Optional[float] = None
    candidate_median_execution_time_ms: Optional[float] = None
    runtime_difference_ms: Optional[float] = None
    percentage_improvement: Optional[float] = None
    original_total_cost: Optional[float] = None
    candidate_total_cost: Optional[float] = None
    performance_assessment: Literal["faster", "similar", "slower", "inconclusive"]

    # 3. Recommendation Dimension
    recommendation: Literal["recommend_candidate", "keep_original", "do_not_recommend", "insufficient_evidence"]
    recommendation_rationale: str

    # Execution telemetry & runs
    requested_repetitions: int
    successful_runs: int
    failed_runs: int
    original_runs: List[BenchmarkRunResult] = Field(default_factory=list)
    candidate_runs: List[BenchmarkRunResult] = Field(default_factory=list)
    original_benchmark_id: Optional[str] = None
    candidate_benchmark_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[EvaluationSummary]
    total: int
    limit: int
    offset: int
