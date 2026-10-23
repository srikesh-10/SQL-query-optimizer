"""
Pydantic Schemas for Query Analysis, Index Recommendations, Rewrites, and Plan Comparison.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.plan_analyzer import PlanSummary, ScanNode, JoinNode, Finding
from app.services.index_advisor import IndexRecommendation
from app.services.sql_rewriter import RewriteCandidate
from app.services.plan_comparison import PlanComparisonResult


class AnalyzeQueryRequest(BaseModel):
    sql: str = Field(..., description="A single read-only SQL query to analyze.")


class AnalyzeQueryResponse(BaseModel):
    status: str
    validated_sql: str
    plan_summary: PlanSummary
    scan_nodes: List[ScanNode]
    join_nodes: List[JoinNode]
    findings: List[Finding]
    index_recommendations: List[IndexRecommendation] = Field(default_factory=list)
    rewrite_candidates: List[RewriteCandidate] = Field(default_factory=list)
    plan_comparison: Optional[PlanComparisonResult] = None
    metadata: Dict[str, Any]


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
