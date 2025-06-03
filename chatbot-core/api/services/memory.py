"""
Handles in-memory chat session state (conversation memory).
Provides utility functions for session lifecycle.
"""

import uuid
from langchain.memory import ConversationBufferMemory

# sessionId --> history
_sessions = {}

def init_session() -> str:
    """
    Initialize a new chat session and store its memory object.

    Returns:
        str: A newly generated UUID representing the session ID.
    """
    session_id = str(uuid.uuid4())
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
    return _sessions.get(session_id)

def delete_session(session_id: str) -> bool:
    """
    Delete an existing chat session and its memory.

    Args:
        session_id (str): The session identifier.

    Returns:
        bool: True if the session existed and was deleted, False otherwise.
    """
    return _sessions.pop(session_id, None) is not None

def session_exists(session_id: str) -> bool:
    """
    Check if a chat session with the given ID exists.

    Args:
        session_id (str): The session identifier.

    Returns:
        bool: True if the session exists, False otherwise.
    """
    return session_id in _sessions
