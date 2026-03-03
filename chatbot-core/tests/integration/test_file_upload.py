"""Integration tests for file upload endpoint POST /sessions/{session_id}/message/upload.

Issue #224 — exercises the upload route end-to-end through the real
file_service layer while mocking only the LLM and RAG retrieval.

Conventions follow tests/integration/test_chatbot.py.
"""

from io import BytesIO

import pytest
from pydantic import ValidationError

from api.models.schemas import ChatResponse
from api.services import memory
from api.services.file_service import MAX_TEXT_FILE_SIZE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_memory_sessions():
    """Reset in-memory sessions between tests."""
    memory.reset_sessions()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_session(client):
    """Create a session and return its ID."""
    resp = client.post("/sessions")
    assert resp.status_code == 201
    return resp.json()["session_id"]


def _rag_output():
    """Standard mock return value for get_relevant_documents."""
    return (
        [{"id": "docid", "chunk_text": "Relevant chunk text."}],
        [0.84],
    )


def _png_bytes():
    """Minimal valid PNG magic bytes."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 50


# ---------------------------------------------------------------------------
# Supported extensions endpoint
# ---------------------------------------------------------------------------

def test_get_supported_extensions(client):
    """GET /files/supported-extensions should list accepted types and size limits."""
    resp = client.get("/files/supported-extensions")
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert "image" in data
    assert "max_text_size_mb" in data
    assert "max_image_size_mb" in data
    assert ".txt" in data["text"]
    assert ".png" in data["image"]


# ---------------------------------------------------------------------------
# Text file uploads
# ---------------------------------------------------------------------------

def test_upload_text_file_returns_200_with_valid_schema(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload a .txt file — response must satisfy the ChatResponse schema."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "I analyzed your text file."
    mock_get_relevant_documents.return_value = _rag_output()

    files = [("files", ("notes.txt", BytesIO(b"Build failed at step 3"), "text/plain"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "What does this log say?"},
        files=files,
    )

    assert resp.status_code == 200
    try:
        chat_response = ChatResponse.model_validate(resp.json())
    except ValidationError as exc:
        assert False, f"Response did not match ChatResponse schema: {exc}"
    assert chat_response.reply == "I analyzed your text file."


def test_upload_python_file_returns_200(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload a .py source file — exercises code-file text path."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "Code looks good."
    mock_get_relevant_documents.return_value = _rag_output()

    files = [("files", ("script.py", BytesIO(b"print('hello')"), "text/plain"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Review this code"},
        files=files,
    )

    assert resp.status_code == 200
    assert "reply" in resp.json()


def test_upload_log_file_returns_200(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload a .log file — common Jenkins use-case."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "Log analysis complete."
    mock_get_relevant_documents.return_value = _rag_output()

    log_content = b"ERROR: connection refused\nFATAL: build failed"
    files = [("files", ("build.log", BytesIO(log_content), "text/plain"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Why did this build fail?"},
        files=files,
    )

    assert resp.status_code == 200
    assert resp.json()["reply"] == "Log analysis complete."


def test_upload_jenkinsfile_returns_200(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload a Jenkinsfile — validates pipeline syntax path."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "Pipeline looks valid."
    mock_get_relevant_documents.return_value = _rag_output()

    files = [("files", ("Jenkinsfile", BytesIO(b"pipeline { agent any; stages {} }"), "text/plain"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Validate this Jenkinsfile"},
        files=files,
    )

    assert resp.status_code == 200
    assert "reply" in resp.json()


# ---------------------------------------------------------------------------
# Image file uploads
# ---------------------------------------------------------------------------

def test_upload_png_image_returns_200(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload a .png image — expect 200 with reply."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "I see an image."
    mock_get_relevant_documents.return_value = _rag_output()

    files = [("files", ("diagram.png", BytesIO(_png_bytes()), "image/png"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Describe this diagram"},
        files=files,
    )

    assert resp.status_code == 200
    assert "reply" in resp.json()


# ---------------------------------------------------------------------------
# Multiple files
# ---------------------------------------------------------------------------

def test_upload_multiple_files_all_processed(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload multiple text files at once — all should be processed."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "All files reviewed."
    mock_get_relevant_documents.return_value = _rag_output()

    files = [
        ("files", ("a.py", BytesIO(b"import os"), "text/plain")),
        ("files", ("b.log", BytesIO(b"ERROR: connection refused"), "text/plain")),
    ]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Check these files"},
        files=files,
    )

    assert resp.status_code == 200
    assert resp.json()["reply"] == "All files reviewed."


# ---------------------------------------------------------------------------
# Edge cases — message variants
# ---------------------------------------------------------------------------

def test_upload_files_with_empty_message_returns_200(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Files with empty message — should succeed (files provide context)."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "Analyzed the attached file."
    mock_get_relevant_documents.return_value = _rag_output()

    files = [("files", ("data.log", BytesIO(b"INFO started"), "text/plain"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": ""},
        files=files,
    )

    assert resp.status_code == 200
    assert "reply" in resp.json()


def test_upload_files_with_whitespace_only_message_returns_200(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Files with whitespace-only message — should succeed."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "Analyzed."
    mock_get_relevant_documents.return_value = _rag_output()

    files = [("files", ("data.txt", BytesIO(b"some content"), "text/plain"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "   "},
        files=files,
    )

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_upload_to_nonexistent_session_returns_404(client):
    """Upload to a session that does not exist — expect 404."""
    files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
    resp = client.post(
        "/sessions/nonexistent-id/message/upload",
        data={"message": "Test"},
        files=files,
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found."


def test_upload_empty_message_no_files_returns_422(client):
    """Empty message with no files — expect 422 validation error."""
    session_id = _create_session(client)
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": ""},
    )

    assert resp.status_code == 422


def test_upload_unsupported_file_type_returns_400(client):
    """Upload a .zip file — expect 400 unsupported type."""
    session_id = _create_session(client)
    files = [("files", ("archive.zip", BytesIO(b"PK\x03\x04"), "application/zip"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Extract this"},
        files=files,
    )

    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]


def test_upload_file_too_large_returns_400(client):
    """Upload a text file exceeding MAX_TEXT_FILE_SIZE — expect 400."""
    session_id = _create_session(client)
    large_content = b"x" * (MAX_TEXT_FILE_SIZE + 1)
    files = [("files", ("huge.txt", BytesIO(large_content), "text/plain"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Read this"},
        files=files,
    )

    assert resp.status_code == 400
    assert "exceeds maximum size" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Multi-turn conversation with file upload
# ---------------------------------------------------------------------------

def test_upload_then_text_message_same_session(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload a file then send a plain text message in the same session."""
    session_id = _create_session(client)
    mock_get_relevant_documents.return_value = _rag_output()

    # Turn 1 — upload a file
    mock_llm_provider.generate.return_value = "File received."
    files = [("files", ("build.log", BytesIO(b"ERROR: OOM"), "text/plain"))]
    upload_resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Analyze this log"},
        files=files,
    )
    assert upload_resp.status_code == 200
    assert upload_resp.json()["reply"] == "File received."

    # Turn 2 — plain text follow-up in same session
    mock_llm_provider.generate.return_value = "Here is a fix suggestion."
    text_resp = client.post(
        f"/sessions/{session_id}/message",
        json={"message": "How do I fix it?"},
    )
    assert text_resp.status_code == 200
    assert text_resp.json()["reply"] == "Here is a fix suggestion."


