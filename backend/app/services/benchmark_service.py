"""
Safe PostgreSQL Query Benchmarking Service.
Executes EXPLAIN (ANALYZE, FORMAT JSON, COSTS TRUE, TIMING TRUE, SUMMARY TRUE)
within a transaction-scoped, read-only session with strict timeouts.
Persists benchmark history and calculates median execution metrics across repetitions.
"""

import statistics
import uuid
from typing import Dict, Any, List, Optional, Tuple

import sqlglot
from sqlglot import exp
from sqlalchemy import text, select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError, OperationalError

from app.db.session import engine
from app.models.benchmark import Benchmark, BenchmarkRun
from app.schemas.benchmark import (
    BenchmarkRunResult,
    BenchmarkResponse,
    BenchmarkSummary,
    BenchmarkListResponse,
)
from app.services.sql_validator import validate_read_only_sql, SQLValidationError


# Prohibited functions that induce sleep, termination, or out-of-band operations
FORBIDDEN_BENCHMARK_FUNCTIONS = {
    "pg_sleep",
    "pg_sleep_for",
    "pg_sleep_until",
    "pg_terminate_backend",
    "pg_cancel_backend",
    "pg_reload_conf",
    "pg_rotate_logfile",
    "dblink",
    "dblink_exec",
    "dblink_connect",
    "pg_read_file",
    "pg_read_binary_file",
    "pg_write_file",
    "lo_export",
    "lo_import",
    "query_to_xml",
}

# Tables permitted for benchmarking (sample e-commerce schema)
ALLOWED_BENCHMARK_TABLES = {"users", "products", "orders", "order_items"}


class BenchmarkSecurityError(Exception):
    """Exception raised when a query contains unsafe functions or system access."""
    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail


def validate_benchmark_sql(raw_sql: str) -> Tuple[str, exp.Expression]:
    """
    Validates that the SQL query is a read-only SELECT statement and does not
    contain dangerous functions or attempt to access system catalogs.
    """
    # 1. Base read-only validation (rejects DDL, DML, multiple statements, Into, CTE writes)
    normalized_sql, parsed_ast = validate_read_only_sql(raw_sql)

    # 2. Inspect AST for forbidden functions
    for func_node in parsed_ast.find_all((exp.Anonymous, exp.Func)):
        func_name = func_node.name.lower() if func_node.name else ""
        if func_name in FORBIDDEN_BENCHMARK_FUNCTIONS:
            raise BenchmarkSecurityError(
                f"Prohibited function detected: '{func_name}'.",
                "Benchmarking queries cannot call sleep, system termination, or administrative functions."
            )

    # 3. Inspect AST for system catalog access (pg_*, information_schema)
    for table_node in parsed_ast.find_all(exp.Table):
        t_name = table_node.name.lower() if table_node.name else ""
        t_db = table_node.db.lower() if table_node.db else ""
        if t_name.startswith("pg_") or t_db.startswith("pg_") or t_db == "information_schema":
            raise BenchmarkSecurityError(
                f"System catalog access prohibited: '{table_node.sql()}'.",
                "Benchmarking is restricted to application sample tables (users, products, orders, order_items)."
            )

    return normalized_sql, parsed_ast


