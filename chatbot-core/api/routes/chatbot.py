"""
API router for chatbot interactions.

Defines the RESTful endpoints.
This module acts as a "controller" connecting the HTTP layer to 
the chat service logic.
"""

from fastapi import APIRouter, HTTPException, Response, status
from api.models.schemas import (
    ChatRequest,
    ChatResponse,
    SessionResponse,
    DeleteResponse
)
from api.services.chat_service import get_chatbot_reply
from api.services.memory import (
    init_session,
    delete_session,
    session_exists
)

router = APIRouter()


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def start_chat(response: Response):
    """
    POST endpoint to create new sessions.

    Start a new chat session and return its unique session_id.

    Returns:
        SesionResponse: The unique session id.
    Includes in the response the location header to send messages in the chat.
    """
    session_id = init_session()
    response.headers["Location"] = f"/sessions/{session_id}/message"

    return SessionResponse(session_id=session_id)


@router.post("/sessions/{session_id}/message", response_model=ChatResponse)
def chatbot_reply(session_id: str, request: ChatRequest):
    """
    POST endpoint to handle chatbot replies.

    Receives a user message and returns the assistant's reply.
    Validates that the session exists before processing.

    Args:
        session_id (str): The ID of the session from the URL path.
        request (ChatRequest): Contains only the user's message.

    Returns:
        ChatResponse: The chatbot's generated reply.
    """
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    return get_chatbot_reply(session_id, request.message)


@router.delete("/sessions/{session_id}", response_model=DeleteResponse)
def delete_chat(session_id: str):
    """
    Deletes an existing chat session.

    Args:
        session_id (str): The ID of the session to delete.

    Returns:
        DeleteResponse: Confirmation message.
    """
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    return DeleteResponse(message=f"Session {session_id} deleted.")
