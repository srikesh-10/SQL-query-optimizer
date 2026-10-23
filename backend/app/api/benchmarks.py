"""
API endpoints for safe query benchmarking and historical performance comparisons.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analysis import ErrorResponse
from app.schemas.benchmark import (
    BenchmarkRunRequest,
    BenchmarkResponse,
    BenchmarkListResponse,
)
from app.services.benchmark_service import (
    validate_benchmark_sql,
    run_benchmark,
    list_benchmarks,
    get_benchmark_by_id,
    BenchmarkSecurityError,
)
from app.services.sql_validator import SQLValidationError

router = APIRouter(prefix="/benchmarks", tags=["Query Benchmarking"])


@router.post(
    "",
    response_model=BenchmarkResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid, dangerous, or unsupported SQL query."},
        503: {"model": ErrorResponse, "description": "Database unavailable or operational failure."},
    },
    summary="Execute an explicit, opt-in query benchmark",
)
def create_benchmark(
    payload: BenchmarkRunRequest,
    db: Session = Depends(get_db),
) -> BenchmarkResponse:
    """
    Safely executes an explicit benchmark of a read-only SQL query against PostgreSQL.
    Enforces single-statement read-only SELECT validation, forbids dangerous functions and
    system catalog access, sets a 3-second statement timeout, executes EXPLAIN ANALYZE
    over 1-5 repetitions within a read-only transaction, and records historical results.
    """
    # 1. Strict SQL and safety validation
    try:
        normalized_sql, _ = validate_benchmark_sql(payload.sql)
    except (SQLValidationError, BenchmarkSecurityError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{e.message} {e.detail}".strip(),
        )

    # 2. Run benchmark across requested repetitions
    try:
        result = run_benchmark(
            sql=normalized_sql,
            repetitions=payload.repetitions,
            db=db,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Benchmark execution encountered an unexpected internal error.",
        )

    return result


@router.get(
    "",
    response_model=BenchmarkListResponse,
    summary="Retrieve paginated benchmark execution history",
)
def get_benchmarks(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of records to return."),
    offset: int = Query(default=0, ge=0, description="Offset for pagination."),
    db: Session = Depends(get_db),
) -> BenchmarkListResponse:
    """
    Returns recent benchmark execution history ordered by timestamp descending.
    """
    try:
        return list_benchmarks(db=db, limit=limit, offset=offset)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve benchmark history from database.",
        )


@router.get(
    "/{benchmark_id}",
    response_model=BenchmarkResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Benchmark record not found."},
        503: {"model": ErrorResponse, "description": "Database unavailable."},
    },
    summary="Retrieve details and per-run measurements for a specific benchmark",
)
def get_benchmark(
    benchmark_id: str,
    db: Session = Depends(get_db),
) -> BenchmarkResponse:
    """
    Retrieves full metrics and individual run measurements for a benchmark run by ID.
    """
    try:
        record = get_benchmark_by_id(db=db, benchmark_id=benchmark_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error while querying benchmark: {str(e)}",
        )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark with ID '{benchmark_id}' not found.",
        )

    return record
