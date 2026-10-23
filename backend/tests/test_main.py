from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify that root endpoint responds with 200 and expected payload."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs_url" in data
    assert data["docs_url"] == "/docs"


def test_health_check_endpoint():
    """Verify that health check endpoint returns status healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "development"
    assert "version" in data


def test_readiness_check_endpoint_success():
    """Verify that readiness check returns 200 and healthy status when database is reachable."""
    with patch("app.main.check_db_readiness", return_value=True):
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["detail"] is None


def test_readiness_check_endpoint_failure():
    """Verify that readiness check returns 503 and unhealthy status when database check fails."""
    with patch("app.main.check_db_readiness", return_value=False):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "detail" in data


def test_readiness_check_real_database():
    """Verify that readiness check against running PostgreSQL instance succeeds."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
