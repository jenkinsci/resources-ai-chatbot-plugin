"""Unit tests for context size management."""

from api.services.context_manager import estimate_token_count, enforce_context_limit
from langchain.schema import HumanMessage, AIMessage


def test_estimate_token_count():
    """Test token estimation heuristic."""
    assert estimate_token_count("") == 0
    assert estimate_token_count("Hello world") == 2
    assert estimate_token_count("a" * 100) == 25


def test_enforce_context_limit_under_budget():
    """Test that messages under limit are not trimmed."""
    messages = [
        HumanMessage(content="Short question"),
        AIMessage(content="Short answer")
    ]
    result = enforce_context_limit(messages, max_tokens=100)
    assert len(result) == 2
    assert result[0].content == "Short question"


def test_enforce_context_limit_over_budget():
    """Test that old messages are removed when over limit."""
    messages = [
        HumanMessage(content="First message with some content"),
        AIMessage(content="First response with some content"),
        HumanMessage(content="Second message"),
        AIMessage(content="Second response"),
        HumanMessage(content="Third message"),
        AIMessage(content="Third response")
    ]
    result = enforce_context_limit(messages, max_tokens=20)
    assert len(result) < len(messages)
    assert "Third" in result[-1].content or "Third" in result[-2].content
