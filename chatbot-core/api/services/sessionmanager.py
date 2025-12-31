import os
import json
import uuid
from threading import Lock



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
    """
    path = _get_session_file_path(session_id)
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _append_message_to_json(session_id: str, messages:list) -> None:
    """
    Persist the current session messages as a full snapshot using atomic write.
    """
    path = _get_session_file_path(session_id)
    tmp_path = f"{path}.tmp"

    with _FILE_LOCK:

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)

        os.replace(tmp_path, path)


def _delete_session(session_id: str) -> bool:
    """
    Delete the persisted session file.
    """
    path = _get_session_file_path(session_id)

    with _FILE_LOCK:
        if os.path.exists(path):
            os.remove(path)
            return True
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
