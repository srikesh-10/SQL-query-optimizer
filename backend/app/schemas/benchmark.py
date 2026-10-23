from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class BenchmarkRunRequest(BaseModel):
    """
    Request payload to execute a safe query benchmark.
    """
    sql: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Single read-only SELECT SQL query to safely benchmark.",
        examples=["SELECT * FROM users WHERE first_name = 'Emily';"],
    )
    repetitions: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Number of benchmark repetitions to execute (1-5).",
        examples=[3],
    )


class BenchmarkRunResult(BaseModel):
    """
    Performance metrics recorded for an individual execution repetition.
    """
    run_order: int = Field(..., description="1-indexed sequence order of the benchmark repetition.")
    status: str = Field(..., description="Status of the individual run: 'success', 'failed', or 'timeout'.")
    execution_time_ms: Optional[float] = Field(
        None, description="Actual query execution time measured by EXPLAIN ANALYZE in milliseconds."
    )
    planning_time_ms: Optional[float] = Field(
        None, description="Planning time reported by PostgreSQL in milliseconds."
    )
    total_cost: Optional[float] = Field(
        None, description="Optimizer estimated total cost units (planner estimate, NOT milliseconds)."
    )
    plan_rows: Optional[float] = Field(
        None, description="Planner estimated row count."
    )
    actual_rows: Optional[float] = Field(
        None, description="Actual row count produced during execution."
    )
    error_message: Optional[str] = Field(
        None, description="Sanitized error description if the run failed."
    )


class BenchmarkResponse(BaseModel):
    """
    Complete benchmark record including repetition results and statistical summaries.
    """
    id: str = Field(..., description="Unique benchmark UUID identifier.")
    sql: str = Field(..., description="Validated SQL query that was benchmarked.")
    created_at: datetime = Field(..., description="Timestamp when the benchmark was executed.")
    status: str = Field(
        ...,
        description="Overall benchmark status: 'completed', 'partial_failure', or 'failed'."
    )
    requested_repetitions: int = Field(..., description="Target number of repetitions requested.")
    successful_runs: int = Field(..., description="Number of successful execution runs.")
    failed_runs: int = Field(..., description="Number of failed or timed-out execution runs.")
    median_execution_time_ms: Optional[float] = Field(
        None, description="Median measured execution time across successful runs in milliseconds."
    )
    median_planning_time_ms: Optional[float] = Field(
        None, description="Median planning time across successful runs in milliseconds."
    )
    estimated_total_cost: Optional[float] = Field(
        None, description="Optimizer estimated total cost units."
    )
    error_message: Optional[str] = Field(
        None, description="Summary error message if runs encountered failures."
    )
    runs: List[BenchmarkRunResult] = Field(
        default_factory=list, description="Per-run measurements and status."
    )
    note: str = Field(
        default=(
            "Execution times are actual measurements from PostgreSQL EXPLAIN ANALYZE within "
            "a read-only transaction. Planner cost is an optimizer estimate, NOT milliseconds. "
            "Measurements vary with caching and system load."
        ),
        description="Methodological disclaimer regarding planner estimates and system caching."
    )

    model_config = ConfigDict(from_attributes=True)


class BenchmarkSummary(BaseModel):
    """
    Summary view of a benchmark record for historical list views.
    """
    id: str = Field(..., description="Unique benchmark UUID identifier.")
    sql: str = Field(..., description="SQL query string.")
    created_at: datetime = Field(..., description="Execution timestamp.")
    status: str = Field(..., description="Execution status.")
    requested_repetitions: int = Field(..., description="Number of repetitions.")
    successful_runs: int = Field(..., description="Successful run count.")
    failed_runs: int = Field(..., description="Failed run count.")
    median_execution_time_ms: Optional[float] = Field(
        None, description="Median execution time in milliseconds."
    )
    estimated_total_cost: Optional[float] = Field(
        None, description="Estimated total cost units."
    )

    model_config = ConfigDict(from_attributes=True)


class BenchmarkListResponse(BaseModel):
    """
    Paginated list of historical benchmark runs.
    """
    items: List[BenchmarkSummary] = Field(default_factory=list)
    total: int = Field(..., description="Total number of benchmark records stored.")
    limit: int = Field(..., description="Requested page limit.")
    offset: int = Field(..., description="Requested page offset.")
