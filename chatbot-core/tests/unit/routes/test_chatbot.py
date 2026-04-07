"""Unit Tests for FastAPI routes."""

def test_start_chat(client, mock_init_session):
    """Testing that creating a session returns session ID and location."""
    mock_init_session.return_value = "test-session-id"

    response = client.post("/sessions")

    assert response.status_code == 201
    assert response.json() == {"session_id": "test-session-id"}
    assert response.headers["location"] == "/sessions/test-session-id/message"


def test_chatbot_reply_success(client, mock_session_exists, mock_get_chatbot_reply):
    """Testing that sending a valid message in a valid session returns a response."""
    mock_session_exists.return_value = True
    mock_get_chatbot_reply.return_value = {"reply": "This is a valid response"}
    data = {"message": "This is a valid query"}

    response = client.post("/sessions/test-session-id/message", json=data)

    assert response.status_code == 200
    assert response.json() == {"reply": "This is a valid response"}


def test_chatbot_reply_invalid_session(client, mock_session_exists):
    """Testing that sending a message to an invalid session returns 404."""
    mock_session_exists.return_value = False
    data = {"message": "This is a valid query"}

    response = client.post("/sessions/invalid-session-id/message", json=data)

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found."}


def test_chatbot_reply_empty_message_returns_422(client, mock_session_exists):
    """Testing that if sending an empty message returns 422 validation error."""
    mock_session_exists.return_value = True
    data = {"message": "   "}
    response = client.post("/sessions/test-session-id/message", json=data)

    errors = response.json()["detail"]

    assert response.status_code == 422
    assert "Message cannot be empty." in errors[0]["msg"]


def test_delete_chat_success(client, mock_delete_session):
    """Testing that deleting an existing session returns confirmation."""
    mock_delete_session.return_value = True

    response = client.delete("/sessions/test-session-id")

    assert response.status_code == 200
    assert response.json() == {"message": "Session test-session-id deleted."}


def test_delete_chat_not_found(client, mock_delete_session):
    """Testing that deleting a session that does not exist returns 404."""
    mock_delete_session.return_value = False

    response = client.delete("/sessions/nonexistent-id")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found."}
