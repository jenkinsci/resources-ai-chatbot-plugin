"""
Context size management for conversation history.
Prevents LLM context overflow by trimming old messages.
"""

from langchain.schema import SystemMessage

def estimate_token_count(text: str) -> int:
    """
    Estimate token count using character-based heuristic.

    Args:
        text: Input text

    Returns:
        Estimated token count (1 token ≈ 4 characters)
    """
    return len(text) // 4


def enforce_context_limit(messages: list, max_tokens: int) -> list:
    """
    Trim message history to fit within token budget.
    Removes oldest messages first until under the limit.
    System messages are always preserved.

    Args:
        messages: List of LangChain message objects
        max_tokens: Maximum allowed tokens for history

    Returns:
        Trimmed message list with system messages preserved
    """
    if not messages:
        return []

    system_msgs = [msg for msg in messages if isinstance(msg, SystemMessage)]
    conversation = [msg for msg in messages if not isinstance(msg, SystemMessage)]

    if not conversation:
        return system_msgs

    total_text = "".join(msg.content or "" for msg in conversation)
    total_tokens = estimate_token_count(total_text)

    if total_tokens <= max_tokens:
        return messages

    trimmed = list(conversation)
    while len(trimmed) > 1 and total_tokens > max_tokens:
        removed = trimmed.pop(0)
        total_tokens -= estimate_token_count(removed.content or "")

    return system_msgs + trimmed
