"""
Handles in-memory chat session state (conversation memory).
Provides utility functions for session lifecycle.
"""

import uuid
from datetime import datetime, timedelta
from threading import Lock
from typing import List
from langchain.memory import ConversationBufferMemory
from api.config.loader import CONFIG
from api.services.sessionmanager import (
    delete_session_file,
    load_session,
    session_exists_in_json,
    append_message,
    save_session_metadata,
    load_session_metadata
)
# sessionId --> {"memory": ConversationBufferMemory, "last_accessed": datetime, "user_id": str}
# user_id --> Set[session_id]


_sessions = {}
_user_sessions = {}  # Track which sessions belong to which users
_lock = Lock()


def init_session(user_id: str = "anonymous") -> str:
    """
    Initialize a new chat session and store its memory object.

    Args:
        user_id (str): The Jenkins user ID. Defaults to "anonymous" for backward compatibility.

    Returns:
        str: A newly generated UUID representing the session ID.
    """
    session_id = str(uuid.uuid4())
    with _lock:
        _sessions[session_id] = {
            "memory": ConversationBufferMemory(return_messages=True),
            "last_accessed": datetime.now(),
            "user_id": user_id
        }

        # Track user-session relationship
        if user_id not in _user_sessions:
            _user_sessions[user_id] = set()
        _user_sessions[user_id].add(session_id)

    # Persist user metadata to disk
    save_session_metadata(session_id, user_id)

    return session_id


def get_session(session_id: str) -> ConversationBufferMemory | None:
    """
    Retrieve the chat session memory for the given session ID.
    Lazily restores from disk if missing in memory.

    Args:
        session_id (str): The session identifier.

    Returns:
        ConversationBufferMemory | None: The memory object if found, else None.
    """

    with _lock:

        session_data = _sessions.get(session_id)

        if session_data:
            session_data["last_accessed"] = datetime.now()
            return session_data["memory"]

        history = load_session(session_id)
        if not history:
            return None

        # Load user_id from metadata
        metadata = load_session_metadata(session_id)
        user_id = metadata.get(
            "user_id", "anonymous") if metadata else "anonymous"

        memory = ConversationBufferMemory(return_messages=True)
        for msg in history:
            memory.chat_memory.add_message(  # pylint: disable=no-member
                {
                    "role": msg["role"],
                    "content": msg["content"],
                }
            )

        _sessions[session_id] = {
            "memory": memory,
            "last_accessed": datetime.now(),
            "user_id": user_id
        }

        # Restore user-session mapping
        if user_id not in _user_sessions:
            _user_sessions[user_id] = set()
        _user_sessions[user_id].add(session_id)

        return memory


def persist_session(session_id: str) -> None:
    """
    Persist the current session messages to disk.

    Args:
        session_id (str): The session identifier.
    """
    session_data = get_session(session_id)
    if session_data:
        messages = list(session_data.chat_memory.messages)
        append_message(session_id, messages)


def delete_session(session_id: str) -> bool:
    """
    Delete a chat session and its persisted data.

    Args:
    session_id (str): The session identifier.

    Returns:
        bool: True if the session existed and was deleted, False otherwise.
    """
    with _lock:
        if session_id is None:
            return True

        session_data = _sessions.get(session_id)
        user_id = session_data.get(
            "user_id", "anonymous") if session_data else None

        in_memory_deleted = _sessions.pop(session_id, None) is not None

        # Remove from user-session mapping
        if user_id and user_id in _user_sessions:
            _user_sessions[user_id].discard(session_id)
            # Clean up empty user entries
            if not _user_sessions[user_id]:
                del _user_sessions[user_id]

    if in_memory_deleted:
        delete_session_file(session_id)

    return in_memory_deleted


def session_exists(session_id: str) -> bool:
    """
    Check if a chat session exists in memory.

    Args:
    session_id (str): The session identifier.

    Returns:
        bool: True if the session exists, False otherwise.
    """
    with _lock:
        return session_id in _sessions


