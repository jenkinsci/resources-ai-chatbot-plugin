"""Unit Tests for health check endpoint."""

from fastapi.testclient import TestClient
import pytest


# Create a simple fixture that doesn't require the full test_env
# pylint: disable=redefined-outer-name
@pytest.fixture(name="simple_client")
def simple_client_fixture():
    """Fixture to provide a minimal TestClient for health check tests."""
    # pylint: disable=import-outside-toplevel
    from api.main import app
    return TestClient(app)


def test_health_check_healthy(simple_client):
    """Test that health check returns healthy status."""
    response = simple_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "llm_available" in data


def test_health_check_response_format(simple_client):
    """Test that health check returns the correct response format."""
    response = simple_client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "status" in data
    assert "llm_available" in data

    # Check types
    assert isinstance(data["status"], str)
    assert isinstance(data["llm_available"], bool)
