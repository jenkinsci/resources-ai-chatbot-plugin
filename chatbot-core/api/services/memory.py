"""
Handles in-memory chat session state (conversation memory).
Provides utility functions for session lifecycle.
"""

import uuid
import logging
from datetime import datetime, timedelta
from threading import Lock
from typing import List, Dict
from langchain.memory import ConversationBufferMemory
from api.services.sessionmanager import(
    delete_session_file,
    load_session,
    append_message,
    save_session_metadata,
    get_session_owner,
    list_user_sessions,
    get_session_metadata
)
logger = logging.getLogger(__name__)

MAX_SESSIONS_PER_USER = 20  # Resource Governance: Prevent disk exhaustion

# sessionId --> {"memory": ConversationBufferMemory, "last_accessed": datetime}
_sessions: Dict[str, Dict] = {}
_user_sessions: Dict[str, List[str]] = {}
_lock = Lock()

def _delete_oldest_user_session(session_ids: List[str]) -> None:
    """
    Helper to identify and delete the oldest session from a list.
    Used for enforcing user quotas.
    """
    oldest_sid = None
    oldest_time = datetime.max

    for sid in session_ids:
        # Check in-memory first for speed
        with _lock:
            if sid in _sessions:
                ts = _sessions[sid]["last_accessed"]
                if ts < oldest_time:
                    oldest_time = ts
                    oldest_sid = sid
                continue

        # Fallback to disk metadata
        meta = get_session_metadata(sid)
        if meta and "last_updated" in meta:
            try:
                ts = datetime.fromisoformat(meta["last_updated"])
                if ts < oldest_time:
                    oldest_time = ts
                    oldest_sid = sid
            except ValueError:
                continue

    if oldest_sid:
        logger.info("Quota reached. Deleting oldest session: %s", oldest_sid)
        delete_session(oldest_sid)

def init_session(user_id: str, user_name: str = "User") -> str:
    """
    Initialize a new chat session and store its memory object.
    Args:
        user_id (str): The Jenkins User ID.
    Returns:
    str: A newly generated UUID representing the session ID.
    """
    existing_sessions = list_user_sessions(user_id)
    if len(existing_sessions) >= MAX_SESSIONS_PER_USER:
        _delete_oldest_user_session(existing_sessions)

    session_id = str(uuid.uuid4())

    save_session_metadata(session_id, user_id, user_name)

    with _lock:
        _sessions[session_id] = {
            "memory": ConversationBufferMemory(return_messages=True),
            "last_accessed": datetime.now(),
            "owner": user_id
        }

    return session_id

def validate_session_access(session_id: str, user_id: str) -> bool:
    """
    Security Check: Verifies if the given user owns the session.
    Checks both volatile memory (fast) and persistent storage (reliable).

    Args:
        session_id (str): The session to access.
        user_id (str): The user attempting access.

    Returns:
        bool: True if access is allowed, False otherwise.
    """
    with _lock:
        session_data = _sessions.get(session_id)
        if session_data:
            stored_owner = session_data.get("owner")
            return stored_owner == user_id

    stored_owner = get_session_owner(session_id)
    # DEBUG PRINT
    print(f"[DEBUG DISK]   ID: {session_id} | Stored: '{stored_owner}' vs Request: '{user_id}'")

    return stored_owner == user_id

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

        if session_data :
            session_data["last_accessed"] = datetime.now()
            return session_data["memory"]

        history = load_session(session_id)
        if not history:
            return None

        owner = get_session_owner(session_id)

        memory = ConversationBufferMemory(return_messages=True)
        for msg in history:
            memory.chat_memory.add_message(# pylint: disable=no-member
                {
                    "role": msg["role"],
                    "content": msg["content"],
                }
            )

        _sessions[session_id] = {
            "memory": memory,
            "last_accessed": datetime.now(),
            "owner": owner
        }

        return memory


def persist_session(session_id: str)-> None:
    """
    Persist the current session messages to disk.

    Args:
        session_id (str): The session identifier.
    """
    session_data = get_session(session_id)
    if session_data:
        messages = list(session_data.chat_memory.messages)
        append_message(session_id, messages)

        with _lock:
            owner = _sessions.get(session_id, {}).get("owner")

        if owner:
            save_session_metadata(session_id, owner)



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
        in_memory_deleted = _sessions.pop(session_id, None) is not None

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

def get_session_count() -> int:
    """Return the number of active sessions in memory."""
    with _lock:
        return len(_sessions)

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

        meta = get_session_metadata(session_id)
        if meta and "last_updated" in meta:
            try:
                return datetime.fromisoformat(meta["last_updated"])
            except ValueError:
                pass

        history = load_session(session_id)
        if not history:
            return None


    return history["last_accessed"]

def set_last_accessed(session_id: str, last_accessed: datetime) -> None:
    """
    Manually set the last accessed timestamp.
    Useful for testing TTL expiration.
    """
    if session_id in _sessions:
        # Force the update.
        # We grab the memory object (index 0) and attach the new timestamp.
        current_entry = _sessions[session_id]

        # Handle case where it might be a tuple or just the object
        memory_obj = current_entry[0] if isinstance(current_entry, tuple) else current_entry

        _sessions[session_id] = (memory_obj, last_accessed)

def cleanup_expired_sessions(timeout_hours: int = 24) -> int:
    """
    Remove sessions that have not been accessed within the configured timeout period.

    Returns:
        int: The number of sessions that were cleaned up.
    """
    cutoff_time = datetime.now() - timedelta(hours=timeout_hours)

    # Identify expired sessions
    # We iterate over items. Value is a tuple: (memory_object, last_accessed_time)
    expired_session_ids = [
        session_id
        for session_id, session_data in _sessions.items()
        if isinstance(session_data, tuple)
        and len(session_data) > 1
        and session_data[1] < cutoff_time
    ]

    # Delete them
    count = 0
    for session_id in expired_session_ids:
        delete_session(session_id)
        count += 1

    return count
