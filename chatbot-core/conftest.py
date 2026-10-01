"""Top-level conftest for the entire test suite."""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Combine the plugins from both unit and integration tests
pytest_plugins = [
    "tests.unit.mocks.test_env",
    "tests.integration.mocks"
]


@pytest.fixture
def client(fastapi_app: FastAPI):
    """Fixture to provide a TestClient for the FastAPI app."""
    return TestClient(fastapi_app)
