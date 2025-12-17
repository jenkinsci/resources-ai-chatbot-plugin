"""Unit tests for file upload routes."""

import pytest
from io import BytesIO
from fastapi.testclient import TestClient


def test_get_supported_extensions(client, mock_session_exists):
    """Test GET /files/supported-extensions endpoint."""
    response = client.get("/files/supported-extensions")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "text" in data
    assert "image" in data
    assert "max_text_size_mb" in data
    assert "max_image_size_mb" in data
    assert ".txt" in data["text"]
    assert ".png" in data["image"]


def test_chatbot_reply_with_text_file(client, mock_session_exists, mock_get_chatbot_reply):
    """Test POST /sessions/{session_id}/message/upload with text file."""
    mock_session_exists.return_value = True
    mock_get_chatbot_reply.return_value = {"reply": "I analyzed the file."}
    
    # Create a mock text file
    file_content = b"print('Hello, World!')"
    files = [
        ("files", ("script.py", BytesIO(file_content), "text/plain"))
    ]
    
    response = client.post(
        "/sessions/test-session-id/message/upload",
        data={"message": "What does this code do?"},
        files=files
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data


def test_chatbot_reply_with_image_file(client, mock_session_exists, mock_get_chatbot_reply):
    """Test POST /sessions/{session_id}/message/upload with image file."""
    mock_session_exists.return_value = True
    mock_get_chatbot_reply.return_value = {"reply": "I see an image."}
    
    # Create a mock image file (PNG header)
    file_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    files = [
        ("files", ("screenshot.png", BytesIO(file_content), "image/png"))
    ]
    
    response = client.post(
        "/sessions/test-session-id/message/upload",
        data={"message": "What's in this image?"},
        files=files
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data


def test_chatbot_reply_with_multiple_files(client, mock_session_exists, mock_get_chatbot_reply):
    """Test POST /sessions/{session_id}/message/upload with multiple files."""
    mock_session_exists.return_value = True
    mock_get_chatbot_reply.return_value = {"reply": "I analyzed the files."}
    
    files = [
        ("files", ("file1.txt", BytesIO(b"Content 1"), "text/plain")),
        ("files", ("file2.log", BytesIO(b"Content 2"), "text/plain")),
    ]
    
    response = client.post(
        "/sessions/test-session-id/message/upload",
        data={"message": "Analyze these logs."},
        files=files
    )
    
    assert response.status_code == 200


def test_chatbot_reply_upload_invalid_session(client, mock_session_exists):
    """Test that upload endpoint returns 404 for invalid session."""
    mock_session_exists.return_value = False
    
    files = [
        ("files", ("test.txt", BytesIO(b"content"), "text/plain"))
    ]
    
    response = client.post(
        "/sessions/invalid-session/message/upload",
        data={"message": "Test message"},
        files=files
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found."


def test_chatbot_reply_upload_unsupported_file_type(client, mock_session_exists):
    """Test that upload endpoint rejects unsupported file types."""
    mock_session_exists.return_value = True
    
    files = [
        ("files", ("archive.zip", BytesIO(b"PK..."), "application/zip"))
    ]
    
    response = client.post(
        "/sessions/test-session-id/message/upload",
        data={"message": "Extract this archive."},
        files=files
    )
    
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_chatbot_reply_upload_empty_message_with_files(client, mock_session_exists, mock_get_chatbot_reply):
    """Test that upload endpoint works with empty message if files provided."""
    mock_session_exists.return_value = True
    mock_get_chatbot_reply.return_value = {"reply": "I analyzed the file."}
    
    files = [
        ("files", ("test.txt", BytesIO(b"Content"), "text/plain"))
    ]
    
    response = client.post(
        "/sessions/test-session-id/message/upload",
        data={"message": ""},
        files=files
    )
    
    assert response.status_code == 200


def test_chatbot_reply_upload_no_message_no_files(client, mock_session_exists):
    """Test that upload endpoint rejects empty message with no files."""
    mock_session_exists.return_value = True
    
    response = client.post(
        "/sessions/test-session-id/message/upload",
        data={"message": ""}
    )
    
    assert response.status_code == 422


def test_chatbot_reply_upload_only_files_no_message(client, mock_session_exists, mock_get_chatbot_reply):
    """Test that upload endpoint handles files without message."""
    mock_session_exists.return_value = True
    mock_get_chatbot_reply.return_value = {"reply": "I analyzed the file."}
    
    files = [
        ("files", ("test.txt", BytesIO(b"Content"), "text/plain"))
    ]
    
    # Send with whitespace-only message
    response = client.post(
        "/sessions/test-session-id/message/upload",
        data={"message": "   "},
        files=files
    )
    
    assert response.status_code == 200
