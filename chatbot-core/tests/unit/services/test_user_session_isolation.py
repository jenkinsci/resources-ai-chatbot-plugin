"""
Unit tests for user session isolation and authentication features.
"""

import pytest
from api.services.memory import (
    init_session,
    get_user_sessions,
    validate_session_owner,
    get_session_user_id,
    delete_session,
    reset_sessions,
)


@pytest.fixture(autouse=True)
def clean_sessions():
    """Ensure clean state before each test."""
    reset_sessions()
    yield
    reset_sessions()


def test_init_session_with_user_id():
    """Test session initialization with user_id."""
    user_id = "alice"
    session_id = init_session(user_id)

    assert session_id is not None
    assert len(session_id) > 0

    # Verify user ownership
    assert validate_session_owner(session_id, user_id) is True


def test_init_session_defaults_to_anonymous_with_unique_id():
    """Test session initialization defaults to unique anonymous ID when no user_id provided."""
    session_id = init_session()

    assert session_id is not None
    stored_user_id = get_session_user_id(session_id)
    # Should be in format "anonymous:<session_id>"
    assert stored_user_id.startswith("anonymous:")
    # The anonymous ID should contain the session ID for uniqueness
    assert session_id in stored_user_id


def test_anonymous_sessions_are_isolated():
    """Test that different anonymous sessions have unique IDs and are isolated."""
    session1 = init_session()
    session2 = init_session()

    user_id_1 = get_session_user_id(session1)
    user_id_2 = get_session_user_id(session2)

    # Each anonymous session should have a unique ID
    assert user_id_1 != user_id_2
    assert user_id_1.startswith("anonymous:")
    assert user_id_2.startswith("anonymous:")

    # Session 1's anonymous ID should not be able to access session 2
    assert validate_session_owner(session1, user_id_1) is True
    assert validate_session_owner(session2, user_id_1) is False
    assert validate_session_owner(session2, user_id_2) is True
    assert validate_session_owner(session1, user_id_2) is False


def test_get_user_sessions():
    """Test retrieving all sessions for a specific user."""
    user_id = "bob"

    # Create multiple sessions for the same user
    session1 = init_session(user_id)
    session2 = init_session(user_id)
    session3 = init_session(user_id)

    # Create session for different user
    other_session = init_session("charlie")

    user_sessions = get_user_sessions(user_id)

    assert len(user_sessions) == 3
    assert session1 in user_sessions
    assert session2 in user_sessions
    assert session3 in user_sessions
    assert other_session not in user_sessions


def test_validate_session_owner_success():
    """Test successful session ownership validation."""
    user_id = "dave"
    session_id = init_session(user_id)

    assert validate_session_owner(session_id, user_id) is True


def test_validate_session_owner_failure():
    """Test failed session ownership validation (wrong user)."""
    user_id = "eve"
    session_id = init_session(user_id)

    # Try to validate with different user
    assert validate_session_owner(session_id, "mallory") is False


def test_validate_session_owner_nonexistent_session():
    """Test validation of non-existent session."""
    assert validate_session_owner("fake-session-id", "alice") is False


def test_get_session_user_id():
    """Test retrieving user_id from session."""
    user_id = "frank"
    session_id = init_session(user_id)

    retrieved_user_id = get_session_user_id(session_id)
    assert retrieved_user_id == user_id


def test_get_session_user_id_nonexistent():
    """Test retrieving user_id from non-existent session."""
    user_id = get_session_user_id("nonexistent-session")
    assert user_id is None


def test_delete_session_removes_from_user_mapping():
    """Test that deleting a session removes it from user mapping."""
    user_id = "grace"
    session_id = init_session(user_id)

    # Verify session exists
    assert session_id in get_user_sessions(user_id)

    # Delete session
    result = delete_session(session_id)
    assert result is True

    # Verify session removed from user mapping
    assert session_id not in get_user_sessions(user_id)


def test_multiple_users_session_isolation():
    """Test that multiple users have isolated session spaces."""
    alice_id = "alice"
    bob_id = "bob"

    alice_session1 = init_session(alice_id)
    alice_session2 = init_session(alice_id)
    bob_session1 = init_session(bob_id)
    bob_session2 = init_session(bob_id)

    alice_sessions = get_user_sessions(alice_id)
    bob_sessions = get_user_sessions(bob_id)

    # Alice should only see her sessions
    assert len(alice_sessions) == 2
    assert alice_session1 in alice_sessions
    assert alice_session2 in alice_sessions
    assert bob_session1 not in alice_sessions
    assert bob_session2 not in alice_sessions

    # Bob should only see his sessions
    assert len(bob_sessions) == 2
    assert bob_session1 in bob_sessions
    assert bob_session2 in bob_sessions
    assert alice_session1 not in bob_sessions
    assert alice_session2 not in bob_sessions


def test_user_cannot_validate_another_users_session():
    """Test security: user cannot validate ownership of another user's session."""
    user1 = "user1"
    user2 = "user2"

    session_user1 = init_session(user1)

    # user2 should not be able to claim ownership of user1's session
    assert validate_session_owner(session_user1, user2) is False

    # user1 should be able to validate their own session
    assert validate_session_owner(session_user1, user1) is True


def test_empty_user_sessions_list():
    """Test that a user with no sessions gets an empty list."""
    sessions = get_user_sessions("user-with-no-sessions")
    assert not sessions


def test_delete_all_user_sessions_cleans_up_user_entry():
    """Test that deleting all of a user's sessions cleans up the user mapping."""
    user_id = "cleanup-test-user"

    session1 = init_session(user_id)
    session2 = init_session(user_id)

    # Verify user has sessions
    assert len(get_user_sessions(user_id)) == 2

    # Delete both sessions
    delete_session(session1)
    delete_session(session2)

    # User should have no sessions
    assert len(get_user_sessions(user_id)) == 0
