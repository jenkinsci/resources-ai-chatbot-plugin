"""Unit tests for file upload routes."""

from io import BytesIO

import pytest

TEST_HEADERS = {
    "X-Jenkins-User-ID": "test-user",
    "X-Jenkins-User-Name": "Test User"
}

@pytest.fixture(autouse=True)
def auto_mock_validate_session_access(mocker):
    """Mock the ownership check to always say 'Yes, this session belongs to test-user'."""
    return mocker.patch("api.routes.chatbot.validate_session_access", return_value="test-user")

def test_get_supported_extensions(client):
    """Test GET /files/supported-extensions endpoint."""
    response = client.get("/files/supported-extensions", headers=TEST_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert "text" in data
    assert "image" in data
    assert "max_text_size_mb" in data
    assert "max_image_size_mb" in data
    assert ".txt" in data["text"]
    assert ".png" in data["image"]


def test_chatbot_reply_with_text_file(
    client, mock_session_exists, mock_get_chatbot_reply
):
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
        files=files, headers=TEST_HEADERS
    )

    assert response.status_code == 200
    data = response.json()
    assert "reply" in data

    # Verify the service layer received correctly processed data
    mock_get_chatbot_reply.assert_called_once()
    args, _ = mock_get_chatbot_reply.call_args
    assert args[2][0].filename == "script.py"
    assert "print('Hello, World!')" in args[2][0].content


def test_chatbot_reply_with_image_file(
    client, mock_session_exists, mock_get_chatbot_reply
):
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
        files=files, headers=TEST_HEADERS
    )

    assert response.status_code == 200
    data = response.json()
    assert "reply" in data


def test_chatbot_reply_with_multiple_files(
    client, mock_session_exists, mock_get_chatbot_reply
):
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
        files=files, headers=TEST_HEADERS
    )

    assert response.status_code == 200

    # Verify both files were processed and passed to service
    mock_get_chatbot_reply.assert_called_once()
    args, _ = mock_get_chatbot_reply.call_args
    assert len(args[2]) == 2
    filenames = [f.filename for f in args[2]]
    assert "file1.txt" in filenames
    assert "file2.log" in filenames


def test_chatbot_reply_upload_invalid_session(client, mock_session_exists):
    """Test that upload endpoint returns 404 for invalid session."""
    mock_session_exists.return_value = False

    files = [
        ("files", ("test.txt", BytesIO(b"content"), "text/plain"))
    ]

    response = client.post(
        "/sessions/invalid-session/message/upload",
        data={"message": "Test message"},
        files=files, headers=TEST_HEADERS
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
        files=  files, headers=TEST_HEADERS
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_chatbot_reply_upload_empty_message_with_files(
    client, mock_session_exists, mock_get_chatbot_reply
):
    """Test that upload endpoint works with empty message if files provided."""
    mock_session_exists.return_value = True
    mock_get_chatbot_reply.return_value = {"reply": "I analyzed the file."}

    files = [
        ("files", ("test.txt", BytesIO(b"Content"), "text/plain"))
    ]

    response = client.post(
        "/sessions/test-session-id/message/upload",
        data={"message": ""},
        files=files, headers=TEST_HEADERS
    )

    assert response.status_code == 200


def test_chatbot_reply_upload_no_message_no_files(client, mock_session_exists):
    """Test that upload endpoint rejects empty message with no files."""
    mock_session_exists.return_value = True

    response = client.post(
        "/sessions/test-session-id/message/upload",
        data={"message": ""}, headers=TEST_HEADERS
    )

    assert response.status_code == 422


def test_chatbot_reply_upload_only_files_no_message(
    client, mock_session_exists, mock_get_chatbot_reply
):
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
        files=files, headers=TEST_HEADERS
    )

    assert response.status_code == 200


def test_chatbot_reply_upload_file_too_large(client, mock_session_exists):
    """Test that upload endpoint rejects files exceeding size limit."""
    mock_session_exists.return_value = True

    # Create content larger than MAX_TEXT_FILE_SIZE (5MB)
    large_content = b"x" * (6 * 1024 * 1024)  # 6MB
    files = [
        ("files", ("large.txt", BytesIO(large_content), "text/plain"))
    ]

    response = client.post(
        "/sessions/test-session-id/message/upload",
        data={"message": "Process this file"},
        files=files, headers=TEST_HEADERS
    )

    assert response.status_code == 400
    assert "exceeds maximum size" in response.json()["detail"]


def test_chatbot_reply_text_truncation(
    client, mock_session_exists, mock_get_chatbot_reply
):
    """Test that text content is truncated when exceeding limit."""
    mock_session_exists.return_value = True
    mock_get_chatbot_reply.return_value = {"reply": "Analyzed truncated content."}

    # Create content larger than MAX_TEXT_CONTENT_LENGTH (10000 chars)
    large_text = "x" * 15000
    files = [
        ("files", ("large_text.txt", BytesIO(large_text.encode()), "text/plain"))
    ]

    response = client.post(
        "/sessions/test-session-id/message/upload",
        data={"message": "Analyze this"},
        files=files, headers=TEST_HEADERS
    )

    assert response.status_code == 200

    # Verify that truncated content was passed to the service
    mock_get_chatbot_reply.assert_called_once()
    args, _ = mock_get_chatbot_reply.call_args
    assert args[2][0].filename == "large_text.txt"
    # Content should be truncated to MAX_TEXT_CONTENT_LENGTH (10000)
    assert len(args[2][0].content) <= 10000 + 50  # Allow for truncation message
