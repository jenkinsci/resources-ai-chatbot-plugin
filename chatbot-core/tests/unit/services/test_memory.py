"""Unit tests for in-memory chat session management logic."""

import uuid
import pytest
from langchain.memory import ConversationBufferMemory
from api.services import memory


@pytest.fixture(autouse=True)
def reset_memory_sessions():
    """Executed before any test to reset the _sessions across the tests."""
    memory.reset_sessions()

def test_init_session_creates_new_session():
    """Test that a new session is initialized with a valid UUID and is stored."""
    session_id = memory.init_session()

    assert isinstance(session_id, str)
    assert uuid.UUID(session_id)
    assert memory.session_exists(session_id)

def test_get_session_returns_existing_session():
    """Test that get_session retrieves the correct memory object for a valid session."""
    session_id = memory.init_session()
    session = memory.get_session(session_id)

    assert isinstance(session, ConversationBufferMemory)
    assert session is memory.get_session(session_id)

def test_get_session_returns_none_for_invalid_id():
    """Test that get_session returns None when the session ID does not exist."""
    assert memory.get_session("missing-session-id") is None

def test_delete_session_removes_existing_session():
    """Test that delete_session successfully removes an existing session."""
    session_id = memory.init_session()
    deleted = memory.delete_session(session_id)

    assert deleted is True
    assert memory.get_session(session_id) is None
    assert memory.session_exists(session_id) is False

def test_delete_session_returns_false_if_not_exists():
    """Test that delete_session returns False when session does not exist."""
    deleted = memory.delete_session("missing-session-id")

    assert deleted is False

def test_session_exists_returns_true_for_existing_session():
    """Test that session_exists returns True for a valid, initialized session."""
    session_id = memory.init_session()

    assert memory.session_exists(session_id)

def test_session_exists_returns_false_for_missing_session():
    """Test that session_exists returns False when session is not present."""
    assert not memory.session_exists("missing-session-id")
