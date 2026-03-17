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
# GET /sessions tests
# =========================
def _make_session_payload(session_id="abc-123", message_count=4):
    """Build the dict that list_sessions returns for a single session."""
    return {
        "sessions": [
            {
                "session_id": session_id,
                "message_count": message_count,
                "last_accessed": "2026-01-01T00:00:00",
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }


def test_get_sessions_empty(client, mock_list_sessions):
    """GET /sessions returns an empty list when no sessions exist."""
    mock_list_sessions.return_value = {
        "sessions": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
    }

    response = client.get("/sessions")

    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_get_sessions_with_sessions(client, mock_list_sessions):
    """GET /sessions returns session metadata when sessions exist."""
    mock_list_sessions.return_value = _make_session_payload()

    response = client.get("/sessions")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["sessions"]) == 1
    session = data["sessions"][0]
    assert session["session_id"] == "abc-123"
    assert session["message_count"] == 4
    assert "last_accessed" in session


def test_get_sessions_default_pagination(client, mock_list_sessions):
    """GET /sessions calls list_sessions with default page=1 and page_size=20."""
    mock_list_sessions.return_value = {
        "sessions": [], "total": 0, "page": 1, "page_size": 20,
    }

    client.get("/sessions")

    mock_list_sessions.assert_called_once_with(page=1, page_size=20)


def test_get_sessions_custom_pagination(client, mock_list_sessions):
    """GET /sessions forwards custom page and page_size query params."""
    mock_list_sessions.return_value = {
        "sessions": [], "total": 0, "page": 2, "page_size": 5,
    }

    client.get("/sessions?page=2&page_size=5")

    mock_list_sessions.assert_called_once_with(page=2, page_size=5)


def test_get_sessions_clamps_page_size_to_100(client, mock_list_sessions):
    """GET /sessions clamps page_size > 100 down to 100."""
    mock_list_sessions.return_value = {
        "sessions": [], "total": 0, "page": 1, "page_size": 100,
    }

    client.get("/sessions?page_size=9999")

    mock_list_sessions.assert_called_once_with(page=1, page_size=100)


def test_get_sessions_clamps_page_to_minimum_1(client, mock_list_sessions):
    """GET /sessions clamps page < 1 up to 1."""
    mock_list_sessions.return_value = {
        "sessions": [], "total": 0, "page": 1, "page_size": 20,
    }

    client.get("/sessions?page=-5")

    mock_list_sessions.assert_called_once_with(page=1, page_size=20)

