"""Unit tests for file-based session persistence logic."""

import json
import os
import uuid

import pytest

from api.services import sessionmanager


@pytest.fixture(autouse=True)
def use_tmp_session_dir(tmp_path, monkeypatch):
    """Redirect _SESSION_DIRECTORY to a temp folder for every test."""
    monkeypatch.setattr(sessionmanager, "_SESSION_DIRECTORY", str(tmp_path))


def _create_session_file(tmp_dir, session_id, messages):
    """Helper: write a session JSON file to the given directory."""
    path = os.path.join(str(tmp_dir), f"{session_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f)


# --- load_session ---


def test_load_session_existing_file(tmp_path):
    """Test that load_session returns messages from an existing file."""
    sid = str(uuid.uuid4())
    messages = [{"role": "user", "content": "hello"}]
    _create_session_file(tmp_path, sid, messages)

    result = sessionmanager.load_session(sid)

    assert result == messages


def test_load_session_missing_file():
    """Test that load_session returns an empty list when no file exists."""
    sid = str(uuid.uuid4())

    result = sessionmanager.load_session(sid)

    assert result == []


def test_load_session_invalid_uuid():
    """Test that load_session returns an empty list for an invalid UUID."""
    result = sessionmanager.load_session("not-a-uuid")

    assert result == []


# --- append_message ---


def test_append_message_overwrites_existing_file(tmp_path):
    """Test that append_message overwrites an existing session file."""
    sid = str(uuid.uuid4())
    _create_session_file(tmp_path, sid, [{"role": "user", "content": "old"}])

    new_messages = [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "new reply"},
    ]
    sessionmanager.append_message(sid, new_messages)

    result = sessionmanager.load_session(sid)
    assert result == new_messages


def test_append_message_skips_when_file_missing():
    """Test that append_message does nothing when the file does not exist."""
    sid = str(uuid.uuid4())

    sessionmanager.append_message(sid, [{"role": "user", "content": "hello"}])

    # File should still not exist
    assert not sessionmanager.session_exists_in_json(sid)


# --- delete_session_file ---


def test_delete_session_file_existing(tmp_path):
    """Test that delete_session_file removes an existing file and returns True."""
    sid = str(uuid.uuid4())
    _create_session_file(tmp_path, sid, [])

    deleted = sessionmanager.delete_session_file(sid)

    assert deleted is True
    assert not sessionmanager.session_exists_in_json(sid)


def test_delete_session_file_missing():
    """Test that delete_session_file returns False when the file does not exist."""
    sid = str(uuid.uuid4())

    deleted = sessionmanager.delete_session_file(sid)

    assert deleted is False


# --- session_exists_in_json ---


def test_session_exists_in_json_true(tmp_path):
    """Test that session_exists_in_json returns True when a file exists."""
    sid = str(uuid.uuid4())
    _create_session_file(tmp_path, sid, [])

    assert sessionmanager.session_exists_in_json(sid) is True


def test_session_exists_in_json_false():
    """Test that session_exists_in_json returns False when no file exists."""
    sid = str(uuid.uuid4())

    assert sessionmanager.session_exists_in_json(sid) is False
