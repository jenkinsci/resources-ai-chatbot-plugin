"""Integration Tests for the chatbot."""

from pydantic import ValidationError
import pytest
from api.models.schemas import ChatResponse
from api.services import memory


@pytest.fixture(autouse=True)
def reset_memory_sessions():
    """Executed before any test to reset the _sessions across the tests."""
    memory.reset_sessions()

def test_create_session(client):
    """Should create a new chat session and return session ID and location header."""
    response = client.post("/sessions")
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert isinstance(data["session_id"], str)
    assert response.headers["Location"] == f"/sessions/{data['session_id']}/message"


def test_reply_to_existing_session(client, mock_llm_provider, mock_get_relevant_documents):
    """Should return a chatbot reply for a valid session and input message."""
    create_resp = client.post("/sessions")
    session_id = create_resp.json()["session_id"]
    mock_llm_provider.generate.return_value = "LLM answers to the query"
    mock_get_relevant_documents.return_value = get_relevant_documents_output()

    payload = {"message": "Hello"}
    response = client.post(f"/sessions/{session_id}/message", json=payload)

    assert response.status_code == 200
    try:
        chat_response = ChatResponse.model_validate(response.json())
    except ValidationError as e:
        assert False, f"Response did not match the expected schema: {e}"
    assert chat_response.reply == "LLM answers to the query"

def test_reply_to_nonexistent_session(client):
    """Should return 404 when replying to a non-existent session."""
    payload = {"message": "Hello"}
    response = client.post("/sessions/nonexistent-session/message", json=payload)

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found."}


