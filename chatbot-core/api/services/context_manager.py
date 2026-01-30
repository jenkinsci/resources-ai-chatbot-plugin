"""
Context size management for conversation history.
Prevents LLM context overflow by trimming old messages.
"""

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
    
    Args:
        messages: List of LangChain message objects
        max_tokens: Maximum allowed tokens for history
        
    Returns:
        Trimmed message list
    """
    if not messages:
        return []
    
    total_text = "".join(msg.content or "" for msg in messages)
    estimated_tokens = estimate_token_count(total_text)
    
    if estimated_tokens <= max_tokens:
        return messages
    
    trimmed = list(messages)
    while trimmed:
        current_text = "".join(msg.content or "" for msg in trimmed)
        if estimate_token_count(current_text) <= max_tokens:
            break
        trimmed.pop(0)
    
    return trimmed
