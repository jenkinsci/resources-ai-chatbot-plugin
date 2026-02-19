"""Session management utilities."""
import os
import json
import uuid
import logging
from threading import Lock

logger = logging.getLogger(__name__)

_SESSION_DIRECTORY = os.getenv("SESSION_FILE_PATH", "data/sessions")

os.makedirs(_SESSION_DIRECTORY,mode = 0o755, exist_ok=True)

_FILE_LOCK = Lock()


def _get_session_file_path(session_id: str) -> str:
    """
    Returns the full path for a session file.
    Example: data/sessions/<session_id>.json
    """

    try:
        uuid.UUID(session_id)
    except ValueError:
        return ""
    return os.path.join(_SESSION_DIRECTORY, f"{session_id}.json")


def _load_session_from_json(session_id: str) -> list:
    """
    Load a session's history from disk.
    Returns empty list on any error.
    """
    path = _get_session_file_path(session_id)
    if not path or not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Corrupted JSON in session file %s: %s", path, e)
        return []
    except OSError as e:
        logger.error("Failed to read session file %s: %s", path, e)
        return []


def _append_message_to_json(session_id: str, messages:list) -> None:
    """
    Persist the current session messages as a full snapshot using atomic write.
    """
    path = _get_session_file_path(session_id)
    if not path:
        return

    # Create file if it doesn't exist (fixes Issue 3: new sessions never saved)
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump([], f)
        except OSError as e:
            logger.error("Failed to create session file %s: %s", path, e)
            return

    tmp_path = f"{path}.tmp"

    with _FILE_LOCK:
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
        except OSError as e:
            logger.error("Failed to write session file %s: %s", path, e)


def _delete_session(session_id: str) -> bool:
    """
    Delete the persisted session file.
    """
    path = _get_session_file_path(session_id)
    if not path:
        return False

    with _FILE_LOCK:
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
        except OSError as e:
            logger.error("Failed to delete session file %s: %s", path, e)
    return False

def session_exists_in_json(session_id: str) -> bool:
    """
    Check if a session file exists on disk.
    """
    path = _get_session_file_path(session_id)
    return os.path.exists(path)

# Public API functions

def append_message(session_id: str, messages: list) -> None:
    """
    Public function to append messages to a session's JSON file.
    """
    _append_message_to_json(session_id, messages)

def load_session(session_id: str) -> list:
    """
    Public function to load a session's history from its JSON file.
    """
    return _load_session_from_json(session_id)

def delete_session_file(session_id: str) -> bool:
    """
    Public function to delete a session's JSON file.
    """
    return _delete_session(session_id)
