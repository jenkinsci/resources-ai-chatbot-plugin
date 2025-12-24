"""
API router for chatbot interactions.

Defines the RESTful endpoints.
This module acts as a "controller" connecting the HTTP layer to 
the chat service logic.
"""


import json
import logging

from fastapi import APIRouter, HTTPException, Response, status, WebSocket, WebSocketDisconnect
from api.models.schemas import (
    ChatRequest,
    ChatResponse,
    SessionResponse,
    DeleteResponse,
)
from api.services.chat_service import get_chatbot_reply, get_chatbot_reply_stream
from api.services.memory import (
    init_session,
    delete_session,
    session_exists,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# --- Conditional Imports for Optional Dependencies ---
try:
    from llama_cpp import Llama
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logger.warning("LLM not available - running in API-only mode")

try:
    from retriv import DenseRetriever
    RETRIEVAL_AVAILABLE = True
except ImportError:
    RETRIEVAL_AVAILABLE = False
    logger.warning("Retrieval not available - limited functionality")

router = APIRouter()


# WebSocket endpoint for real-time token streaming
@router.websocket("/sessions/{session_id}/stream")
async def chatbot_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time token streaming.
    Protocol:
        Client sends: {"message": "user query"}
        Server sends: {"token": "text"} for each token
        Server sends: {"end": true} when complete
        Server sends: {"error": "message"} on errors
    """
    logger.info(f"WebSocket connection attempt for session: {session_id}")
    await websocket.accept()
    logger.info(f"WebSocket accepted for session: {session_id}")

    if not session_exists(session_id):
        await websocket.send_text(json.dumps({"error": "Session not found"}))
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")

            if not user_message:
                continue

            async for token in get_chatbot_reply_stream(session_id, user_message):
                await websocket.send_text(json.dumps({"token": token}))

            await websocket.send_text(json.dumps({"end": True}))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({"error": "An unexpected error occurred."}))
        except:
            pass  # Connection already closed


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
