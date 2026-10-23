"""
API Endpoints for SQL Rewrite Correctness & Result Equivalence Validation.
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.equivalence import (
    CompareResultsRequest,
    CompareResultsResponse,
)
from app.services.equivalence_service import compare_query_results

router = APIRouter(prefix="/validation", tags=["Validation"])


@router.post(
    "/compare-results",
    response_model=CompareResultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate SQL Rewrite Result Equivalence",
    description=(
        "Safely compares the executed results of an original SELECT query with a proposed "
        "rewritten SELECT query inside a read-only, repeatable-read transaction snapshot. "
        "Enforces strict timeouts, multiset/deterministic ordering, and row limits."
    ),
)
def compare_sql_results(payload: CompareResultsRequest) -> CompareResultsResponse:
    """
    Validates result equivalence between original and candidate SQL queries.
    Requires explicit user confirmation.
    """
    # 1. Require explicit user confirmation
    if not payload.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Result comparison requires explicit user confirmation before queries can be executed.",
        )

    # 2. Reject empty SQL inputs
    if not payload.original_sql or not payload.original_sql.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Original SQL query cannot be empty or whitespace.",
        )
    if not payload.candidate_sql or not payload.candidate_sql.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate SQL query cannot be empty or whitespace.",
        )

    # 3. Execute comparison service
    result = compare_query_results(
        original_sql=payload.original_sql,
        candidate_sql=payload.candidate_sql,
        confirmed=payload.confirmed,
        row_limit=payload.row_limit,
    )

    return result
