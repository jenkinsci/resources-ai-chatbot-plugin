"""Session management utilities."""
import os
import json
import uuid
from datetime import datetime
from threading import Lock
from typing import List, Optional, Dict



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

def _get_metadata_path(session_id: str) -> str:
    """
    Returns the full path for a session metadata file.
    Example: data/sessions/<session_id>.meta.json
    """
    try:
        uuid.UUID(session_id)
    except ValueError:
        return ""
    return os.path.join(_SESSION_DIRECTORY, f"{session_id}.meta.json")


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
    if os.path.exists(path):
        tmp_path = f"{path}.tmp"

        with _FILE_LOCK:
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(messages, f, indent=2, ensure_ascii=False)

                # Atomic replacement
                    os.replace(tmp_path, path)
            except IOError:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)


def _delete_session(session_id: str) -> bool:
    """
    Delete the persisted session file and its metadata.
    """
    history_path = _get_session_file_path(session_id)
    meta_path = _get_metadata_path(session_id)
    deleted = False

    with _FILE_LOCK:
        if os.path.exists(history_path):
            os.remove(history_path)
            deleted = True

        if os.path.exists(meta_path):
            os.remove(meta_path)
            # Metadata deletion is secondary; we return True if history was deleted

    return deleted

def save_session_metadata(session_id: str, user_id: str, user_name: str = "User") -> None:
    """
    Persist session ownership and details to disk.
    This enables Strict Ownership validation even after server restarts.
    """
    path = _get_metadata_path(session_id)
    if not path:
        return

    data = {
        "owner": user_id,
        "user_name": user_name,
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat()
    }

    with _FILE_LOCK:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except IOError:
            pass

def get_session_metadata(session_id: str) -> Optional[Dict]:
    """
    Load session metadata (owner, created_at, etc.) from disk.
    """
    path = _get_metadata_path(session_id)
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

def get_session_owner(session_id: str) -> Optional[str]:
    """
    Helper to quickly get the owner ID of a session.
    Returns None if session or metadata doesn't exist.
    """
    meta = get_session_metadata(session_id)
    return meta.get("owner") if meta else None

def list_user_sessions(user_id: str) -> List[str]:
    """
    List all session IDs belonging to a specific user.
    Used for enforcing Resource Quotas (Anti-DoS).
    """
    user_sessions = []

    # Scan directory for .meta.json files
    # Note: efficient enough for reasonable numbers of files.
    # For massive scale, a database would be preferred, but this fits the file-based architecture.
    try:
        for filename in os.listdir(_SESSION_DIRECTORY):
            if filename.endswith(".meta.json"):
                session_id = filename.replace(".meta.json", "")
                owner = get_session_owner(session_id)
                if owner == user_id:
                    user_sessions.append(session_id)
    except FileNotFoundError:
        return []

    return user_sessions

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
