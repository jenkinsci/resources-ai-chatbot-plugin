"""Unit tests for the pipeline validation endpoint."""

# pylint: disable=wrong-import-position,duplicate-code

import sys
from unittest.mock import MagicMock

for mod in (
    "sentence_transformers",
    "litellm",
    "faiss",
    "langchain",
    "langchain.memory",
    "langchain.prompts",
    "langchain.chains",
    "langchain.schema",
    "langchain_community",
    "langchain_community.embeddings",
    "langchain_community.vectorstores",
    "langchain_core",
    "langchain_core.messages",
    "torch",
    "transformers",
    "tokenizers",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.routes.chatbot import router


@pytest.fixture(name="simple_client")
def simple_client_fixture():
    """Fixture providing a lightweight TestClient for router tests."""
    app = FastAPI()
    app.include_router(router, prefix="/api/chatbot")
    return TestClient(app)


def test_validate_valid_pipeline_endpoint(simple_client):
    """Test validating a valid declarative pipeline through API."""
    pipeline = """
    pipeline {
        agent any
        stages {
            stage('Build') {
                steps {
                    sh 'mvn clean install'
                }
            }
        }
    }
    """
    response = simple_client.post(
        "/api/chatbot/pipeline/validate",
        json={"pipeline_content": pipeline},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["pipeline_type"] == "declarative"
    assert data["errors"] == []
    assert data["stages"] == ["Build"]


def test_validate_invalid_pipeline_endpoint(simple_client):
    """Test validating an invalid pipeline through API."""
    pipeline = """
    pipeline {
        stages {
            stage('Build') {
                steps {
                    sh 'mvn clean install'
                }
            }
        }
    }
    """
    response = simple_client.post(
        "/api/chatbot/pipeline/validate",
        json={"pipeline_content": pipeline},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert any("agent" in err.lower() for err in data["errors"])


def test_validate_empty_pipeline_endpoint(simple_client):
    """Test submitting empty pipeline content."""
    response = simple_client.post(
        "/api/chatbot/pipeline/validate",
        json={"pipeline_content": "   "},
    )

    assert response.status_code == 422  # Pydantic validation error for empty content
