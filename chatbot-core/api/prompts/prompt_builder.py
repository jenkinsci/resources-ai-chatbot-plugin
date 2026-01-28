"""
Constructs the prompt used for querying the LLM, including system-level instructions,
chat history, context retrieved from the knowledge base, and the user's question.
"""
from typing import Optional
from langchain.memory import ConversationBufferMemory
from api.prompts.prompts import SYSTEM_INSTRUCTION, LOG_ANALYSIS_INSTRUCTION

def build_prompt(
    user_query: str,
    context: str,
    memory: ConversationBufferMemory,
    log_context: Optional[str] = None
) -> str:
    """
    Build the full prompt by combining system instructions, chat history, context,
    user question, and optional log data.

    Args:
        user_query (str): The raw question from the user.
        context (str): The relevant retrieved chunks to ground the answer.
        memory (ConversationBufferMemory): LangChain memory holding prior chat turns.
        log_context (Optional[str]): Raw logs provided by the user (e.g. build failure logs).

    Returns:
        str: A structured prompt for the language model.
    """
    if memory:
        history = "\n".join(
            f"{'User' if msg.type == 'human' else 'Jenkins Assistant'}: {msg.content or ''}"
            for msg in memory.chat_memory.messages
        ) if memory.chat_memory.messages else ""
    else:
        history = ""

    # If log context exists, we append it as a specific section
    if log_context:
        system_prompt = LOG_ANALYSIS_INSTRUCTION
        log_section = f"""
            User-Provided Log Data:
            {log_context}
            """
    else:
        # Otherwise, use the standard Friendly Assistant prompt
        system_prompt = SYSTEM_INSTRUCTION
        log_section = ""

    prompt = f"""{system_prompt}
            Chat History:
            {history}

            Context (Documentation & Knowledge Base):
            {context}
            {log_section}
            User Question:
            {user_query.strip()}

            Answer:
            """

    return prompt