def test_multiple_upload_turns_same_session(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload files across multiple turns in the same session."""
    session_id = _create_session(client)
    mock_get_relevant_documents.return_value = _rag_output()
    mock_llm_provider.generate.side_effect = ["Reply 1", "Reply 2"]

    for i, content in enumerate([b"log line A", b"log line B"]):
        files = [("files", (f"file{i}.log", BytesIO(content), "text/plain"))]
        resp = client.post(
            f"/sessions/{session_id}/message/upload",
            data={"message": f"Analyze file {i}"},
            files=files,
        )
        assert resp.status_code == 200
        assert resp.json()["reply"] == f"Reply {i + 1}"


# ---------------------------------------------------------------------------
# Session isolation
# ---------------------------------------------------------------------------

def test_upload_sessions_are_isolated(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Uploads to different sessions must not interfere with each other."""
    mock_get_relevant_documents.return_value = _rag_output()
    mock_llm_provider.generate.return_value = "Response"

    session_a = _create_session(client)
    session_b = _create_session(client)

    # Upload to A
    files_a = [("files", ("a.txt", BytesIO(b"content A"), "text/plain"))]
    resp_a = client.post(
        f"/sessions/{session_a}/message/upload",
        data={"message": "Check A"},
        files=files_a,
    )
    assert resp_a.status_code == 200

    # Delete B and verify A still works
    client.delete(f"/sessions/{session_b}")

    files_a2 = [("files", ("a2.txt", BytesIO(b"content A2"), "text/plain"))]
    resp_a2 = client.post(
        f"/sessions/{session_a}/message/upload",
        data={"message": "Check A again"},
        files=files_a2,
    )
    assert resp_a2.status_code == 200

    # Upload to deleted B — must 404
    files_b = [("files", ("b.txt", BytesIO(b"content B"), "text/plain"))]
    resp_b = client.post(
        f"/sessions/{session_b}/message/upload",
        data={"message": "Check B"},
        files=files_b,
    )
    assert resp_b.status_code == 404
    assert resp_b.json()["detail"] == "Session not found."


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------

def test_full_lifecycle_create_upload_delete(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Create session -> upload file -> verify reply -> delete -> verify 404."""
    # 1. Create
    session_id = _create_session(client)

    # 2. Upload
    mock_llm_provider.generate.return_value = "File processed successfully."
    mock_get_relevant_documents.return_value = _rag_output()
    files = [("files", ("Jenkinsfile", BytesIO(b"pipeline { }"), "text/plain"))]
    upload_resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Validate this Jenkinsfile"},
        files=files,
    )
    assert upload_resp.status_code == 200
    assert upload_resp.json()["reply"] == "File processed successfully."

    # 3. Delete
    delete_resp = client.delete(f"/sessions/{session_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["message"] == f"Session {session_id} deleted."

    # 4. Verify deleted — upload should 404
    files2 = [("files", ("test.txt", BytesIO(b"hi"), "text/plain"))]
    post_delete_resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Should fail"},
        files=files2,
    )
    assert post_delete_resp.status_code == 404
