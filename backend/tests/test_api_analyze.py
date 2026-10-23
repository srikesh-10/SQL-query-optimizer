"""
Integration and API endpoint tests for POST /api/v1/analyze including Phase 3 capabilities.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.explain_service import ExplainServiceError

client = TestClient(app)


def test_analyze_valid_select_live_db():
    """Verify live EXPLAIN analysis against running PostgreSQL database."""
    payload = {
        "sql": "SELECT id, email FROM users WHERE email = 'karen.harris.7505@example.com';"
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "SELECT" in data["validated_sql"]
    assert "plan_summary" in data
    assert data["plan_summary"]["total_cost"] > 0
    assert "scan_nodes" in data
    assert "findings" in data
    assert "index_recommendations" in data
    assert "rewrite_candidates" in data
    assert data["metadata"]["is_runtime_benchmark"] is False


def test_analyze_with_index_recommendation_and_rewrite():
    """Verify an unindexed filter triggers an index recommendation and SELECT * triggers rewrite."""
    payload = {
        "sql": "SELECT * FROM users WHERE first_name = 'Emily';"
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Index advisor should recommend an index on first_name
    recs = data["index_recommendations"]
    assert any(r["table_name"] == "users" and "first_name" in r["columns"] for r in recs)

    # Rewrite engine should expand SELECT *
    rewrites = data["rewrite_candidates"]
    star_rewrite = next((r for r in rewrites if r["rule_id"] == "REWRITE_EXPAND_SELECT_STAR"), None)
    assert star_rewrite is not None
    assert "email" in star_rewrite["rewritten_sql"]

    # Plan comparison should be executed for the verified safe rewrite
    assert data["plan_comparison"] is not None
    assert data["plan_comparison"]["original_total_cost"] > 0
    assert data["plan_comparison"]["candidate_total_cost"] > 0


def test_analyze_complex_join_live_db():
    """Verify live EXPLAIN analysis for a multi-table JOIN query."""
    payload = {
        "sql": """
        SELECT u.email, count(o.id) as order_count
        FROM users u
        JOIN orders o ON u.id = o.user_id
        WHERE o.status = 'completed'
        GROUP BY u.email
        LIMIT 10;
        """
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["scan_nodes"]) >= 2
    assert len(data["join_nodes"]) >= 1


def test_analyze_rejects_empty_sql():
    response = client.post("/api/v1/analyze", json={"sql": ""})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_analyze_rejects_unsafe_write_statements():
    unsafe_queries = [
        "DROP TABLE users;",
        "INSERT INTO users (email, first_name, last_name) VALUES ('x@y.com', 'A', 'B');",
        "DELETE FROM orders WHERE id = 1;",
        "UPDATE products SET price = 9.99 WHERE id = 1;",
        "SELECT 1; DROP TABLE products;",
        "SELECT * INTO copy_users FROM users;",
    ]
    for sql in unsafe_queries:
        response = client.post("/api/v1/analyze", json={"sql": sql})
        assert response.status_code == 400
        assert "detail" in response.json()


def test_analyze_invalid_payload_schema():
    response = client.post("/api/v1/analyze", json={"invalid_field": "SELECT 1;"})
    assert response.status_code == 422


def test_analyze_db_operational_failure_simulation():
    with patch("app.api.analysis.get_execution_plan") as mock_explain:
        mock_explain.side_effect = ExplainServiceError(
            "Database service is unreachable",
            status_code=503,
            detail="Connection failed"
        )
        response = client.post("/api/v1/analyze", json={"sql": "SELECT 1;"})
        assert response.status_code == 503
        assert "unreachable" in response.json()["detail"]


def test_analyze_db_timeout_simulation():
    with patch("app.api.analysis.get_execution_plan") as mock_explain:
        mock_explain.side_effect = ExplainServiceError(
            "Execution plan inspection timed out.",
            status_code=504,
            detail="Timeout exceeded"
        )
        response = client.post("/api/v1/analyze", json={"sql": "SELECT 1;"})
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]