def reset_sessions():
    """Helper function to clear all sessions. Useful for testing."""
    with _lock:
        _sessions.clear()
        _user_sessions.clear()


def get_last_accessed(session_id: str) -> datetime | None:
    """
    Get the last accessed timestamp for a given session.

    Args:
        session_id (str): The session identifier.

    Returns:
        datetime | None: The last accessed timestamp if session exists, else None.
    """
    with _lock:
        session_data = _sessions.get(session_id)
        if session_data is not None:
            return session_data["last_accessed"]

        history = load_session(session_id)
        if not history:
            return None

    return history["last_accessed"]


def set_last_accessed(session_id: str, timestamp: datetime) -> bool:
    """
    Set the last accessed timestamp for a given session (for testing purposes).

    Args:
        session_id (str): The session identifier.
        timestamp (datetime): The timestamp to set.

    Returns:
        bool: True if session exists and timestamp was set, False otherwise.
    """
    with _lock:
        session_data = _sessions.get(session_id)
        if session_data:
            session_data["last_accessed"] = timestamp
            return True

        history = load_session(session_id)
        if not history:
            return False

        history["last_accessed"] = timestamp
        return True

    return False


def get_session_count() -> int:
    """
    Get the total number of active sessions (for testing purposes).

    Returns:
        int: The number of active sessions.
    """
    with _lock:
        return len(_sessions)


def cleanup_expired_sessions() -> int:
    """
    Remove sessions that have not been accessed within the configured timeout period.

    Returns:
        int: The number of sessions that were cleaned up.
    """
    timeout_hours = CONFIG.get("session", {}).get("timeout_hours", 24)
    now = datetime.now()
    cutoff_time = now - timedelta(hours=timeout_hours)

    with _lock:
        expired_session_ids = [
            session_id
            for session_id, session_data in _sessions.items()
            if session_data["last_accessed"] < cutoff_time
        ]

        for session_id in expired_session_ids:
            session_data = _sessions.get(session_id)
            user_id = session_data.get(
                "user_id", "anonymous") if session_data else None

            in_memory_deleted = _sessions.pop(session_id, None) is not None

            # Remove from user-session mapping
            if user_id and user_id in _user_sessions:
                _user_sessions[user_id].discard(session_id)
                if not _user_sessions[user_id]:
                    del _user_sessions[user_id]

            if in_memory_deleted and session_exists_in_json(session_id):
                delete_session_file(session_id)

    return len(expired_session_ids)


def get_user_sessions(user_id: str) -> List[str]:
    """
    Retrieve all session IDs for a given user.

    Args:
        user_id (str): The Jenkins user ID.

    Returns:
        List[str]: List of session IDs belonging to the user.
    """
    with _lock:
        return list(_user_sessions.get(user_id, set()))


def validate_session_owner(session_id: str, user_id: str) -> bool:
    """
    Validate that a session belongs to a specific user.

    Args:
        session_id (str): The session identifier.
        user_id (str): The Jenkins user ID.

    Returns:
        bool: True if the session belongs to the user, False otherwise.
    """
    with _lock:
        # Check in-memory mapping first
        if user_id in _user_sessions and session_id in _user_sessions[user_id]:
            return True

        # Check if session exists and load its metadata
        session_data = _sessions.get(session_id)
        if session_data:
            return session_data.get("user_id") == user_id

        # Load from disk if not in memory
        metadata = load_session_metadata(session_id)
        if metadata:
            stored_user_id = metadata.get("user_id", "anonymous")
            return stored_user_id == user_id

        return False


def get_session_user_id(session_id: str) -> str | None:
    """
    Get the user_id associated with a session.

    Args:
        session_id (str): The session identifier.

    Returns:
        str | None: The user_id if session exists, else None.
    """
    with _lock:
        session_data = _sessions.get(session_id)
        if session_data:
            return session_data.get("user_id")

        # Load from disk if not in memory
        metadata = load_session_metadata(session_id)
        if metadata:
            return metadata.get("user_id", "anonymous")

        return None
