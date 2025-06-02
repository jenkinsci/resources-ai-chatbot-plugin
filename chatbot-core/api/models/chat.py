"""
Pydantic models for the chatbot API.

Defines the input structure (`ChatRequest`) expected from the client
and the output format (`ChatResponse`) returned by the assistant.
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
