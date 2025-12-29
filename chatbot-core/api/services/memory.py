"""
Handles in-memory chat session state (conversation memory).
Provides utility functions for session lifecycle.
"""

import uuid
from threading import Lock
from langchain.memory import ConversationBufferMemory
from api.services.sessionmanager import _delete_session, _load_session_from_json
from datetime import datetime


# sessionId --> ConversationBufferMemory
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
    Retrieve the chat session memory for the given session ID.
    Lazily restores from disk if missing in memory.

    Args:
        session_id (str): The session identifier.

    Returns:
        ConversationBufferMemory | None: The memory object if found, else None.
    """

    with _lock:
        memory = _sessions.get(session_id)

        if memory is None:
            history = _load_session_from_json(session_id)
            if not history:
                return None

            memory = ConversationBufferMemory(return_messages=True)
            for msg in history:
                memory.chat_memory.add_message(
                    {"role": msg["role"], "content": msg["content"]}
                )

            _sessions[session_id] = {
            "memory": memory,
            "last_accessed": datetime.now(datetime.UTC),
        }

    return memory


def delete_session(session_id: str) -> bool:
    """
    Delete a chat session and its persisted data.

    Args:
    session_id (str): The session identifier.

    Returns:
        bool: True if the session existed and was deleted, False otherwise.
    """
    with _lock:
        in_memory_deleted = _sessions.pop(session_id, None) is not None

    if in_memory_deleted:
        return _delete_session(session_id)

    return False


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