def test_delete_existing_session(client):
    """Should delete an existing session and confirm deletion message."""
    create_resp = client.post("/sessions")
    session_id = create_resp.json()["session_id"]

    response = client.delete(f"/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json() == {"message": f"Session {session_id} deleted."}


def test_delete_nonexistent_session(client):
    """Should return 404 when trying to delete a non-existent session."""
    response = client.delete("/sessions/invalid-session")
    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found."}


def test_reply_after_session_deleted(client):
    """Should return 404 when replying to a session that was deleted."""
    create_resp = client.post("/sessions")
    session_id = create_resp.json()["session_id"]

    client.delete(f"/sessions/{session_id}")

    payload = {"message": "Is anyone there?"}
    response = client.post(f"/sessions/{session_id}/message", json=payload)

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found."}


def test_reply_with_empty_message(client):
    """Should return 422 when sending an empty message."""
    create_resp = client.post("/sessions")
    session_id = create_resp.json()["session_id"]

    payload = {"message": "   "}
    response = client.post(f"/sessions/{session_id}/message", json=payload)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("Message cannot be empty." in e["msg"] for e in errors)


def test_full_chat_lifecycle(client, mock_llm_provider, mock_get_relevant_documents):
    """Test the complete flow: create, send message, delete a chat session."""
    mock_llm_provider.generate.return_value = "Hello from the bot!"
    mock_get_relevant_documents.return_value = get_relevant_documents_output()

    create_resp = client.post("/sessions")
    assert create_resp.status_code == 201
    session_id = create_resp.json()["session_id"]

    payload = {"message": "Hello"}
    reply_resp = client.post(f"/sessions/{session_id}/message", json=payload)
    assert reply_resp.status_code == 200
    assert reply_resp.json()["reply"] == "Hello from the bot!"

    delete_resp = client.delete(f"/sessions/{session_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["message"] == f"Session {session_id} deleted."


def test_multiple_messages_in_session(client, mock_llm_provider, mock_get_relevant_documents):
    """Ensure multiple consecutive messages are handled in the same session."""
    mock_llm_provider.generate.side_effect = [
        "Reply 1", "Reply 2", "Reply 3"
    ]
    mock_get_relevant_documents.side_effect = [
        get_relevant_documents_output(),
        get_relevant_documents_output(),
        get_relevant_documents_output()
    ]
    session_id = client.post("/sessions").json()["session_id"]
    for i in range(3):
        resp = client.post(f"/sessions/{session_id}/message", json={"message": f"Msg {i+1}"})
        assert resp.status_code == 200
        assert resp.json()["reply"] == f"Reply {i+1}"


def test_multiple_sessions_are_isolated(client, mock_llm_provider, mock_get_relevant_documents):
    """Ensure messages in different sessions don't interfere with each other."""
    mock_llm_provider.generate.return_value = "LLM response"
    mock_get_relevant_documents.return_value = get_relevant_documents_output()

    active_session = client.post("/sessions").json()["session_id"]
    deleted_session = client.post("/sessions").json()["session_id"]

    client.post(f"/sessions/{active_session}/message", json={"message": "Hi A"})
    client.post(f"/sessions/{deleted_session}/message", json={"message": "Hi B"})

    client.delete(f"/sessions/{deleted_session}")
    response_active_session = client.post(f"/sessions/{active_session}/message",
                                json={"message": "Message again"})
    response_deleted_session = client.post(f"/sessions/{deleted_session}/message",
                                json={"message": "Should be off"})

    assert response_active_session.status_code == 200
    assert response_deleted_session.status_code == 404
    assert response_deleted_session.json() == {"detail": "Session not found."}


def test_get_history_empty_session(client):
    """Should return an empty message list for a newly created session."""
    session_id = client.post("/sessions").json()["session_id"]

    response = client.get(f"/sessions/{session_id}/message")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["messages"] == []


def test_get_history_with_messages(client, mock_llm_provider, mock_get_relevant_documents):
    """Should return the conversation history after exchanging messages."""
    mock_llm_provider.generate.return_value = "Bot reply"
    mock_get_relevant_documents.return_value = get_relevant_documents_output()

    session_id = client.post("/sessions").json()["session_id"]
    client.post(f"/sessions/{session_id}/message", json={"message": "Hello"})

    response = client.get(f"/sessions/{session_id}/message")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "human"
    assert data["messages"][0]["content"] == "Hello"
    assert data["messages"][1]["role"] == "ai"
    assert data["messages"][1]["content"] == "Bot reply"


def test_get_history_nonexistent_session(client):
    """Should return 404 when retrieving history of a non-existent session."""
    response = client.get("/sessions/nonexistent-session/message")
    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found."}


def test_get_history_deleted_session(client):
    """Should return 404 when retrieving history of a deleted session."""
    session_id = client.post("/sessions").json()["session_id"]
    client.delete(f"/sessions/{session_id}")

    response = client.get(f"/sessions/{session_id}/message")
    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found."}


def get_relevant_documents_output():
    """Utility to return the output of the mock of get_relevant_documents."""
    return ([
        {
            "id": "docid",
            "chunk_text": "Relevant chunk text."
        }],[0.84])


# =========================
# GET /sessions integration tests
# =========================
def test_list_sessions_empty(client):
    """Should return an empty session list when no sessions have been created."""
    response = client.get("/sessions")

    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_list_sessions_after_create(client):
    """Should include a newly created session in the list."""
    create_resp = client.post("/sessions")
    session_id = create_resp.json()["session_id"]

    response = client.get("/sessions")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    ids = [s["session_id"] for s in data["sessions"]]
    assert session_id in ids


def test_list_sessions_message_count(client, mock_llm_provider, mock_get_relevant_documents):
    """Should report accurate message_count after exchanging messages."""
    mock_llm_provider.generate.return_value = "Hello!"
    mock_get_relevant_documents.return_value = get_relevant_documents_output()

    session_id = client.post("/sessions").json()["session_id"]
    client.post(f"/sessions/{session_id}/message", json={"message": "Hi"})

    data = client.get("/sessions").json()

    session = next(s for s in data["sessions"] if s["session_id"] == session_id)
    # 1 human + 1 ai message = 2
    assert session["message_count"] == 2


def test_list_sessions_multiple_sessions(client):
    """Should list all active sessions."""
    id_a = client.post("/sessions").json()["session_id"]
    id_b = client.post("/sessions").json()["session_id"]

    data = client.get("/sessions").json()

    assert data["total"] == 2
    ids = {s["session_id"] for s in data["sessions"]}
    assert id_a in ids
    assert id_b in ids


def test_list_sessions_excludes_deleted(client):
    """Should not include sessions that have been deleted."""
    keep_id = client.post("/sessions").json()["session_id"]
    drop_id = client.post("/sessions").json()["session_id"]
    client.delete(f"/sessions/{drop_id}")

    data = client.get("/sessions").json()

    ids = [s["session_id"] for s in data["sessions"]]
    assert keep_id in ids
    assert drop_id not in ids
    assert data["total"] == 1


def test_list_sessions_pagination(client):
    """Should respect page and page_size query parameters."""
    for _ in range(3):
        client.post("/sessions")

    page1 = client.get("/sessions?page=1&page_size=2").json()
    page2 = client.get("/sessions?page=2&page_size=2").json()

    assert len(page1["sessions"]) == 2
    assert len(page2["sessions"]) == 1
    assert page1["total"] == 3
    assert page2["total"] == 3


def test_list_sessions_response_has_last_accessed(client):
    """Each session entry should include a non-empty last_accessed ISO timestamp."""
    client.post("/sessions")

    session = client.get("/sessions").json()["sessions"][0]

    assert "last_accessed" in session
    assert len(session["last_accessed"]) > 0

