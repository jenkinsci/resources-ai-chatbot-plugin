"""
Schemas for the chatbot API.

This module defines the request and response data models exchanged between
clients and the chatbot API endpoints.
"""

from pydantic import BaseModel

class ChatRequest(BaseModel):
    """
    Represents a user message submitted to the chatbot.
    """
    message: str

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
