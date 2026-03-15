"""
Handles in-memory chat session state (conversation memory).
Provides utility functions for session lifecycle.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory
from api.config.loader import CONFIG
from api.services.sessionmanager import (
    delete_session_file,
    load_session,
    session_exists_in_json,
    get_persisted_session_ids
)


_sessions = {}
_lock = Lock()
_ROLE_TO_MESSAGE_CLASS = {
    "human": HumanMessage,
    "user": HumanMessage,
    "ai": AIMessage,
    "assistant": AIMessage,
    "system": SystemMessage,
}


class BoundedChatMessageHistory(ChatMessageHistory):
    """A bounded chat message history that keeps only the last N messages."""

    def _enforce_limit(self):
        if len(self.messages) > 2:
            del self.messages[:-2]

    def add_message(self, message):
        """Add a single message and enforce limit."""
        super().add_message(message)
        self._enforce_limit()

    def add_messages(self, messages):
        """Add a single messages and enforce limit."""
        super().add_messages(messages)
        self._enforce_limit()


def init_session() -> str:
    """
    Initialize a new chat session and store its memory object.
    ...
    """
    session_id = str(uuid.uuid4())
    with _lock:
        _sessions[session_id] = {
            "memory": ConversationBufferWindowMemory(
                k=10,
                return_messages=True,
                chat_memory=BoundedChatMessageHistory()  # Injecting the hard limit
            ),
            "last_accessed": datetime.now()
        }
    return session_id


def get_session(session_id: str) -> Optional[ConversationBufferWindowMemory]:
    """
    Retrieve the chat session memory for the given session ID.
    Lazily restores from disk if missing in memory.

    Args:
        session_id (str): The session identifier.

    Returns:
        Optional[ConversationBufferMemory]: The memory object if found, else None.
    """

    with _lock:

        session_data = _sessions.get(session_id)

        if session_data:
            session_data["last_accessed"] = datetime.now()
            return session_data["memory"]

        history = load_session(session_id)
        if not history:
            return None

        # PATCH: Use bounded window memory for restored sessions too
        memory = ConversationBufferWindowMemory(
            k=10,
            return_messages=True,
            chat_memory=BoundedChatMessageHistory()  # <-- You MUST inject it here too!
        )

        # When we load history from disk, LangChain's window memory will
        # automatically truncate older messages as we add them here.
        # When we load history from disk, we handle both dicts and LangChain objects
        for msg in history:
            # Handle dictionary format (JSON) or LangChain object format
            if isinstance(msg, dict):
                content = msg.get("content", "")
                role = msg.get("role", "human")
            else:
                content = getattr(msg, "content", "")
                role = "human" if msg.type == "human" else "ai"

            # Add to the bounded memory
            if role == "human":
                memory.chat_memory.add_user_message(content)
            else:
                memory.chat_memory.add_ai_message(content)

        _sessions[session_id] = {
            "memory": memory,
            "last_accessed": datetime.now()
        }

        return memory


async def get_session_async(session_id: str) -> Optional[ConversationBufferWindowMemory]:
    """
    Async wrapper for get_session to prevent event loop blocking.
    """
    return await asyncio.to_thread(get_session, session_id)


def persist_session(session_id: str) -> None:  # pylint: disable=unused-argument
    """
    Persist the current session messages to disk.
    """


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


def get_last_accessed(session_id: str) -> datetime | None:
    """
    Get the last accessed timestamp for a given session.

    Args:
        session_id (str): The session identifier.

    Returns:
        Optional[datetime]: The last accessed timestamp if session exists, else None.
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
            in_memory_deleted = _sessions.pop(session_id, None) is not None
            if in_memory_deleted and session_exists_in_json(session_id):
                delete_session_file(session_id)

    return len(expired_session_ids)


def reload_persisted_sessions() -> int:
    """
    Load all persisted sessions from disk into memory.
    Called once at application startup.
    """
    session_ids = get_persisted_session_ids()
    loaded = 0
    for session_id in session_ids:
        if get_session(session_id) is not None:
            loaded += 1
    return loaded
