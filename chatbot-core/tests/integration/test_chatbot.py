"""Integration Tests for the chatbot."""

from pydantic import ValidationError
from api.models.schemas import ChatResponse

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

    client.delete(f"/sessions/{active_session}")
    response_b = client.post(f"/sessions/{deleted_session}/message",
                                json={"message": "Message again"})
    response_a = client.post(f"/sessions/{active_session}/message",
                                json={"message": "Should be off"})

    assert response_b.status_code == 200
    assert response_a.status_code == 404
    assert response_a.json() == {"detail": "Session not found."}


def get_relevant_documents_output():
    """Utility to return the output of the mock of get_relevant_documents."""
    return ([
        {
            "id": "docid",
            "chunk_text": "Relevant chunk text."
        }],[0.84])
