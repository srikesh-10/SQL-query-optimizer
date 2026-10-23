"""
API tests for POST /api/v1/evaluations and GET /api/v1/evaluations endpoints.
Verifies confirmation requirements, validation failure halting, evaluation results,
and historical persistence.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import check_db_readiness
from app.schemas.equivalence import CompareResultsResponse
from app.schemas.benchmark import BenchmarkRunResult

client = TestClient(app)


def test_evaluation_rejects_missing_confirmation():
    payload = {
        "original_sql": "SELECT id FROM users;",
        "candidate_sql": "SELECT id FROM users;",
        "confirmed": False,
        "repetitions": 3,
    }
    res = client.post("/api/v1/evaluations", json=payload)
    assert res.status_code == 400
    assert "confirmation" in res.json()["detail"].lower()


def test_evaluation_rejects_empty_sql():
    payload = {
        "original_sql": "   ",
        "candidate_sql": "SELECT id FROM users;",
        "confirmed": True,
        "repetitions": 3,
    }
    res = client.post("/api/v1/evaluations", json=payload)
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_evaluation_rejects_out_of_bounds_repetitions():
    payload = {
        "original_sql": "SELECT id FROM users;",
        "candidate_sql": "SELECT id FROM users;",
        "confirmed": True,
        "repetitions": 6,
    }
    res = client.post("/api/v1/evaluations", json=payload)
    assert res.status_code == 422


def test_evaluation_stops_on_different_results_mocked():
    payload = {
        "original_sql": "SELECT id FROM users WHERE id = 1;",
        "candidate_sql": "SELECT id FROM users WHERE id = 2;",
        "confirmed": True,
        "repetitions": 3,
    }

    diff_equiv = CompareResultsResponse(
        status="different",
        matched=False,
        original_row_count=1,
        candidate_row_count=1,
        is_complete_comparison=True,
        row_limit_applied=1000,
        order_deterministic=True,
        ordering_mode="ordered",
        mismatch_reason="Row 0 differs in values: id (1 != 2)",
    )

    with patch("app.services.evaluation_service.compare_query_results", return_value=diff_equiv) as mock_compare, \
         patch("app.services.evaluation_service.execute_single_run") as mock_exec:
        
        res = client.post("/api/v1/evaluations", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["correctness_status"] == "different"
        assert data["recommendation"] == "do_not_recommend"
        assert data["performance_assessment"] == "inconclusive"
        assert len(data["original_runs"]) == 0
        assert len(data["candidate_runs"]) == 0
        mock_exec.assert_not_called()


def test_evaluation_lifecycle_and_history():
    """Verify evaluation flow, persistence, listing, and retrieval."""
    if not check_db_readiness():
        pytest.skip("PostgreSQL database is not available for integration test.")

    payload = {
        "original_sql": "SELECT id, email FROM users WHERE id = 10;",
        "candidate_sql": "SELECT id, email FROM users WHERE id = 10;",
        "confirmed": True,
        "repetitions": 2,
    }

    create_res = client.post("/api/v1/evaluations", json=payload)
    assert create_res.status_code == 201
    eval_data = create_res.json()

    assert eval_data["id"] is not None
    assert eval_data["correctness_status"] == "validated"
    assert eval_data["is_complete_comparison"] is True
    assert eval_data["successful_runs"] >= 2
    assert eval_data["original_median_execution_time_ms"] is not None
    assert eval_data["candidate_median_execution_time_ms"] is not None
    eval_id = eval_data["id"]

    # Retrieve single evaluation
    get_res = client.get(f"/api/v1/evaluations/{eval_id}")
    assert get_res.status_code == 200
    single_data = get_res.json()
    assert single_data["id"] == eval_id
    assert single_data["correctness_status"] == "validated"

    # List evaluations
    list_res = client.get("/api/v1/evaluations?limit=10&offset=0")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == eval_id for item in list_data["items"])


def test_get_evaluation_not_found():
    res = client.get("/api/v1/evaluations/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
