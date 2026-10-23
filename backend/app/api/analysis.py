"""
API endpoints for query optimization, performance analysis, index recommendations,
rewriting, and plan comparisons.
"""

from fastapi import APIRouter, HTTPException, status

from app.schemas.analysis import AnalyzeQueryRequest, AnalyzeQueryResponse, ErrorResponse
from app.services.sql_validator import validate_read_only_sql, SQLValidationError
from app.services.explain_service import get_execution_plan, ExplainServiceError
from app.services.plan_analyzer import analyze_plan
from app.services.index_advisor import advise_indexes
from app.services.sql_rewriter import generate_rewrite_candidates
from app.services.plan_comparison import compare_plans, PlanComparisonResult

router = APIRouter(prefix="", tags=["Query Analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeQueryResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid, malformed, or unsafe SQL query."},
        503: {"model": ErrorResponse, "description": "Database unavailable."},
        504: {"model": ErrorResponse, "description": "Query plan inspection timed out."},
        500: {"model": ErrorResponse, "description": "Unexpected internal error."},
    },
    summary="Analyze a SQL query execution plan, suggest indexes, generate rewrites, and compare plans",
)
def analyze_sql_query(payload: AnalyzeQueryRequest) -> AnalyzeQueryResponse:
    """
    Validates a read-only SQL query, safely requests its PostgreSQL execution plan,
    produces rule-based findings, generates index recommendations, checks safe rewrite
    candidates, and compares plans when a verified candidate is available.
    """
    # 1. SQL parsing and safety validation
    try:
        normalized_sql, parsed_ast = validate_read_only_sql(payload.sql)
    except SQLValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{e.message} {e.detail}".strip(),
        )

    # 2. Safe execution-plan inspection via PostgreSQL EXPLAIN
    try:
        raw_plan = get_execution_plan(normalized_sql)
    except ExplainServiceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"{e.message} {e.detail}".strip(),
        )

    # 3. Parse plan metrics and extract rule-based findings
    analysis = analyze_plan(raw_plan, normalized_sql)

    # 4. Phase 3: Index Recommendations
    try:
        index_recommendations = advise_indexes(parsed_ast, raw_plan)
    except Exception:
        index_recommendations = []

    # 5. Phase 3: Conservative Rewrite Candidates
    try:
        rewrite_candidates = generate_rewrite_candidates(parsed_ast, normalized_sql)
    except Exception:
        rewrite_candidates = []

    # 6. Phase 3: Plan Comparison Service (compare eligible verified rewritten candidate)
    plan_comparison: Optional[PlanComparisonResult] = None
    eligible_rewrite = next(
        (c for c in rewrite_candidates if c.rewritten_sql and c.semantic_safety == "verified_safe"),
        None
    )
    if eligible_rewrite and eligible_rewrite.rewritten_sql:
        try:
            plan_comparison = compare_plans(normalized_sql, eligible_rewrite.rewritten_sql)
        except Exception:
            plan_comparison = None

    return AnalyzeQueryResponse(
        status=analysis.status,
        validated_sql=analysis.validated_sql,
        plan_summary=analysis.plan_summary,
        scan_nodes=analysis.scan_nodes,
        join_nodes=analysis.join_nodes,
        findings=analysis.findings,
        index_recommendations=index_recommendations,
        rewrite_candidates=rewrite_candidates,
        plan_comparison=plan_comparison,
        metadata=analysis.metadata,
    )
