from langchain.memory import ConversationBufferMemory

# session_id --> memory object
session_memory_store = {}

def get_or_create_memory(session_id: str) -> ConversationBufferMemory:
    """
    Retrieve existing memory for a session or create a new one.
    """
    if session_id not in session_memory_store:
        session_memory_store[session_id] = ConversationBufferMemory(
            memory_key="history",
            return_messages=True
        )
    return session_memory_store[session_id]
