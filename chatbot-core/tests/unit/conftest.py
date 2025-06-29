"""conftest for unit tests."""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

pytest_plugins = ["tests.unit.mocks.test_env"]

@pytest.fixture
def client(fastapi_app: FastAPI):
    """Fixture to provide a TestClient for the FastAPI app."""
    return TestClient(fastapi_app)
