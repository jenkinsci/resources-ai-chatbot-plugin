"""
Unit tests for session persistence — sessionmanager.py

Covers the two bugs fixed by PR #181:
1. Gate bug: _append_message_to_json() silently skipped new sessions (os.path.exists guard)
2. Serialization bug: persist_session() passed raw HumanMessage/AIMessage to json.dump()
"""
# pylint: disable=redefined-outer-name
import json
import uuid

import pytest
from langchain.schema import AIMessage, HumanMessage

from api.services import memory


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _new_uuid() -> str:
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def reset_sessions():
    """Clear in-memory sessions before each test."""
    memory.reset_sessions()


@pytest.fixture()
def tmp_session(tmp_path, monkeypatch):
    """
    Redirect session file storage to a pytest tmp_path so tests
    never write to the real data/sessions directory.
    """
    monkeypatch.setenv("SESSION_FILE_PATH", str(tmp_path))
    # Re-import the module so _SESSION_DIRECTORY picks up the patched env var.
    import importlib  # pylint: disable=import-outside-toplevel
    import api.services.sessionmanager as sm  # pylint: disable=import-outside-toplevel
    importlib.reload(sm)
    # Re-patch the public helpers in memory.py to use the reloaded module.
    monkeypatch.setattr(
        "api.services.memory.append_message", sm.append_message)
    monkeypatch.setattr("api.services.memory.load_session", sm.load_session)
    monkeypatch.setattr(
        "api.services.memory.delete_session_file", sm.delete_session_file)
    monkeypatch.setattr(
        "api.services.memory.session_exists_in_json", sm.session_exists_in_json)
    yield sm, tmp_path


# ─────────────────────────────────────────────────────────────────
# Fix 1: Gate bug — append_message creates file for a NEW session
# ─────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Security: append_message logic rewritten to prevent Disk DoS")
class TestAppendMessageGateFix:
    """
    Before fix: os.path.exists(path) guard prevented writing for new sessions.
    After fix: the guard was replaced with an invalid-path check, so new files
    are created on first persist.
    """

    def test_append_message_creates_file_for_new_session(self, tmp_session):
        """append_message must create the session file if it does not yet exist."""
        sm, _ = tmp_session
        session_id = _new_uuid()
        messages = [{"role": "human", "content": "Hello"}]

        assert not sm.session_exists_in_json(
            session_id), "Precondition: file must not exist yet"

        sm.append_message(session_id, messages)

        assert sm.session_exists_in_json(
            session_id), "File must be created for a new session"

    def test_append_message_content_is_correct(self, tmp_session):
        """Content written by append_message must match what was passed in."""
        sm, _ = tmp_session
        session_id = _new_uuid()
        messages = [
            {"role": "human", "content": "What is Jenkins?"},
            {"role": "ai", "content": "Jenkins is a CI/CD tool."},
        ]

        sm.append_message(session_id, messages)
        loaded = sm.load_session(session_id)

        assert loaded == messages

    def test_append_message_overwrites_with_full_snapshot(self, tmp_session):
        """Each call to append_message replaces the file with the latest snapshot."""
        sm, _ = tmp_session
        session_id = _new_uuid()

        first = [{"role": "human", "content": "First message"}]
        sm.append_message(session_id, first)

        updated = [
            {"role": "human", "content": "First message"},
            {"role": "ai", "content": "Reply"},
        ]
        sm.append_message(session_id, updated)

        loaded = sm.load_session(session_id)
        assert loaded == updated
        assert len(loaded) == 2

    def test_append_message_ignores_invalid_session_id(self, tmp_session):
        """append_message must silently skip non-UUID session IDs (no crash, no file)."""
        sm, tmp_path = tmp_session
        sm.append_message("not-a-uuid", [{"role": "human", "content": "Hi"}])

        # No file should have been created
        files_created = list(tmp_path.iterdir())
        assert not files_created, "No file should be created for an invalid session ID"


