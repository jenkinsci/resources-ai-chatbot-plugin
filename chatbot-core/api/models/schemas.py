"""
Schemas for the chatbot API.

This module defines the request and response data models exchanged between
clients and the chatbot API endpoints.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class FileType(str, Enum):
    """Enum representing supported file types."""
    TEXT = "text"
    IMAGE = "image"


class FileAttachment(BaseModel):
    """
    Represents a processed file attachment.

    Fields:
        filename (str): Original name of the uploaded file.
        type (FileType): Type of file - TEXT or IMAGE.
        content (str): Text content or base64 encoded image data.
        mime_type (str): MIME type of the file.
    """
    filename: str
    type: FileType
    content: str
    mime_type: str

class CreateSessionRequest(BaseModel):
    """
    Request model for creating a new chat session.

    Fields:
        user_id (str): The Jenkins User ID (or 'anonymous').
    """
    user_id: str = Field(..., description="The Jenkins User ID")

class ChatRequest(BaseModel):
    """
    Represents a user message submitted to the chatbot.

    Fields:
        message (str): The user's input message.

    Validation:
        - Rejects messages that are empty.
    """
    message: str

    @field_validator("message")
    def message_must_not_be_empty(cls, v): # pylint: disable=no-self-argument
        """Validator that checks that a message is not empty."""
        if not v.strip():
            raise ValueError("Message cannot be empty.")
        return v


class ChatRequestWithFiles(BaseModel):
    """
    Represents a user message with optional file attachments.

    Fields:
        message (str): The user's input message.
        files (List[FileAttachment]): Optional list of file attachments.

    Validation:
        - Rejects when both message is empty and no files are attached.
    """
    message: str = ""
    files: Optional[List[FileAttachment]] = None

    @model_validator(mode="after")
    def validate_message_or_files(self):
        """Validates that at least message or files are present."""
        has_message = bool(self.message and self.message.strip())
        has_files = bool(self.files and len(self.files) > 0)
        if not has_message and not has_files:
            raise ValueError("Either message or files must be provided.")
        return self

class ChatResponse(BaseModel):
    """
    Represents the chatbot's reply.
    """
    reply: str


class ChatResponseWithFiles(BaseModel):
    """
    Represents the chatbot's reply with information about processed files.

    Fields:
        reply (str): The chatbot's text response.
        processed_files (List[str]): List of filenames that were processed.
    """
    reply: str
    processed_files: Optional[List[str]] = None


class FileUploadResponse(BaseModel):
    """
    Response model for file upload operations.

    Fields:
        success (bool): Whether the upload was successful.
        filename (str): Name of the uploaded file.
        type (str): Type of file processed ("text" or "image").
        message (str): Status message.
    """
    success: bool
    filename: str
    type: str
    message: str


class SupportedExtensionsResponse(BaseModel):
    """
    Response model for supported file extensions.

    Fields:
        text (List[str]): List of supported text file extensions.
        image (List[str]): List of supported image file extensions.
        max_text_size_mb (float): Maximum text file size in MB.
        max_image_size_mb (float): Maximum image file size in MB.
    """
    text: List[str]
    image: List[str]
    max_text_size_mb: float
    max_image_size_mb: float

class SessionResponse(BaseModel):
    """
    Response model when a new chat session is created.
    """
    session_id: str

class DeleteResponse(BaseModel):
    """
    Response model when a session is successfully deleted.
    """
    message: str

class QueryType(Enum):
    """
    Enum that represents the possible query types:
        - MULTI  -> Represents a multi-question query.
        - SIMPLE -> Represents a single scope query.
    """
    MULTI = 'MULTI'
    SIMPLE = 'SIMPLE'

def is_valid_query_type(input_str: str) -> bool:
    """
    Check if the given string is a valid member of the QueryType enum.

    Args:
        input_str (str): The string to validate.

    Returns:
        bool: True if the string is a valid QueryType member, False otherwise.
    """
    return input_str in QueryType.__members__

def str_to_query_type(input_str: str) -> QueryType:
    """
    Convert a string to its corresponding QueryType enum member.

    Args:
        input_str (str): The string representation of a QueryType.

    Returns:
        QueryType: The corresponding enum member.

    Raises:
        ValueError: If the input string is not a valid QueryType.
    """
    try:
        return QueryType[input_str]
    except KeyError as e:
        raise ValueError(f"Invalid query type: {input_str}") from e

def try_str_to_query_type(query_type: str, logger) -> QueryType:
    """
    Extract the generated query type. In case the query type is not
    a not valid output it sets by default to MULTI, since in case it of a false
    positive it won't split up the query.

    Args:
        query (str): The user query.
        logger: The logger param.

    Returns:
        QueryType: the query type, either 'SIMPLE' or 'MULTI'
    """
    if not is_valid_query_type(query_type):
        logger.info("Not valid query type: %s. Setting to default to MULTI.", query_type)
        query_type = 'MULTI'
    return str_to_query_type(query_type)
