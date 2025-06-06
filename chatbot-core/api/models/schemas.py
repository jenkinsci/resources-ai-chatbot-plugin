"""
Schemas for the chatbot API.

This module defines the request and response data models exchanged between
clients and the chatbot API endpoints.
"""

from pydantic import BaseModel, field_validator

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

class ChatResponse(BaseModel):
    """
    Represents the chatbot's reply.
    """
    reply: str

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
