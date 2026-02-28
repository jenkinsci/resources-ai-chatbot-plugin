"""
E2E smoke test — create session → send message → assert disk persistence.

This test exercises the full production call chain with only inference
swapped out (via ``StubLLMProvider``):

    POST /sessions  →  init_session()
    POST /sessions/{id}/message  →  get_chatbot_reply()
        → retrieve_context() [dev_mode placeholder]
        → build_prompt()
        → StubLLMProvider.generate()
        → memory.add_message()
    BackgroundTask  →  persist_session()  →  sessionmanager.append_message()

The disk-write assertion is marked ``xfail`` because of a known bug:
``_append_message_to_json()`` only writes when the file already exists,
so new sessions never get persisted.  See #180.
"""

import uuid

import pytest


@pytest.mark.e2e
class TestSmoke:
    """Minimal E2E smoke tests for the chatbot API."""

    def test_create_session_returns_201(self, e2e_client):
        """POST /sessions should return 201 with a session_id."""
        resp = e2e_client.post("/sessions")

        assert resp.status_code == 201
        data = resp.json()
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0
        uuid.UUID(data["session_id"])

    def test_send_message_returns_reply(self, e2e_client, stub_llm):
        """POST /sessions/{id}/message should return 200 with a reply."""
        session_id = e2e_client.post("/sessions").json()["session_id"]

        resp = e2e_client.post(
            f"/sessions/{session_id}/message",
            json={"message": "What is Jenkins?"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert isinstance(data["reply"], str)
        assert len(data["reply"]) > 0
        # StubLLMProvider should have been called exactly once
        assert stub_llm.call_count == 1

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Blocked by #180: _append_message_to_json() only writes when "
            "the file already exists, so new sessions are never persisted."
        ),
    )
    def test_session_persisted_to_disk(self, e2e_client, session_data_dir):
        """After sending a message the session file should exist on disk.

        The full chain is:
            chatbot_reply() → BackgroundTask(persist_session) →
            sessionmanager.append_message() → write JSON file

        ``TestClient`` as a context manager flushes ``BackgroundTasks``
        on ``__exit__`` of the ``with`` block.
        """
        session_id = e2e_client.post("/sessions").json()["session_id"]

        e2e_client.post(
            f"/sessions/{session_id}/message",
            json={"message": "Explain Jenkins pipelines."},
        )

        # The session file should now exist in the temp sessions dir
        expected_file = session_data_dir / f"{session_id}.json"
        assert expected_file.exists(), (
            f"Session file was not written to {expected_file}. "
            "This is the known bug tracked in #180."
        )
