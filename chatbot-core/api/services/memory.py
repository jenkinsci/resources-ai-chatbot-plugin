"""
Handles in-memory chat session state (conversation memory).
Provides utility functions for session lifecycle.
"""

import uuid
from threading import Lock
from langchain.memory import ConversationBufferMemory

# sessionId --> history
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
        _sessions[session_id] = ConversationBufferMemory(return_messages=True)
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
        memory = _sessions.get(session_id)
    return memory

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
