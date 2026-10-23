import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import OperationalError, DBAPIError

from app.services.benchmark_service import (
    validate_benchmark_sql,
    execute_single_run,
    run_benchmark,
    BenchmarkSecurityError,
)
from app.services.sql_validator import SQLValidationError


def test_validate_benchmark_sql_valid_query():
    sql = "SELECT id, email FROM users WHERE id = 10;"
    normalized, ast = validate_benchmark_sql(sql)
    assert "users" in normalized.lower()
    assert ast is not None


def test_validate_benchmark_sql_rejects_forbidden_functions():
    # pg_sleep must be rejected
    with pytest.raises(BenchmarkSecurityError) as exc_info:
        validate_benchmark_sql("SELECT pg_sleep(2);")
    assert "Prohibited function" in exc_info.value.message
    assert "pg_sleep" in exc_info.value.message

    # pg_terminate_backend must be rejected
    with pytest.raises(BenchmarkSecurityError) as exc_info:
        validate_benchmark_sql("SELECT pg_terminate_backend(123);")
    assert "Prohibited function" in exc_info.value.message


def test_validate_benchmark_sql_rejects_system_catalog():
    # pg_shadow / pg_tables must be rejected
    with pytest.raises(BenchmarkSecurityError) as exc_info:
        validate_benchmark_sql("SELECT * FROM pg_tables;")
    assert "System catalog access prohibited" in exc_info.value.message

    with pytest.raises(BenchmarkSecurityError) as exc_info:
        validate_benchmark_sql("SELECT * FROM information_schema.tables;")
    assert "System catalog access prohibited" in exc_info.value.message


def test_validate_benchmark_sql_rejects_writes():
    with pytest.raises(SQLValidationError):
        validate_benchmark_sql("UPDATE users SET first_name = 'hacked' WHERE id = 1;")

    with pytest.raises(SQLValidationError):
        validate_benchmark_sql("DROP TABLE users;")

    with pytest.raises(SQLValidationError):
        validate_benchmark_sql("SELECT * FROM users; DROP TABLE orders;")


def test_execute_single_run_success():
    mock_plan = [
        [
            {
                "Plan": {
                    "Node Type": "Seq Scan",
                    "Total Cost": 150.25,
                    "Plan Rows": 100,
                    "Actual Rows": 95,
                },
                "Planning Time": 0.254,
                "Execution Time": 2.150,
            }
        ]
    ]

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = mock_plan

    with patch("app.services.benchmark_service.engine.connect") as mock_connect:
        mock_connect.return_value.__enter__.return_value = mock_conn

        res = execute_single_run("SELECT * FROM users", run_order=1)
        assert res.status == "success"
        assert res.execution_time_ms == 2.15
        assert res.planning_time_ms == 0.254
        assert res.total_cost == 150.25
        assert res.actual_rows == 95
        assert res.error_message is None


def test_execute_single_run_timeout():
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = OperationalError(
        "canceling statement due to statement timeout", params=None, orig=Exception("timeout")
    )

    with patch("app.services.benchmark_service.engine.connect") as mock_connect:
        mock_connect.return_value.__enter__.return_value = mock_conn

        res = execute_single_run("SELECT * FROM users", run_order=1, statement_timeout_ms=3000)
        assert res.status == "timeout"
        assert "timed out" in res.error_message


def test_run_benchmark_median_and_repetitions():
    # Test 3 repetitions with different timings
    timings = [3.5, 1.2, 2.4]

    def mock_single_run(clean_sql, run_order, statement_timeout_ms=3000):
        t = timings[run_order - 1]
        from app.schemas.benchmark import BenchmarkRunResult
        return BenchmarkRunResult(
            run_order=run_order,
            status="success",
            execution_time_ms=t,
            planning_time_ms=0.1,
            total_cost=200.0,
            plan_rows=50,
            actual_rows=50,
        )

    with patch("app.services.benchmark_service.execute_single_run", side_effect=mock_single_run):
        resp = run_benchmark("SELECT * FROM users", repetitions=3, db=None)

        assert resp.status == "completed"
        assert resp.requested_repetitions == 3
        assert resp.successful_runs == 3
        assert resp.failed_runs == 0
        # Median of [3.5, 1.2, 2.4] sorted is [1.2, 2.4, 3.5] -> 2.4
        assert resp.median_execution_time_ms == 2.4
        assert len(resp.runs) == 3


def test_run_benchmark_partial_failure():
    # Run 1 succeeds (1.5ms), Run 2 times out
    def mock_single_run(clean_sql, run_order, statement_timeout_ms=3000):
        from app.schemas.benchmark import BenchmarkRunResult
        if run_order == 1:
            return BenchmarkRunResult(
                run_order=1,
                status="success",
                execution_time_ms=1.5,
                planning_time_ms=0.1,
                total_cost=100.0,
            )
        else:
            return BenchmarkRunResult(
                run_order=2,
                status="timeout",
                error_message="Execution timed out",
            )

    with patch("app.services.benchmark_service.execute_single_run", side_effect=mock_single_run):
        resp = run_benchmark("SELECT * FROM users", repetitions=2, db=None)

        assert resp.status == "partial_failure"
        assert resp.successful_runs == 1
        assert resp.failed_runs == 1
        assert resp.median_execution_time_ms == 1.5
        assert "1 of 2 repetitions failed" in resp.error_message
