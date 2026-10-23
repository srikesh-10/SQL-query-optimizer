import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.schemas.benchmark import BenchmarkRunResult, BenchmarkResponse

client = TestClient(app)


def test_create_benchmark_rejects_empty_sql():
    res = client.post("/api/v1/benchmarks", json={"sql": "", "repetitions": 1})
    assert res.status_code == 422  # Pydantic min_length validation


def test_create_benchmark_rejects_disallowed_function():
    res = client.post(
        "/api/v1/benchmarks",
        json={"sql": "SELECT pg_sleep(3);", "repetitions": 1},
    )
    assert res.status_code == 400
    assert "Prohibited function" in res.json()["detail"]


def test_create_benchmark_rejects_system_catalog():
    res = client.post(
        "/api/v1/benchmarks",
        json={"sql": "SELECT * FROM pg_class;", "repetitions": 1},
    )
    assert res.status_code == 400
    assert "System catalog access prohibited" in res.json()["detail"]


def test_create_benchmark_rejects_data_modification():
    res = client.post(
        "/api/v1/benchmarks",
        json={"sql": "DELETE FROM users WHERE id = 1;", "repetitions": 1},
    )
    assert res.status_code == 400
    assert "Data-modifying" in res.json()["detail"] or "Unsupported statement" in res.json()["detail"]


def test_create_benchmark_success_mocked():
    mock_response = BenchmarkResponse(
        id="test-benchmark-uuid-1234",
        sql="SELECT * FROM users WHERE first_name = 'Emily'",
        created_at="2026-10-21T11:00:00Z",
        status="completed",
        requested_repetitions=2,
        successful_runs=2,
        failed_runs=0,
        median_execution_time_ms=1.45,
        median_planning_time_ms=0.12,
        estimated_total_cost=236.0,
        error_message=None,
        runs=[
            BenchmarkRunResult(
                run_order=1,
                status="success",
                execution_time_ms=1.40,
                planning_time_ms=0.11,
                total_cost=236.0,
                plan_rows=248,
                actual_rows=248,
            ),
            BenchmarkRunResult(
                run_order=2,
                status="success",
                execution_time_ms=1.50,
                planning_time_ms=0.13,
                total_cost=236.0,
                plan_rows=248,
                actual_rows=248,
            ),
        ],
    )

    with patch("app.api.benchmarks.run_benchmark", return_value=mock_response):
        res = client.post(
            "/api/v1/benchmarks",
            json={
                "sql": "SELECT * FROM users WHERE first_name = 'Emily';",
                "repetitions": 2,
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["id"] == "test-benchmark-uuid-1234"
        assert data["status"] == "completed"
        assert data["median_execution_time_ms"] == 1.45
        assert len(data["runs"]) == 2
        assert "EXPLAIN ANALYZE" in data["note"]


def test_get_benchmark_by_id_not_found():
    mock_db = MagicMock()
    with patch("app.api.benchmarks.get_benchmark_by_id", return_value=None):
        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            res = client.get("/api/v1/benchmarks/non-existent-uuid")
            assert res.status_code == 404
            assert "not found" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_db, None)


def test_get_benchmarks_pagination():
    mock_db = MagicMock()
    from app.schemas.benchmark import BenchmarkListResponse, BenchmarkSummary

    mock_list = BenchmarkListResponse(
        items=[
            BenchmarkSummary(
                id="bench-1",
                sql="SELECT * FROM products",
                created_at="2026-10-21T11:00:00Z",
                status="completed",
                requested_repetitions=1,
                successful_runs=1,
                failed_runs=0,
                median_execution_time_ms=0.85,
                estimated_total_cost=45.0,
            )
        ],
        total=1,
        limit=10,
        offset=0,
    )

    with patch("app.api.benchmarks.list_benchmarks", return_value=mock_list):
        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            res = client.get("/api/v1/benchmarks?limit=10&offset=0")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["id"] == "bench-1"
        finally:
            app.dependency_overrides.pop(get_db, None)


def test_analyze_endpoint_remains_unaffected_and_does_not_benchmark():
    # Verify existing /api/v1/analyze is untouched and does not call run_benchmark
    with patch("app.api.benchmarks.run_benchmark") as mock_benchmark:
        res = client.post(
            "/api/v1/analyze",
            json={"sql": "SELECT 1;"},
        )
        # /analyze does NOT call run_benchmark
        assert mock_benchmark.call_count == 0


def test_benchmark_live_postgres_end_to_end():
    """Live benchmark execution against running PostgreSQL sample database."""
    payload = {
        "sql": "SELECT id, email, first_name FROM users WHERE id = 1;",
        "repetitions": 2,
    }
    response = client.post("/api/v1/benchmarks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "completed"
    assert data["requested_repetitions"] == 2
    assert data["successful_runs"] == 2
    assert data["failed_runs"] == 0
    assert data["median_execution_time_ms"] is not None
    assert data["median_execution_time_ms"] > 0.0
    assert data["median_planning_time_ms"] is not None
    assert data["estimated_total_cost"] is not None
    assert len(data["runs"]) == 2
    for run in data["runs"]:
        assert run["status"] == "success"
        assert run["execution_time_ms"] > 0.0

    # Test retrieval via GET /benchmarks/{id}
    bench_id = data["id"]
    get_res = client.get(f"/api/v1/benchmarks/{bench_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["id"] == bench_id
    assert retrieved["median_execution_time_ms"] == data["median_execution_time_ms"]
    assert len(retrieved["runs"]) == 2

    # Test listing via GET /benchmarks
    list_res = client.get("/api/v1/benchmarks?limit=5")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(b["id"] == bench_id for b in list_data["items"])
