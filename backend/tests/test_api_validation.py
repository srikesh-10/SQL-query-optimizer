"""
API Endpoint tests for POST /api/v1/validation/compare-results.
Covers validation request schemas, confirmation checks, rejection handling,
live PostgreSQL end-to-end equivalence checks, and endpoint isolation.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_compare_results_rejects_missing_confirmation():
    """Verify that omitting confirmation results in HTTP 400 Bad Request."""
    payload = {
        "original_sql": "SELECT id FROM users;",
        "candidate_sql": "SELECT id FROM users;",
        "confirmed": False,
    }
    response = client.post("/api/v1/validation/compare-results", json=payload)
    assert response.status_code == 400
    assert "confirmation" in response.json()["detail"].lower()


def test_compare_results_rejects_empty_sql():
    """Verify that empty SQL inputs result in HTTP 400 Bad Request."""
    payload = {
        "original_sql": "   ",
        "candidate_sql": "SELECT id FROM users;",
        "confirmed": True,
    }
    response = client.post("/api/v1/validation/compare-results", json=payload)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_compare_results_rejects_dangerous_function():
    """Verify that dangerous functions return rejected status."""
    payload = {
        "original_sql": "SELECT * FROM users;",
        "candidate_sql": "SELECT pg_sleep(1);",
        "confirmed": True,
    }
    response = client.post("/api/v1/validation/compare-results", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["matched"] is False
    assert "pg_sleep" in data["mismatch_reason"]


def test_compare_results_rejects_ddl_and_dml():
    """Verify that write statements return rejected status."""
    payload = {
        "original_sql": "DELETE FROM users WHERE id = 1;",
        "candidate_sql": "SELECT id FROM users;",
        "confirmed": True,
    }
    response = client.post("/api/v1/validation/compare-results", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert "validation" in data["mismatch_reason"].lower()


def test_compare_results_live_postgres_identical():
    """Live DB test: Identical queries evaluate to Equivalent with matched=True."""
    payload = {
        "original_sql": "SELECT id, email, first_name FROM users WHERE id = 1;",
        "candidate_sql": "SELECT id, email, first_name FROM users WHERE id = 1;",
        "confirmed": True,
    }
    response = client.post("/api/v1/validation/compare-results", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "equivalent"
    assert data["matched"] is True
    assert data["original_row_count"] == 1
    assert data["candidate_row_count"] == 1
    assert data["is_complete_comparison"] is True
    assert data["column_compatibility"]["counts_match"] is True


def test_compare_results_live_postgres_different():
    """Live DB test: Queries returning different rows evaluate to Different."""
    payload = {
        "original_sql": "SELECT id, email FROM users WHERE id = 1;",
        "candidate_sql": "SELECT id, email FROM users WHERE id = 2;",
        "confirmed": True,
    }
    response = client.post("/api/v1/validation/compare-results", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "different"
    assert data["matched"] is False
    assert "mismatch" in data["mismatch_reason"].lower()


def test_compare_results_live_postgres_select_star_expansion_equivalent():
    """Live DB test: SELECT * vs explicit column list on users table evaluates to Equivalent."""
    payload = {
        "original_sql": "SELECT * FROM users WHERE first_name = 'Emily';",
        "candidate_sql": "SELECT id, email, first_name, last_name, created_at, updated_at FROM users WHERE first_name = 'Emily';",
        "confirmed": True,
    }
    response = client.post("/api/v1/validation/compare-results", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "equivalent"
    assert data["matched"] is True
    assert data["original_row_count"] > 0
    assert data["original_row_count"] == data["candidate_row_count"]
    assert data["is_complete_comparison"] is True


def test_compare_results_live_postgres_truncated_returns_inconclusive():
    """Live DB test: Bounded row limit truncation returns Inconclusive."""
    payload = {
        "original_sql": "SELECT * FROM users;",
        "candidate_sql": "SELECT id, email, first_name, last_name, created_at, updated_at FROM users;",
        "confirmed": True,
        "row_limit": 5,  # Only 5 rows compared, but users has 10,000 rows
    }
    response = client.post("/api/v1/validation/compare-results", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inconclusive"
    assert data["matched"] is None
    assert data["is_complete_comparison"] is False
    assert "maximum row limit" in data["mismatch_reason"].lower()


def test_analyze_endpoint_remains_unaffected_and_does_not_validate():
    """Verify that calling /api/v1/analyze does NOT execute result equivalence comparison."""
    with patch("app.api.validation.compare_query_results") as mock_validate:
        res = client.post(
            "/api/v1/analyze",
            json={"sql": "SELECT 1;"},
        )
        assert res.status_code == 200
        assert mock_validate.call_count == 0
