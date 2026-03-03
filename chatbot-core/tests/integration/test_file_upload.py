"""Integration tests for file upload endpoint POST /sessions/{session_id}/message/upload.

Issue #224 — exercises the upload route end-to-end through the real
file_service layer while mocking only the LLM and RAG retrieval.
"""

from io import BytesIO

import pytest
from api.services import memory


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


def _get_relevant_documents_output():
    """Standard mock return value for get_relevant_documents."""
    return (
        [{"id": "docid", "chunk_text": "Relevant chunk text."}],
        [0.84],
    )


# ---------------------------------------------------------------------------
# Text file upload
# ---------------------------------------------------------------------------

def test_upload_text_file_returns_200(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload a .txt file to a valid session — expect 200 with reply."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "I analyzed your text file."
    mock_get_relevant_documents.return_value = _get_relevant_documents_output()

    files = [("files", ("notes.txt", BytesIO(b"Build failed at step 3"), "text/plain"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "What does this log say?"},
        files=files,
    )

    assert resp.status_code == 200
    assert resp.json()["reply"] == "I analyzed your text file."


def test_upload_code_file_returns_200(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload a .py file — exercises the code-file text path."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "Code looks good."
    mock_get_relevant_documents.return_value = _get_relevant_documents_output()

    files = [("files", ("script.py", BytesIO(b"print('hello')"), "text/plain"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Review this code"},
        files=files,
    )

    assert resp.status_code == 200
    assert "reply" in resp.json()


# ---------------------------------------------------------------------------
# Image file upload
# ---------------------------------------------------------------------------

def test_upload_image_file_returns_200(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload a .png image to a valid session — expect 200."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "I see an image."
    mock_get_relevant_documents.return_value = _get_relevant_documents_output()

    # Minimal PNG header (magic bytes)
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    files = [("files", ("diagram.png", BytesIO(png_bytes), "image/png"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Describe this diagram"},
        files=files,
    )

    assert resp.status_code == 200
    assert "reply" in resp.json()


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
    """Upload a text file exceeding 5 MB — expect 400 size limit."""
    session_id = _create_session(client)

    large_content = b"x" * (6 * 1024 * 1024)  # 6 MB
    files = [("files", ("huge.txt", BytesIO(large_content), "text/plain"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": "Read this"},
        files=files,
    )

    assert resp.status_code == 400
    assert "exceeds maximum size" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_upload_files_only_no_message(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload files with empty message — should succeed with default prompt."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "Analyzed the attached file."
    mock_get_relevant_documents.return_value = _get_relevant_documents_output()

    files = [("files", ("data.log", BytesIO(b"INFO started"), "text/plain"))]
    resp = client.post(
        f"/sessions/{session_id}/message/upload",
        data={"message": ""},
        files=files,
    )

    assert resp.status_code == 200
    assert "reply" in resp.json()


def test_upload_multiple_files(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Upload multiple text files at once — all should be processed."""
    session_id = _create_session(client)
    mock_llm_provider.generate.return_value = "All files reviewed."
    mock_get_relevant_documents.return_value = _get_relevant_documents_output()

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
# Full lifecycle
# ---------------------------------------------------------------------------

def test_full_lifecycle_create_upload_delete(
    client, mock_llm_provider, mock_get_relevant_documents
):
    """Create session -> upload file -> verify reply -> delete session."""
    # 1. Create
    session_id = _create_session(client)

    # 2. Upload
    mock_llm_provider.generate.return_value = "File processed successfully."
    mock_get_relevant_documents.return_value = _get_relevant_documents_output()

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
