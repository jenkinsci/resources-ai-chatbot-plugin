"""
E2E lifecycle scenarios for the chatbot API - Part 2 of 2.

Depends on scaffolding from #193 (PR #201). This file will not
import-resolve until PR #201 lands on main and is intentionally
left as a Draft PR until that happens.

Scenarios
---------
1. test_session_survives_restart      xfail - blocked by #175
2. test_websocket_stream_persists     xfail - blocked by #173
3. test_upload_without_message_returns_200  passing - validates #184
4. test_agentic_pipeline_no_type_error      passing - validates #189/#190
5. test_upload_unknown_session_returns_404  passing - Python-layer gate for #168
"""

import json
from pathlib import Path

import pytest


@pytest.mark.e2e
class TestChatLifecycle:
    """Lifecycle E2E checks for session, upload, and streaming paths."""

    # ------------------------------------------------------------------
    # 1. Session survival across in-memory reset (xfail #175)
    # ------------------------------------------------------------------
    @pytest.mark.xfail(
        strict=False,
        reason="Blocked by #175: session_exists() only checks in-memory store.",
    )
    def test_session_survives_restart(self, e2e_client, session_data_dir):
        """Session persisted to disk must be accessible after in-memory wipe.

        Note: #180 also affects this path because new sessions are not always
        written to disk, but the primary acceptance gate remains #175.
        """
        import api.services.memory as memory_module  # pylint: disable=import-outside-toplevel

        # Fixture activates isolated session directory monkeypatching from #201.
        assert session_data_dir.exists()

        session_id = e2e_client.post("/sessions").json()["session_id"]
        e2e_client.post(
            f"/sessions/{session_id}/message",
            json={"message": "Hello before restart."},
        )

        # Simulate an in-process restart by wiping only in-memory store.
        memory_module.reset_sessions()

        # session_exists() must fall back to disk for this to return 200.
        resp = e2e_client.post(
            f"/sessions/{session_id}/message",
            json={"message": "Still there?"},
        )
        assert resp.status_code == 200, (
            "Session lost after reset - disk fallback not implemented (#175)."
        )

    # ------------------------------------------------------------------
    # 2. WebSocket path must persist session (xfail #173)
    # ------------------------------------------------------------------
    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Blocked by #173: chatbot_stream() does not call persist_session(), "
            "so WebSocket sessions are never written to disk."
        ),
    )
    def test_websocket_stream_persists(self, e2e_client, session_data_dir):
        """After a WebSocket exchange the session file must exist on disk."""
        session_id = e2e_client.post("/sessions").json()["session_id"]

        with e2e_client.websocket_connect(f"/sessions/{session_id}/stream") as ws:
            ws.send_text(json.dumps({"message": "Stream this."}))
            while True:
                frame = json.loads(ws.receive_text())
                if frame.get("end"):
                    break

        expected_file = session_data_dir / f"{session_id}.json"
        assert expected_file.exists(), (
            f"No session file at {expected_file}. "
            "WebSocket handler skips persist_session() - tracked in #173."
        )

    # ------------------------------------------------------------------
    # 3. File-only upload (no message) must return 200 - validates #184
    # ------------------------------------------------------------------
    def test_upload_without_message_returns_200(self, e2e_client):
        """POST /message/upload with files and empty message must return 200."""
        session_id = e2e_client.post("/sessions").json()["session_id"]
        sample = Path(__file__).parent / "fixtures" / "sample.txt"

        with sample.open("rb") as fixture_file:
            resp = e2e_client.post(
                f"/sessions/{session_id}/message/upload",
                data={"message": ""},
                files={"files": ("sample.txt", fixture_file, "text/plain")},
            )

        assert resp.status_code == 200, (
            f"Expected 200 for file-only upload, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert "reply" in data
        assert isinstance(data["reply"], str)
        assert len(data["reply"]) > 0

    # ------------------------------------------------------------------
    # 4. Chat endpoint must not produce TypeError - validates #189/#190
    # ------------------------------------------------------------------
    def test_agentic_pipeline_no_type_error(self, e2e_client):
        """The chat pipeline must not raise TypeError on LLM output."""
        session_id = e2e_client.post("/sessions").json()["session_id"]

        resp = e2e_client.post(
            f"/sessions/{session_id}/message",
            json={"message": "Explain Jenkins distributed builds."},
        )

        assert resp.status_code == 200, (
            f"Pipeline returned {resp.status_code} - possible TypeError: {resp.text}"
        )
        data = resp.json()
        assert "reply" in data
        assert isinstance(data["reply"], str), (
            "reply is not a string - non-string LLM output propagated."
        )

    # ------------------------------------------------------------------
    # 5. Upload to unknown session must return 404 - Python gate for #168
    # ------------------------------------------------------------------
    def test_upload_unknown_session_returns_404(self, e2e_client):
        """POST /message/upload to a non-existent session must return 404.

        This validates the Python-layer session existence gate. Full ownership
        isolation (user A cannot upload to user B session) requires user_id
        propagation via Java Gatekeeper and is intentionally out of scope here.
        """
        sample = Path(__file__).parent / "fixtures" / "sample.txt"
        phantom_session = "00000000-0000-0000-0000-000000000000"

        with sample.open("rb") as fixture_file:
            resp = e2e_client.post(
                f"/sessions/{phantom_session}/message/upload",
                data={"message": "Attempt cross-session upload."},
                files={"files": ("sample.txt", fixture_file, "text/plain")},
            )

        assert resp.status_code == 404, (
            "Expected 404 for upload to non-existent session, "
            f"got {resp.status_code}."
        )
