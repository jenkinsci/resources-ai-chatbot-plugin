"""
Handles in-memory chat session state (conversation memory).
Provides utility functions for session lifecycle.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from api.config.loader import CONFIG
from api.services.sessionmanager import(
    delete_session_file,
    load_session,
    session_exists_in_json,
    append_message
)
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


def _dict_to_message(msg_dict: dict):
    """
    Convert a serialized message dict back to a LangChain message object.

    Args:
        msg_dict: A dictionary with 'type' and 'data' keys representing the message.

    Returns:
        A LangChain message object (HumanMessage, AIMessage, etc.)
    """
    msg_type = msg_dict.get("type", "HumanMessage")
    msg_data = msg_dict.get("data", {})

    if msg_type == "HumanMessage":
        return HumanMessage(
            content=msg_data.get("content", ""),
            additional_kwargs=msg_data.get("additional_kwargs", {})
        )
    elif msg_type == "AIMessage":
        return AIMessage(
            content=msg_data.get("content", ""),
            additional_kwargs=msg_data.get("additional_kwargs", {})
        )
    else:
        # Fallback to HumanMessage for unknown types
        return HumanMessage(
            content=msg_data.get("content", ""),
            additional_kwargs=msg_data.get("additional_kwargs", {})
        )


def get_session(session_id: str) -> Optional[ConversationBufferMemory]:
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

        if session_data :
            session_data["last_accessed"] = datetime.now()
            return session_data["memory"]

        history = load_session(session_id)
        if not history:
            return None

        memory = ConversationBufferMemory(return_messages=True)
        for msg in history:
            # Check if the message is in the new serialized format or old format
            if isinstance(msg, dict) and "type" in msg and "data" in msg:
                # New format: {"type": "HumanMessage", "data": {...}}
                message_obj = _dict_to_message(msg)
                memory.chat_memory.add_message(message_obj)  # pylint: disable=no-member
            else:
                # Old format: {"role": ..., "content": ...}
                memory.chat_memory.add_message(# pylint: disable=no-member
                    {
                        "role": msg.get("role", "human"),
                        "content": msg.get("content", ""),
                    }
                )

        _sessions[session_id] = {
            "memory": memory,
            "last_accessed": datetime.now()
        }

        return memory

async def get_session_async(session_id: str) -> Optional[ConversationBufferMemory]:
    """
    Async wrapper for get_session to prevent event loop blocking.
    """
    return await asyncio.to_thread(get_session, session_id)


def _message_to_dict(message) -> dict:
    """
    Convert a LangChain message (HumanMessage, AIMessage, etc.) to a JSON-serializable dict.

    Args:
        message: A LangChain message object (HumanMessage, AIMessage, etc.)

    Returns:
        dict: A dictionary with 'type' and 'data' keys representing the message.
    """
    # Use the message's type name and convert content/data to dict
    return {
        "type": type(message).__name__,
        "data": {
            "content": message.content,
            "additional_kwargs": message.additional_kwargs,
        }
    }


def persist_session(session_id: str)-> None:
    """
    Persist the current session messages to disk.

    Args:
        session_id (str): The session identifier.
    """
    session_data = get_session(session_id)
    if session_data:
        messages = list(session_data.chat_memory.messages)
        # Convert messages to JSON-serializable dicts before persisting
        serializable_messages = [_message_to_dict(msg) for msg in messages]
        append_message(session_id, serializable_messages)



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

def get_last_accessed(session_id: str) -> Optional[datetime]:
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
