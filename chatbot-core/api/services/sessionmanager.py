"""Session management utilities."""
import os
import json
import uuid
from datetime import datetime
from threading import Lock


_SESSION_DIRECTORY = os.getenv("SESSION_FILE_PATH", "data/sessions")

os.makedirs(_SESSION_DIRECTORY, mode=0o755, exist_ok=True)

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


def _get_session_metadata_path(session_id: str) -> str:
    """
    Returns the full path for a session metadata file.
    Example: data/sessions/<session_id>.metadata.json
    """
    try:
        uuid.UUID(session_id)
    except ValueError:
        return ""
    return os.path.join(_SESSION_DIRECTORY, f"{session_id}.metadata.json")


def _load_session_from_json(session_id: str) -> list:
    """
    Load a session's history from disk.
    """
    path = _get_session_file_path(session_id)
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _append_message_to_json(session_id: str, messages: list) -> None:
    """
    Persist the current session messages as a full snapshot using atomic write.
    """
    path = _get_session_file_path(session_id)
    if os.path.exists(path):
        tmp_path = f"{path}.tmp"

        with _FILE_LOCK:

            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)

            os.replace(tmp_path, path)


def _delete_session(session_id: str) -> bool:
    """
    Delete the persisted session file and metadata.
    """
    path = _get_session_file_path(session_id)
    metadata_path = _get_session_metadata_path(session_id)

    with _FILE_LOCK:
        deleted = False
        if os.path.exists(path):
            os.remove(path)
            deleted = True
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
            deleted = True
    return deleted


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


def save_session_metadata(session_id: str, user_id: str) -> None:
    """
    Save session metadata (user_id, created_at) to a metadata file.

    Args:
        session_id (str): The session identifier.
        user_id (str): The Jenkins user ID.
    """
    metadata_path = _get_session_metadata_path(session_id)
    if not metadata_path:
        return

    metadata = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "session_id": session_id
    }

    with _FILE_LOCK:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)


def load_session_metadata(session_id: str) -> dict | None:
    """
    Load session metadata from the metadata file.

    Args:
        session_id (str): The session identifier.

    Returns:
        dict | None: The metadata dict if found, else None.
    """
    metadata_path = _get_session_metadata_path(session_id)
    if not metadata_path or not os.path.exists(metadata_path):
        return None

    with _FILE_LOCK:
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
