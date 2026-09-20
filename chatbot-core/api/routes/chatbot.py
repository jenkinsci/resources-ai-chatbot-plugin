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
import asyncio
import os

# =========================
# Third-party imports
# =========================
from typing import List, Optional
from fastapi import (
    APIRouter,
    HTTPException,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
    UploadFile,
    File,
    Form,
    BackgroundTasks
)

# =========================
# Local application imports
# =========================
from api.models.schemas import (
    ChatRequest,
    ChatResponse,
    LogPreviewRequest,
    LogPreviewResponse,
    DeleteResponse,
    MessageHistoryResponse,
    SessionResponse,
    FileAttachment,
    SupportedExtensionsResponse,
    ProviderMetadata,
    ProvidersResponse,
)
from api.config.providers import load_provider_catalog
from api.services.chat_service import (
    get_chatbot_reply,
    get_chatbot_reply_stream,
    provider_manager,
    prepare_log_context,
)
from api.services.memory import (
    delete_session,
    get_session,
    session_exists,
    persist_session,
    init_session,
)
from api.services.file_service import (
    process_uploaded_file,
    get_supported_extensions,
    FileProcessingError,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
DEFAULT_LOG_ANALYSIS_MESSAGE = "Analyze the provided failed Jenkins build logs."

# --- Optional dependency checks (feature flags) ---
LLM_AVAILABLE = False  # pylint: disable=invalid-name
try:
    import llama_cpp  # noqa: F401 # pylint: disable=unused-import
    LLM_AVAILABLE = True  # pylint: disable=invalid-name
except ImportError:
    logger.warning("LLM not available - running in API-only mode")

RETRIEVAL_AVAILABLE = False  # pylint: disable=invalid-name
try:
    import retriv  # noqa: F401 # pylint: disable=unused-import
    RETRIEVAL_AVAILABLE = True  # pylint: disable=invalid-name
except ImportError:
    logger.warning("Retrieval not available - limited functionality")

router = APIRouter()


async def _process_uploaded_files(
    files: Optional[List[UploadFile]],
) -> List[FileAttachment]:
    """Process uploaded files and close each upload after reading it.

    Args:
        files: Uploaded files received from the multipart request.

    Returns:
        Processed file attachments.

    Raises:
        HTTPException: If an uploaded file cannot be processed.
    """
    processed_files: List[FileAttachment] = []

    if not files:
        return processed_files

    for upload_file in files:
        try:
            content = await upload_file.read()
            processed = process_uploaded_file(
                content, upload_file.filename or "unknown"
            )
            processed_files.append(FileAttachment(**processed))
        except FileProcessingError as exc:
            logger.warning("File processing failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=400,
                detail="Unable to process uploaded file.",
            ) from exc
        except Exception as exc:
            logger.error("Unexpected file processing error: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Unable to process uploaded file.",
            ) from exc
        finally:
            await upload_file.close()

    return processed_files


@router.post("/log-preview", response_model=LogPreviewResponse)
def log_preview(request: LogPreviewRequest) -> LogPreviewResponse:
    """Extract and sanitize Jenkins output without invoking the LLM."""
    return LogPreviewResponse(preview=prepare_log_context(request.log_text))


@router.get("/providers", response_model=ProvidersResponse)
def get_providers() -> ProvidersResponse:
    """Return safe metadata for configured providers.

    Returns:
        ProvidersResponse: Provider metadata and configuration status.
    """
    providers = load_provider_catalog()
    return ProvidersResponse(
        providers=[
            ProviderMetadata(
                id=provider.id,
                label=provider.label,
                model=provider.model,
                configured=(
                    provider.id == "local"
                    or bool(os.getenv(provider.api_key_env))
                ),
            )
            for provider in providers
        ]
    )


# =========================
# WebSocket Endpoints
# =========================
@router.websocket("/sessions/{session_id}/stream")
async def chatbot_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time token streaming.

    Accepts WebSocket connections and streams chatbot responses
    token-by-token for a more interactive user experience.
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

            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(
                    "Malformed JSON from session %s", session_id
                )
                await websocket.send_text(
                    json.dumps({"error": "Invalid JSON format."})
                )
                continue

            if not isinstance(message_data, dict):
                logger.warning(
                    "Invalid JSON payload type from session %s: %s",
                    session_id,
                    type(message_data).__name__,
                )
                await websocket.send_text(
                    json.dumps(
                        {"error": "Invalid message payload. Expected JSON object."}
                    )
                )
                continue

            user_message = message_data.get("message", "")
            provider_id = message_data.get("provider", "local")

            if not user_message:
                continue

            if not isinstance(provider_id, str):
                await websocket.send_text(
                    json.dumps({"error": "Provider ID must be a string."})
                )
                continue

            try:
                with provider_manager.activate(provider_id):
                    async for token in get_chatbot_reply_stream(
                        session_id,
                        user_message,
                    ):
                        await websocket.send_text(
                            json.dumps({"token": token})
                        )
            except ValueError as exc:
                logger.error(
                    "WebSocket provider error for session %s: %s",
                    session_id,
                    exc,
                    exc_info=True,
                )
                await websocket.send_text(
                    json.dumps({"error": "Unable to generate a response."})
                )
                continue

            await websocket.send_text(
                json.dumps({"end": True})
            )

            asyncio.create_task(asyncio.to_thread(persist_session, session_id))

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


# =========================
# Session Management
# =========================
@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_chat(response: Response):
    """
    Create a new chat session.

    Returns a unique session ID that can be used for subsequent
    chatbot interactions.
    """
    session_id = init_session()
    response.headers["Location"] = (
        f"/sessions/{session_id}/message"
    )
    return SessionResponse(session_id=session_id)

@router.delete(
    "/sessions/{session_id}",
    response_model=DeleteResponse,
)
def delete_chat(session_id: str):
    """
    Delete an existing chat session.

    Removes all conversation history and resources associated
    with the specified session.
    """
    if not delete_session(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )

    return DeleteResponse(
        message=f"Session {session_id} deleted."
    )


@router.get(
    "/sessions/{session_id}/message",
    response_model=MessageHistoryResponse,
)
def get_chat_history(session_id: str):
    """
    Retrieve the conversation history for a session.

    Returns the ordered list of messages exchanged in the
    given session. Restores persisted sessions from disk
    if they are not currently in memory.

    Args:
        session_id (str): The session identifier.

    Returns:
        MessageHistoryResponse: The session ID and message list.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )

    messages = [
        {"role": msg.type, "content": msg.content}
        for msg in session.chat_memory.messages
    ]
    return MessageHistoryResponse(
        session_id=session_id,
        messages=messages,
    )


# Chat Endpoint
@router.post("/sessions/{session_id}/message", response_model=ChatResponse)
def chatbot_reply(session_id: str, request: ChatRequest, _background_tasks: BackgroundTasks):

    """
    POST endpoint to handle chatbot replies.

    Receives a user message and returns the assistant's reply.
    Validates that the session exists before processing.

    Args:
        session_id (str): The session identifier.
        request (ChatRequest): The request containing the user message.

    Returns:
        ChatResponse: The assistant's reply.
    """
    if not session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )
    message = request.message.strip() or DEFAULT_LOG_ANALYSIS_MESSAGE
    try:
        provider = provider_manager.resolve(request.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with provider_manager.activate_provider(provider):
        reply = get_chatbot_reply(session_id, message)
    _background_tasks.add_task(
        persist_session,
        session_id,
        )

    return reply


@router.post(
    "/sessions/{session_id}/message/upload",
    response_model=ChatResponse,
)
async def chatbot_reply_with_files(
    session_id: str,
    background_tasks: BackgroundTasks,
    message: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    provider: str = Form("local"),
):
    """
    POST endpoint to handle chatbot replies with file uploads.

    Receives a user message with optional file attachments and returns
    the assistant's reply. Files are processed and their content is
    included in the context for the LLM.

    Supported file types:
    - Text files: .txt, .log, .md, .json, .xml, .yaml, .yml, code files
    - Image files: .png, .jpg, .jpeg, .gif, .webp, .bmp

    Args:
        session_id (str): The ID of the session from the URL path.
        message (str): The user's message (form field).
        files (List[UploadFile]): Optional list of uploaded files.

    Returns:
        ChatResponse: The chatbot's generated reply.

    Raises:
        HTTPException: 404 if session not found, 400 if file processing fails,
                      422 if message is empty and no files provided.
    """
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        selected_provider = provider_manager.resolve(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Validate that at least message or files are provided
    has_message = message and message.strip()
    has_files = files and len(files) > 0

    if not has_message and not has_files:
        raise HTTPException(
            status_code=422,
            detail="Either message or files must be provided.",
        )

    processed_files = await _process_uploaded_files(files)

    # Use default message if only files provided
    final_message = (
        message.strip()
        if has_message
        else "Please analyze the attached file(s)."
    )

    with provider_manager.activate_provider(selected_provider):
        reply = await asyncio.to_thread(
            get_chatbot_reply,
            session_id,
            final_message,
            processed_files if processed_files else None
        )
    background_tasks.add_task(
        persist_session,
        session_id,
    )
    return reply


# =========================
# Utility Endpoints
# =========================
@router.get(
    "/files/supported-extensions",
    response_model=SupportedExtensionsResponse,
)
def get_supported_file_extensions():
    """
    GET endpoint to retrieve supported file extensions for upload.

    Returns:
        SupportedExtensionsResponse: Lists of supported text and image extensions,
                                     along with size limits.
    """
    extensions = get_supported_extensions()
    return SupportedExtensionsResponse(**extensions)
