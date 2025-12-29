"""
API router for chatbot interactions.

Defines the RESTful endpoints.
This module acts as a "controller" connecting the HTTP layer to 
the chat service logic.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Response, status, UploadFile, File, Form, BackgroundTasks
from api.models.schemas import (
    ChatRequest,
    ChatResponse,
    SessionResponse,
    DeleteResponse,
    FileAttachment,
    SupportedExtensionsResponse
)
from api.services.chat_service import get_chatbot_reply
from api.services.memory import (
    init_session,
    delete_session,
    session_exists,
    get_session
)
from api.services.file_service import (
    process_uploaded_file,
    get_supported_extensions,
    FileProcessingError
)
from api.services.sessionmanager import append_message
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
def chatbot_reply(session_id: str, request: ChatRequest, background_tasks: BackgroundTasks):
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

    reply =  get_chatbot_reply(session_id, request.message)
    background_tasks.add_task(append_message , session_id , get_session(session_id).chat_memory.messages) 

    return reply


@router.post("/sessions/{session_id}/message/upload", response_model=ChatResponse)
async def chatbot_reply_with_files(
    session_id: str,
    message: str = Form(...),
    files: Optional[List[UploadFile]] = File(None)
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

    # Validate that at least message or files are provided
    has_message = message and message.strip()
    has_files = files and len(files) > 0

    if not has_message and not has_files:
        raise HTTPException(
            status_code=422,
            detail="Either message or files must be provided."
        )

    # Process uploaded files
    processed_files: List[FileAttachment] = []

    if files:
        for upload_file in files:
            try:
                content = await upload_file.read()
                processed = process_uploaded_file(
                    content, upload_file.filename or "unknown"
                )
                processed_files.append(FileAttachment(**processed))
            except FileProcessingError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process file: {type(e).__name__}"
                ) from e
            finally:
                await upload_file.close()

    # Use default message if only files provided
    final_message = message.strip() if has_message else "Please analyze the attached file(s)."

    return get_chatbot_reply(
        session_id, final_message, processed_files if processed_files else None
    )


@router.get("/files/supported-extensions", response_model=SupportedExtensionsResponse)
def get_supported_file_extensions():
    """
    GET endpoint to retrieve supported file extensions for upload.

    Returns:
        SupportedExtensionsResponse: Lists of supported text and image extensions,
                                     along with size limits.
    """
    extensions = get_supported_extensions()
    return SupportedExtensionsResponse(**extensions)


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
