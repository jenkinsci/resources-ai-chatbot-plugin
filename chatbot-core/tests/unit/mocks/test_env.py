"""Fixtures for unit tests."""

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
def mock_get_session(mocker):
    """Mock the memory.get_session function."""
    return mocker.patch("api.services.chat_service.get_session")

@pytest.fixture
def mock_retrieve_context(mocker):
    """Mock the retrieve_context function."""
    return mocker.patch("api.services.chat_service.retrieve_context")

@pytest.fixture
def mock_prompt_builder(mocker):
    """Mock the build_prompt function."""
    return mocker.patch("api.services.chat_service.build_prompt")

@pytest.fixture
def mock_llm_provider(mocker):
    """Mock the LLM provider generate function."""
    return mocker.patch("api.services.chat_service.llm_provider")

@pytest.fixture
def mock_get_relevant_documents(mocker):
    """Mock the get_relevant_documents function."""
    return mocker.patch("api.services.chat_service.get_relevant_documents")

@pytest.fixture
def mock_init_session(mocker):
    """Mock the init_session function."""
    return mocker.patch("api.routes.chatbot.init_session")

@pytest.fixture
def mock_session_exists(mocker):
    """Mock the session_exists function."""
    return mocker.patch("api.routes.chatbot.session_exists")

@pytest.fixture
def mock_delete_session(mocker):
    """Mock the delete_session function."""
    return mocker.patch("api.routes.chatbot.delete_session")

@pytest.fixture
def mock_get_chatbot_reply(mocker):
    """Mock the get_chatbot_reply function."""
    return mocker.patch("api.routes.chatbot.get_chatbot_reply")