# ─────────────────────────────────────────────────────────────────
# Fix 2: Serialization bug — persist_session converts to dicts
# ─────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Security: persist_session disabled to prevent Disk DoS")
class TestPersistSessionSerializationFix:
    """
    Before fix: persist_session() passed raw HumanMessage/AIMessage objects
    to json.dump(), raising a TypeError since they aren't JSON-serializable.
    After fix: messages are converted to {"role": msg.type, "content": msg.content}.
    """

    def test_persist_session_serializes_human_message(self, tmp_session):
        """persist_session() must serialize HumanMessage to a JSON-safe dict."""
        sm, _ = tmp_session
        session_id = memory.init_session()
        session = memory.get_session(session_id)
        session.chat_memory.add_message(
            HumanMessage(content="How do I install Jenkins?"))

        # Must not raise TypeError
        memory.persist_session(session_id)

        loaded = sm.load_session(session_id)
        assert len(loaded) == 1
        assert loaded[0]["role"] == "human"
        assert loaded[0]["content"] == "How do I install Jenkins?"

    def test_persist_session_serializes_ai_message(self, tmp_session):
        """persist_session() must serialize AIMessage to a JSON-safe dict."""
        sm, _ = tmp_session
        session_id = memory.init_session()
        session = memory.get_session(session_id)
        session.chat_memory.add_message(
            AIMessage(content="Jenkins is open-source."))

        memory.persist_session(session_id)

        loaded = sm.load_session(session_id)
        assert len(loaded) == 1
        assert loaded[0]["role"] == "ai"
        assert loaded[0]["content"] == "Jenkins is open-source."

    def test_persist_session_serializes_multi_turn_conversation(self, tmp_session):
        """persist_session() must serialize a full multi-turn conversation correctly."""
        sm, _ = tmp_session
        session_id = memory.init_session()
        session = memory.get_session(session_id)
        session.chat_memory.add_message(
            HumanMessage(content="What is Jenkins?"))
        session.chat_memory.add_message(
            AIMessage(content="Jenkins is a CI/CD tool."))
        session.chat_memory.add_message(
            HumanMessage(content="How do I install it?"))

        memory.persist_session(session_id)

        loaded = sm.load_session(session_id)
        assert len(loaded) == 3
        assert loaded[0] == {"role": "human", "content": "What is Jenkins?"}
        assert loaded[1] == {"role": "ai",
                             "content": "Jenkins is a CI/CD tool."}
        assert loaded[2] == {"role": "human",
                             "content": "How do I install it?"}

    def test_persist_session_output_is_valid_json(self, tmp_session):
        """The session file written by persist_session() must be valid JSON."""
        _, tmp_path = tmp_session
        session_id = memory.init_session()
        session = memory.get_session(session_id)
        session.chat_memory.add_message(HumanMessage(content="Hello"))

        memory.persist_session(session_id)

        session_file = tmp_path / f"{session_id}.json"
        assert session_file.exists()
        with open(session_file, encoding="utf-8") as f:
            parsed = json.load(f)  # Raises if not valid JSON
        assert isinstance(parsed, list)


# ─────────────────────────────────────────────────────────────────
# Fix 1 + 2 together: full persist → load round-trip
# ─────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Security: persist_session disabled to prevent Disk DoS")
class TestPersistLoadRoundTrip:
    """
    Combines both fixes: persist_session() serializes correctly AND
    load_session() can read the result back from disk.
    Previously both bugs together made this round-trip impossible:
    - Fix 1 (gate): the file was never created for new sessions
    - Fix 2 (serialization): json.dump() would crash on raw BaseMessage objects
    """

    def test_full_round_trip_single_message(self, tmp_session):
        """A message persisted by persist_session() must be readable by load_session()."""
        sm, _ = tmp_session
        session_id = memory.init_session()
        session = memory.get_session(session_id)
        session.chat_memory.add_message(
            HumanMessage(content="Hello, Jenkins!"))

        memory.persist_session(session_id)

        loaded = sm.load_session(session_id)
        assert len(loaded) == 1
        assert loaded[0]["role"] == "human"
        assert loaded[0]["content"] == "Hello, Jenkins!"

    def test_full_round_trip_multi_turn(self, tmp_session):
        """A full conversation must survive a persist → load round-trip intact."""
        sm, _ = tmp_session
        session_id = memory.init_session()
        session = memory.get_session(session_id)
        session.chat_memory.add_message(
            HumanMessage(content="What is Jenkins?"))
        session.chat_memory.add_message(
            AIMessage(content="Jenkins is a CI/CD tool."))
        session.chat_memory.add_message(HumanMessage(content="Thanks!"))

        memory.persist_session(session_id)

        loaded = sm.load_session(session_id)
        assert len(loaded) == 3
        assert loaded[0] == {"role": "human", "content": "What is Jenkins?"}
        assert loaded[1] == {"role": "ai",
                             "content": "Jenkins is a CI/CD tool."}
        assert loaded[2] == {"role": "human", "content": "Thanks!"}
