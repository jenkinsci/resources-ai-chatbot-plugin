"""Unit tests for context size management."""

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from api.services.context_manager import estimate_token_count, enforce_context_limit


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


def test_preserve_system_message():
    """Test that system messages are never trimmed."""
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="First question with lots of content here"),
        AIMessage(content="First answer with lots of content here"),
        HumanMessage(content="Second question"),
        AIMessage(content="Second answer")
    ]
    result = enforce_context_limit(messages, max_tokens=20)

    assert len(result) > 0
    assert isinstance(result[0], SystemMessage)
    assert result[0].content == "You are a helpful assistant."


def test_single_message_exceeds_budget():
    """Test behavior when a single message exceeds the budget."""
    messages = [
        HumanMessage(content="Very long message " * 100)
    ]
    result = enforce_context_limit(messages, max_tokens=10)

    assert len(result) == 1
    assert result[0].content == messages[0].content
