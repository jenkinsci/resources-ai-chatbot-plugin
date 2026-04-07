"""Fixtures for integration tests."""

import pytest
from fastapi import FastAPI
from api.routes.chatbot import router

@pytest.fixture
def fastapi_app() -> FastAPI:
    """Fixture to create FastAPI app instance with routes."""
    app = FastAPI()
    app.include_router(router)
    return app

@pytest.fixture
def mock_llm_provider(mocker):
    """Mock the LLM provider generate function."""
    return mocker.patch("api.services.chat_service.llm_provider")

@pytest.fixture
def mock_get_relevant_documents(mocker):
    """Mock the get_relevant_documents function."""
    return mocker.patch("api.services.chat_service.get_relevant_documents")
