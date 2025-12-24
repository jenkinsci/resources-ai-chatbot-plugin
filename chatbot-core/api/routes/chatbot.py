"""
API router for chatbot interactions.

Defines the RESTful endpoints.
This module acts as a controller connecting the HTTP layer
to the chat service logic.
"""

# =========================
# Standard library imports
# =========================
import json
import logging

# =========================
# Third-party imports
# =========================
from fastapi import (
    APIRouter,
    HTTPException,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)

# =========================
# Local application imports
# =========================
from api.models.schemas import (
    ChatRequest,
    ChatResponse,
    SessionResponse,
    DeleteResponse,
)
from api.services.chat_service import (
    get_chatbot_reply,
    get_chatbot_reply_stream,
)
from api.services.memory import (
    init_session,
    delete_session,
    session_exists,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# --- Optional dependency checks (feature flags) ---
LLM_AVAILABLE = False
try:
    import llama_cpp  # noqa: F401 # pylint: disable=unused-import
    LLM_AVAILABLE = True
except ImportError:
    logger.warning("LLM not available - running in API-only mode")

RETRIEVAL_AVAILABLE = False
try:
    import retriv  # noqa: F401 # pylint: disable=unused-import
    RETRIEVAL_AVAILABLE = True
except ImportError:
    logger.warning("Retrieval not available - limited functionality")

router = APIRouter()


# WebSocket endpoint for real-time token streaming
@router.websocket("/sessions/{session_id}/stream")
async def chatbot_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time token streaming.
    """
    logger.info("WebSocket connection attempt for session: %s", session_id)
    await websocket.accept()
    logger.info("WebSocket accepted for session: %s", session_id)

    if not session_exists(session_id):
        await websocket.send_text(
            json.dumps({"error": "Session not found"})
        )
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")

            if not user_message:
                continue

            async for token in get_chatbot_reply_stream(
                session_id,
                user_message,
            ):
                await websocket.send_text(
                    json.dumps({"token": token})
                )

            await websocket.send_text(
                json.dumps({"end": True})
            )

    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected for session %s",
            session_id,
        )

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error(
            "WebSocket error for session %s: %s",
            session_id,
            exc,
            exc_info=True,
        )
        try:
            await websocket.send_text(
                json.dumps(
                    {"error": "An unexpected error occurred."}
                )
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # Connection already closed
            pass


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_chat(response: Response):
    """
    Create a new chat session.
    """
    session_id = init_session()
    response.headers["Location"] = (
        f"/sessions/{session_id}/message"
    )
    return SessionResponse(session_id=session_id)


@router.post(
    "/sessions/{session_id}/message",
    response_model=ChatResponse,
)
def chatbot_reply(session_id: str, request: ChatRequest):
    """
    Handle chatbot replies.
    """
    if not session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )

    return get_chatbot_reply(
        session_id,
        request.message,
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=DeleteResponse,
)
def delete_chat(session_id: str):
    """
    Delete an existing chat session.
    """
    if not delete_session(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )

    return DeleteResponse(
    message=f"Session {session_id} deleted."
    )