def execute_single_run(
    clean_sql: str,
    run_order: int,
    statement_timeout_ms: int = 3000,
    lock_timeout_ms: int = 1000,
) -> BenchmarkRunResult:
    """
    Executes a single benchmark repetition using EXPLAIN ANALYZE in a read-only transaction.
    """
    explain_cmd = (
        f"EXPLAIN (ANALYZE, FORMAT JSON, COSTS TRUE, TIMING TRUE, SUMMARY TRUE) {clean_sql}"
    )

    try:
        with engine.connect() as conn:
            # Enforce read-only transaction and strict timeouts
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text(f"SET LOCAL statement_timeout = {int(statement_timeout_ms)}"))
            conn.execute(text(f"SET LOCAL lock_timeout = {int(lock_timeout_ms)}"))

            result = conn.execute(text(explain_cmd))
            plan_rows = result.fetchall()
            conn.rollback()

            if not plan_rows:
                return BenchmarkRunResult(
                    run_order=run_order,
                    status="failed",
                    error_message="PostgreSQL returned empty execution plan.",
                )

            raw_plan_data = plan_rows[0][0]
            if isinstance(raw_plan_data, list) and len(raw_plan_data) > 0:
                plan_obj = raw_plan_data[0]
            elif isinstance(raw_plan_data, dict):
                plan_obj = raw_plan_data
            else:
                return BenchmarkRunResult(
                    run_order=run_order,
                    status="failed",
                    error_message=f"Unexpected plan data format: {type(raw_plan_data).__name__}",
                )

            exec_time = plan_obj.get("Execution Time")
            plan_time = plan_obj.get("Planning Time")
            root_node = plan_obj.get("Plan", {})
            total_cost = root_node.get("Total Cost")
            plan_rows_est = root_node.get("Plan Rows")
            actual_rows_est = root_node.get("Actual Rows")

            return BenchmarkRunResult(
                run_order=run_order,
                status="success",
                execution_time_ms=round(float(exec_time), 3) if exec_time is not None else None,
                planning_time_ms=round(float(plan_time), 3) if plan_time is not None else None,
                total_cost=float(total_cost) if total_cost is not None else None,
                plan_rows=float(plan_rows_est) if plan_rows_est is not None else None,
                actual_rows=float(actual_rows_est) if actual_rows_est is not None else None,
                error_message=None,
            )

    except OperationalError as e:
        err_str = str(e).lower()
        if "timeout" in err_str or "canceling statement due to statement timeout" in err_str:
            return BenchmarkRunResult(
                run_order=run_order,
                status="timeout",
                error_message=f"Execution timed out after {statement_timeout_ms}ms.",
            )
        return BenchmarkRunResult(
            run_order=run_order,
            status="failed",
            error_message="Database operational error or timeout.",
        )
    except DBAPIError as e:
        orig = getattr(e, "orig", str(e))
        clean_err = str(orig).split("\n")[0]
        return BenchmarkRunResult(
            run_order=run_order,
            status="failed",
            error_message=f"PostgreSQL error: {clean_err}",
        )
    except Exception as e:
        return BenchmarkRunResult(
            run_order=run_order,
            status="failed",
            error_message=f"Unexpected execution error: {str(e)}",
        )


def run_benchmark(
    sql: str,
    repetitions: int = 1,
    db: Optional[Session] = None,
    statement_timeout_ms: int = 3000,
) -> BenchmarkResponse:
    """
    Orchestrates the benchmark execution over the requested number of repetitions (1-5),
    calculates statistical aggregates, persists the record, and returns the response.
    """
    clean_sql = sql.strip().rstrip(";")
    benchmark_id = str(uuid.uuid4())
    run_results: List[BenchmarkRunResult] = []

    # Bounded repetitions: clamp between 1 and 5
    num_runs = max(1, min(repetitions, 5))

    for run_num in range(1, num_runs + 1):
        run_res = execute_single_run(
            clean_sql=clean_sql,
            run_order=run_num,
            statement_timeout_ms=statement_timeout_ms,
        )
        run_results.append(run_res)

    successful_runs = [r for r in run_results if r.status == "success" and r.execution_time_ms is not None]
    failed_runs = [r for r in run_results if r.status != "success"]

    median_exec: Optional[float] = None
    median_plan: Optional[float] = None
    estimated_cost: Optional[float] = None

    if successful_runs:
        exec_times = [r.execution_time_ms for r in successful_runs if r.execution_time_ms is not None]
        plan_times = [r.planning_time_ms for r in successful_runs if r.planning_time_ms is not None]
        if exec_times:
            median_exec = round(statistics.median(exec_times), 3)
        if plan_times:
            median_plan = round(statistics.median(plan_times), 3)
        estimated_cost = successful_runs[0].total_cost

    # Determine overall status
    if len(successful_runs) == num_runs:
        overall_status = "completed"
        error_msg = None
    elif len(successful_runs) > 0:
        overall_status = "partial_failure"
        error_msg = f"{len(failed_runs)} of {num_runs} repetitions failed or timed out."
    else:
        overall_status = "failed"
        error_msg = failed_runs[0].error_message if failed_runs else "All benchmark repetitions failed."

    # Persist in PostgreSQL database if session provided
    benchmark_record = None
    if db is not None:
        try:
            benchmark_record = Benchmark(
                id=benchmark_id,
                sql=clean_sql,
                status=overall_status,
                requested_repetitions=num_runs,
                successful_runs=len(successful_runs),
                failed_runs=len(failed_runs),
                median_execution_time_ms=median_exec,
                median_planning_time_ms=median_plan,
                estimated_total_cost=estimated_cost,
                error_message=error_msg,
            )
            db.add(benchmark_record)
            db.flush()

            for r in run_results:
                run_entry = BenchmarkRun(
                    benchmark_id=benchmark_id,
                    run_order=r.run_order,
                    status=r.status,
                    execution_time_ms=r.execution_time_ms,
                    planning_time_ms=r.planning_time_ms,
                    total_cost=r.total_cost,
                    plan_rows=r.plan_rows,
                    actual_rows=r.actual_rows,
                    error_message=r.error_message,
                )
                db.add(run_entry)
            db.commit()
            db.refresh(benchmark_record)
        except Exception:
            db.rollback()
            # If persistence fails (e.g. database offline or error), continue without crashing

    from datetime import datetime, timezone
    created_at = (
        benchmark_record.created_at
        if benchmark_record and hasattr(benchmark_record, "created_at") and benchmark_record.created_at
        else datetime.now(timezone.utc)
    )

    return BenchmarkResponse(
        id=benchmark_id,
        sql=clean_sql,
        created_at=created_at,
        status=overall_status,
        requested_repetitions=num_runs,
        successful_runs=len(successful_runs),
        failed_runs=len(failed_runs),
        median_execution_time_ms=median_exec,
        median_planning_time_ms=median_plan,
        estimated_total_cost=estimated_cost,
        error_message=error_msg,
        runs=run_results,
    )


