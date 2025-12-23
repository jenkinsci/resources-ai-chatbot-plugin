"""Unit tests for in-memory chat session management logic."""

import time
import uuid
from datetime import datetime, timedelta

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


# Tests for session cleanup (TTL mechanism) - Issue #63


def test_init_session_creates_session_with_timestamp():
    """Test that new sessions are created with last_accessed timestamp."""
    session_id = memory.init_session()

    # Check that session data contains both memory and timestamp
    session_data = memory._sessions.get(session_id)  # pylint: disable=protected-access
    assert session_data is not None
    assert "memory" in session_data
    assert "last_accessed" in session_data
    assert isinstance(session_data["memory"], ConversationBufferMemory)
    assert isinstance(session_data["last_accessed"], datetime)


def test_get_session_updates_timestamp():
    """Test that accessing a session updates its last_accessed timestamp."""
    session_id = memory.init_session()
    initial_timestamp = memory._sessions[session_id]["last_accessed"]  # pylint: disable=protected-access

    # Wait a bit to ensure timestamp difference
    time.sleep(0.1)

    # Access the session
    retrieved_memory = memory.get_session(session_id)
    updated_timestamp = memory._sessions[session_id]["last_accessed"]  # pylint: disable=protected-access

    assert retrieved_memory is not None
    assert updated_timestamp > initial_timestamp


def test_cleanup_expired_sessions_removes_old_sessions():
    """Test that cleanup_expired_sessions removes sessions older than timeout."""
    # Create test sessions
    session1 = memory.init_session()
    session2 = memory.init_session()
    session3 = memory.init_session()

    # Manually set session1 and session2 to be expired (>24 hours old)
    old_timestamp = datetime.now() - timedelta(hours=25)
    memory._sessions[session1]["last_accessed"] = old_timestamp  # pylint: disable=protected-access
    memory._sessions[session2]["last_accessed"] = old_timestamp  # pylint: disable=protected-access

    # session3 remains fresh
    assert len(memory._sessions) == 3  # pylint: disable=protected-access

    # Run cleanup
    cleaned_count = memory.cleanup_expired_sessions()

    # Verify results
    assert cleaned_count == 2
    assert len(memory._sessions) == 1  # pylint: disable=protected-access
    assert session3 in memory._sessions  # pylint: disable=protected-access
    assert session1 not in memory._sessions  # pylint: disable=protected-access
    assert session2 not in memory._sessions  # pylint: disable=protected-access


def test_cleanup_expired_sessions_preserves_active_sessions():
    """Test that cleanup preserves sessions within the timeout period."""
    # Create sessions
    session1 = memory.init_session()
    session2 = memory.init_session()

    # Both sessions are fresh (just created)
    initial_count = len(memory._sessions)  # pylint: disable=protected-access

    # Run cleanup
    cleaned_count = memory.cleanup_expired_sessions()

    # No sessions should be cleaned up
    assert cleaned_count == 0
    assert len(memory._sessions) == initial_count  # pylint: disable=protected-access
    assert memory.session_exists(session1)
    assert memory.session_exists(session2)


def test_cleanup_expired_sessions_with_no_sessions():
    """Test that cleanup handles empty session dictionary gracefully."""
    memory.reset_sessions()

    # Run cleanup on empty sessions
    cleaned_count = memory.cleanup_expired_sessions()

    assert cleaned_count == 0
    assert len(memory._sessions) == 0  # pylint: disable=protected-access
