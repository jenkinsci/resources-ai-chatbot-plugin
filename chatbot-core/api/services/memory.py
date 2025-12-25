"""
Handles in-memory chat session state (conversation memory).
Provides utility functions for session lifecycle.
"""

import uuid
from datetime import datetime, timedelta
from threading import Lock
from langchain.memory import ConversationBufferMemory
from api.config.loader import CONFIG

# sessionId --> {"memory": ConversationBufferMemory, "last_accessed": datetime}
_sessions = {}
_lock = Lock()

def init_session() -> str:
    """
    Initialize a new chat session and store its memory object.

    Returns:
        str: A newly generated UUID representing the session ID.
    """
    session_id = str(uuid.uuid4())
    with _lock:
        _sessions[session_id] = {
            "memory": ConversationBufferMemory(return_messages=True),
            "last_accessed": datetime.now()
        }
    return session_id

def get_session(session_id: str) -> ConversationBufferMemory | None:
    """
    Retrieve the conversation memory for a given session ID.

    Args:
        session_id (str): The session identifier.

    Returns:
        ConversationBufferMemory | None: The memory object if found, else None.
    """
    with _lock:
        session_data = _sessions.get(session_id)
        if session_data:
            # Update last accessed timestamp
            session_data["last_accessed"] = datetime.now()
            return session_data["memory"]
    return None

def delete_session(session_id: str) -> bool:
    """
    Delete an existing chat session and its memory.

    Args:
        session_id (str): The session identifier.

    Returns:
        bool: True if the session existed and was deleted, False otherwise.
    """
    with _lock:
        deleted = _sessions.pop(session_id, None) is not None
    return deleted

def session_exists(session_id: str) -> bool:
    """
    Check if a chat session with the given ID exists.

    Args:
        session_id (str): The session identifier.

    Returns:
        bool: True if the session exists, False otherwise.
    """
    with _lock:
        exists = session_id in _sessions
    return exists

def reset_sessions():
    """Helper fucntion to clear all sessions. Useful for testing."""
    with _lock:
        _sessions.clear()

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
        if session_data:
            return session_data["last_accessed"]
    return None

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
            del _sessions[session_id]

    return len(expired_session_ids)