def list_benchmarks(
    db: Session,
    limit: int = 20,
    offset: int = 0,
) -> BenchmarkListResponse:
    """
    Retrieves a paginated list of historical benchmark runs.
    """
    bounded_limit = max(1, min(limit, 100))
    bounded_offset = max(0, offset)

    total = db.scalar(select(func.count()).select_from(Benchmark)) or 0

    query = (
        select(Benchmark)
        .order_by(Benchmark.created_at.desc())
        .limit(bounded_limit)
        .offset(bounded_offset)
    )
    records = db.scalars(query).all()

    items = [
        BenchmarkSummary(
            id=r.id,
            sql=r.sql,
            created_at=r.created_at,
            status=r.status,
            requested_repetitions=r.requested_repetitions,
            successful_runs=r.successful_runs,
            failed_runs=r.failed_runs,
            median_execution_time_ms=r.median_execution_time_ms,
            estimated_total_cost=r.estimated_total_cost,
        )
        for r in records
    ]

    return BenchmarkListResponse(
        items=items,
        total=total,
        limit=bounded_limit,
        offset=bounded_offset,
    )


def get_benchmark_by_id(db: Session, benchmark_id: str) -> Optional[BenchmarkResponse]:
    """
    Retrieves a single benchmark run by UUID with its detailed run measurements.
    """
    query = select(Benchmark).where(Benchmark.id == benchmark_id)
    benchmark = db.scalar(query)
    if not benchmark:
        return None

    run_results = [
        BenchmarkRunResult(
            run_order=r.run_order,
            status=r.status,
            execution_time_ms=r.execution_time_ms,
            planning_time_ms=r.planning_time_ms,
            total_cost=r.total_cost,
            plan_rows=r.plan_rows,
            actual_rows=r.actual_rows,
            error_message=r.error_message,
        )
        for r in benchmark.runs
    ]

    return BenchmarkResponse(
        id=benchmark.id,
        sql=benchmark.sql,
        created_at=benchmark.created_at,
        status=benchmark.status,
        requested_repetitions=benchmark.requested_repetitions,
        successful_runs=benchmark.successful_runs,
        failed_runs=benchmark.failed_runs,
        median_execution_time_ms=benchmark.median_execution_time_ms,
        median_planning_time_ms=benchmark.median_planning_time_ms,
        estimated_total_cost=benchmark.estimated_total_cost,
        error_message=benchmark.error_message,
        runs=run_results,
    )
