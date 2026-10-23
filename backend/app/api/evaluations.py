"""
API Endpoints for Optimizer Evaluation & Performance Scoring.
Provides POST /api/v1/evaluations, GET /api/v1/evaluations, and GET /api/v1/evaluations/{id}.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.evaluation import (
    EvaluationListResponse,
    EvaluationRequest,
    EvaluationResponse,
)
from app.services.evaluation_service import (
    get_evaluation_by_id,
    list_evaluations,
    run_evaluation,
)

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.post(
    "",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate SQL Rewrite",
    description=(
        "Executes a unified evaluation of an original SQL query and candidate rewrite across "
        "three dimensions: correctness validation gate, empirical performance benchmarking "
        "with alternating probe orders, and a deterministic recommendation engine."
    ),
)
def create_evaluation(
    payload: EvaluationRequest,
    db: Session = Depends(get_db),
) -> EvaluationResponse:
    """
    Executes an optimizer evaluation.
    Requires explicit user confirmation before queries are run.
    """
    if not payload.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evaluation requires explicit user confirmation before queries can be executed.",
        )

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

    try:
        return run_evaluation(
            db=db,
            original_sql=payload.original_sql,
            candidate_sql=payload.candidate_sql,
            confirmed=payload.confirmed,
            repetitions=payload.repetitions,
            row_limit=payload.row_limit,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evaluation encountered an unexpected internal error.",
        )


@router.get(
    "",
    response_model=EvaluationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Evaluation History",
    description="Retrieves a paginated list of historical rewrite evaluations sorted by timestamp descending.",
)
def get_evaluations(
    limit: int = Query(default=10, ge=1, le=50, description="Max evaluations to retrieve"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> EvaluationListResponse:
    """Retrieves paginated historical evaluations."""
    return list_evaluations(db=db, limit=limit, offset=offset)


@router.get(
    "/{evaluation_id}",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Evaluation By ID",
    description="Retrieves a specific evaluation record with its complete multi-run telemetry and recommendation.",
)
def get_evaluation(
    evaluation_id: str,
    db: Session = Depends(get_db),
) -> EvaluationResponse:
    """Retrieves a single evaluation by ID."""
    record = get_evaluation_by_id(db=db, evaluation_id=evaluation_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation record with ID '{evaluation_id}' was not found.",
        )
    return record
