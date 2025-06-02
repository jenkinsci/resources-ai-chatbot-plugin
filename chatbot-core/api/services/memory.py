"""
Handles in-memory chat session state (conversation memory).
Provides utility functions for session lifecycle.
"""

import uuid
from langchain.memory import ConversationBufferMemory

# sessionId --> history
_sessions = {}

def init_session() -> str:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = ConversationBufferMemory(return_messages=True)
    return session_id

def get_session(session_id: str) -> ConversationBufferMemory | None:
    return _sessions.get(session_id)

def delete_session(session_id: str) -> bool:
    print(_sessions)
    return _sessions.pop(session_id, None) is not None

def session_exists(session_id: str) -> bool:
    return session_id in _sessions
