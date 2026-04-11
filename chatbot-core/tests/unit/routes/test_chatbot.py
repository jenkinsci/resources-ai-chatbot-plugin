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


# =========================
# WebSocket Tests
# =========================

def test_websocket_malformed_json_returns_error_and_stays_alive(
    client, mock_session_exists, mock_get_chatbot_reply_stream
):
    """Malformed JSON must return an error message without closing the connection.

    Before fix: a single bad message like 'hello' would propagate to the
    outer except block and terminate the WebSocket connection entirely.
    After fix: the handler catches json.JSONDecodeError, sends an error
    JSON, and continues listening.
    """
    mock_session_exists.return_value = True

    async def fake_stream(_session_id, _message):
        yield "reply-token"

    mock_get_chatbot_reply_stream.side_effect = fake_stream

    with client.websocket_connect("/sessions/test-session-id/stream") as ws:
        # Send malformed JSON
        ws.send_text("not valid json")
        error_response = ws.receive_json()
        assert error_response == {"error": "Invalid JSON format."}

        # Connection is still alive - send a valid message
        ws.send_json({"message": "Hello"})
        token_response = ws.receive_json()
        assert "token" in token_response
        end_response = ws.receive_json()
        assert end_response == {"end": True}


def test_websocket_valid_json_streams_response(
    client, mock_session_exists, mock_get_chatbot_reply_stream
):
    """A valid JSON message must produce streaming tokens followed by end marker."""
    mock_session_exists.return_value = True

    async def fake_stream(_session_id, _message):
        yield "Hello"
        yield " world"

    mock_get_chatbot_reply_stream.side_effect = fake_stream

    with client.websocket_connect("/sessions/test-session-id/stream") as ws:
        ws.send_json({"message": "What is Jenkins?"})

        token1 = ws.receive_json()
        assert token1 == {"token": "Hello"}
        token2 = ws.receive_json()
        assert token2 == {"token": " world"}
        end = ws.receive_json()
        assert end == {"end": True}


def test_websocket_empty_message_is_skipped(
    client, mock_session_exists, mock_get_chatbot_reply_stream
):
    """An empty message field must be silently skipped without error."""
    mock_session_exists.return_value = True

    async def fake_stream(_session_id, _message):
        yield "response"

    mock_get_chatbot_reply_stream.side_effect = fake_stream

    with client.websocket_connect("/sessions/test-session-id/stream") as ws:
        # Send valid JSON with empty message - should be skipped
        ws.send_json({"message": ""})

        # Send a real message to prove connection is still alive
        ws.send_json({"message": "Real question"})
        token = ws.receive_json()
        assert token == {"token": "response"}
        end = ws.receive_json()
        assert end == {"end": True}


def test_websocket_non_object_json_returns_error_and_stays_alive(
    client, mock_session_exists, mock_get_chatbot_reply_stream
):
    """Non-object JSON payloads should return a validation error and keep socket open."""
    mock_session_exists.return_value = True

    async def fake_stream(_session_id, _message):
        yield "ok"

    mock_get_chatbot_reply_stream.side_effect = fake_stream

    with client.websocket_connect("/sessions/test-session-id/stream") as ws:
        ws.send_text("[\"not\", \"an\", \"object\"]")
        error_response = ws.receive_json()
        assert error_response == {"error": "Invalid message payload. Expected JSON object."}

        ws.send_json({"message": "Real question"})
        token = ws.receive_json()
        assert token == {"token": "ok"}
        end = ws.receive_json()
        assert end == {"end": True}


def test_websocket_invalid_session_returns_error_and_closes(
    client, mock_session_exists
):
    """Connecting with a non-existent session ID must return error and close."""
    mock_session_exists.return_value = False

    with client.websocket_connect("/sessions/bad-session/stream") as ws:
        error = ws.receive_json()
        assert error == {"error": "Session not found"}
