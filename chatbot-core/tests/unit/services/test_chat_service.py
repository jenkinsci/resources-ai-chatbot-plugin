"""Unit tests for chat service logic."""

import logging
from unittest.mock import MagicMock
import inspect
import pytest
from api.services.chat_service import (
    _execute_search_tools,
    generate_answer,
    get_chatbot_reply,
    retrieve_context,
)
from api.config.loader import CONFIG
from api.models.schemas import ChatResponse

def test_get_chatbot_reply_success(
    mock_get_session,
    mock_retrieve_context,
    mock_prompt_builder,
    mock_llm_provider,
    mocker
):
    """Test response of get_chatbot_reply for a valid chat session."""
    mock_chat_memory = mocker.MagicMock()
    mock_session = mock_get_session.return_value
    mock_session.chat_memory = mock_chat_memory

    mock_retrieve_context.return_value = "Context to answer"
    mock_prompt_builder.return_value = "Built prompt"
    mock_llm_provider.generate.return_value = "LLM answers to the query"

    response = get_chatbot_reply("session-id", "Query for the LLM")

    assert isinstance(response, ChatResponse)
    assert response.reply == "LLM answers to the query"
    mock_chat_memory.add_user_message.assert_called_once_with("Query for the LLM")
    mock_chat_memory.add_ai_message.assert_called_once_with("LLM answers to the query")


def test_get_chatbot_reply_session_not_found(mock_get_session):
    """Testing that RuntimeError is raised if session does not exist."""
    mock_get_session.return_value = None

    with pytest.raises(RuntimeError) as exc_info:
        get_chatbot_reply("missing-session-id", "Query for the LLM")

    assert "Session 'missing-session-id' not found in the memory store." in str(exc_info.value)


def test_get_chatbot_reply_does_not_log_raw_content(
    mock_get_session,
    mock_retrieve_context,
    mock_prompt_builder,
    mock_llm_provider,
    caplog
):
    """Ensure sensitive payloads are not logged at INFO level."""
    logging.getLogger("API").propagate = True

    sensitive_query = "token=abc123"
    sensitive_context = "internal secret context"
    sensitive_prompt = "prompt contains password=top-secret"

    mock_chat_memory = MagicMock()
    mock_session = mock_get_session.return_value
    mock_session.chat_memory = mock_chat_memory
    mock_retrieve_context.return_value = sensitive_context
    mock_prompt_builder.return_value = sensitive_prompt
    mock_llm_provider.generate.return_value = "safe response"

    with caplog.at_level(logging.INFO):
        get_chatbot_reply("session-id", sensitive_query)

    assert sensitive_query not in caplog.text
    assert sensitive_context not in caplog.text
    assert sensitive_prompt not in caplog.text
    assert "New message from session 'session-id'" in caplog.text


def test_get_chatbot_reply_debug_logs_are_sanitized(
    mock_get_session,
    mock_retrieve_context,
    mock_prompt_builder,
    mock_llm_provider,
    caplog
):
    """Ensure payload-heavy debug logs keep structure but redact secrets."""
    logging.getLogger("API").propagate = True

    sanitized_query = "api_key=[REDACTED]"
    sanitized_context = "password=[REDACTED]"
    sanitized_prompt = "Bearer [REDACTED_TOKEN]"

    mock_chat_memory = MagicMock()
    mock_session = mock_get_session.return_value
    mock_session.chat_memory = mock_chat_memory
    mock_retrieve_context.return_value = "context password=top-secret"
    mock_prompt_builder.return_value = (
        "prompt Authorization: Bearer "
        "ghp_1234567890abcdef1234567890abcdef1234"
    )
    mock_llm_provider.generate.return_value = "safe response"

    with caplog.at_level(logging.DEBUG, logger="API"):
        get_chatbot_reply("session-id", "api_key=abc123")

    assert "api_key=abc123" not in caplog.text
    assert "password=top-secret" not in caplog.text
    assert "ghp_1234567890abcdef1234567890abcdef1234" not in caplog.text
    assert sanitized_query in caplog.text
    assert sanitized_context in caplog.text
    assert sanitized_prompt in caplog.text


def test_generate_answer_error_logs_sanitized_prompt(mock_llm_provider, caplog):
    """Ensure failed prompt logging is sanitized across ERROR and DEBUG paths."""
    logging.getLogger("API").propagate = True
    sensitive_prompt = "api_key=very-secret-key"
    mock_llm_provider.generate.side_effect = RuntimeError("provider failure")

    with caplog.at_level(logging.DEBUG, logger="API"):
        response = generate_answer(sensitive_prompt)

    assert response == "Sorry, I'm having trouble generating a response right now."
    assert sensitive_prompt not in caplog.text
    assert "LLM generation failed" in caplog.text
    assert "api_key=[REDACTED]" in caplog.text


def test_retrieve_context_with_placeholders(mock_get_relevant_documents):
    """Test retrieve_context replaces placeholders with code blocks correctly."""
    mock_documents = get_mock_documents("with_placeholders")
    mock_get_relevant_documents.return_value = (mock_documents, None)

    result = retrieve_context("This is an interesting query")

    document = mock_documents[0]

    assert document["code_blocks"][0] in result
    assert document["code_blocks"][1] in result
    assert "[[CODE_BLOCK_0]]" not in result
    assert "[[CODE_SNIPPET_1]]" not in result
    assert result == (
        "Here is a code block: print('Hello, code block'), and here you have "
        "a code snippet: print('Hello, code snippet')"
    )


def test_retrieve_context_no_documents(mock_get_relevant_documents):
    """Test retrieve_context returns empty context message when no data is found."""
    mock_get_relevant_documents.return_value = ([], None)

    result = retrieve_context("This is a relevant query")

    assert result == CONFIG["retrieval"]["empty_context_message"]

def test_retrieve_context_missing_id(mock_get_relevant_documents, caplog):
    """Test retrieve_context skips chunks missing an ID and logs a warning."""
    mock_get_relevant_documents.return_value = (get_mock_documents("missing_id"), None)
    logging.getLogger("API").propagate = True

    with caplog.at_level(logging.WARNING):
        result = retrieve_context("Query with missing ID")

    assert CONFIG["retrieval"]["empty_context_message"] == result
    assert "Id of retrieved context not found" in caplog.text


def test_retrieve_context_missing_text(mock_get_relevant_documents, caplog):
    """Test retrieve_context skips chunks missing text and logs a warning."""
    mock_get_relevant_documents.return_value = (get_mock_documents("missing_text"), None)
    logging.getLogger("API").propagate = True

    with caplog.at_level(logging.WARNING):
        result = retrieve_context("Query with missing text")

    assert CONFIG["retrieval"]["empty_context_message"] == result
    assert "Text of chunk with ID doc-111 is missing" in caplog.text


def test_retrieve_context_with_missing_code(mock_get_relevant_documents, caplog):
    """Test retrieve_context replaces unmatched placeholders with [MISSING_CODE]."""
    mock_documents = get_mock_documents("missing_code")
    mock_get_relevant_documents.return_value = (mock_documents, None)
    logging.getLogger("API").propagate = True

    with caplog.at_level(logging.WARNING):
        result = retrieve_context("Query with too many placeholders")

    document = mock_documents[0]

    assert document["code_blocks"][0] in result
    assert "[MISSING_CODE]" in result
    assert result == (
        "Snippet 1: print('Only one snippet'), Snippet 2: [MISSING_CODE]"
    )
    assert "More placeholders than code blocks in chunk with ID doc-111" in caplog.text



def get_mock_documents(doc_type: str):
    """Helper function to retrieve the mock documents."""
    if doc_type == "with_placeholders":
        return [
            {
                "id": "doc-111",
                "chunk_text": (
                    "Here is a code block: [[CODE_BLOCK_0]], "
                    "and here you have a code snippet: [[CODE_SNIPPET_1]]"
                ),
                "code_blocks": [
                    "print('Hello, code block')",
                    "print('Hello, code snippet')"
                ]
            }
        ]
    if doc_type == "missing_id":
        return [
            {
                "chunk_text": "Some text with placeholder [[CODE_BLOCK_0]]",
                "code_blocks": ["print('orphan block')"]
            }
        ]
    if doc_type == "missing_text":
        return [
            {
                "id": "doc-111",
                "code_blocks": ["print('no text here')"]
            }
        ]
    if doc_type== "missing_code":
        return [
            {
                "id": "doc-111",
                "chunk_text": (
                    "Snippet 1: [[CODE_BLOCK_0]], Snippet 2: [[CODE_BLOCK_1]]"
                ),
                "code_blocks": ["print('Only one snippet')"]
            }
        ]
    return []



# Tests for _execute_search_tools — Bug fix #241


def test_execute_search_tools_unknown_tool_name_is_skipped(mocker):
    """Test that unknown tool names are skipped gracefully without crashing."""
    mock_logger = mocker.patch("api.services.chat_service.logger")
    mock_registry = {}
    mocker.patch("api.services.chat_service.TOOL_REGISTRY", mock_registry)
    tool_calls = [{"tool": "nonexistent_tool", "params": {"query": "test"}}]
    result = _execute_search_tools(tool_calls)
    assert result == ""
    mock_logger.warning.assert_called_once_with(
        "Unknown tool name '%s'. Skipping.", "nonexistent_tool"
    )


def test_execute_search_tools_logger_injected_automatically(mocker):
    """Test that logger is automatically injected into tools that require it."""
    mock_tool = mocker.MagicMock(return_value="tool result")
    mocker.patch("api.services.chat_service.TOOL_REGISTRY", {"mock_tool": mock_tool})
    mocker.patch(
        "api.services.chat_service.inspect.signature",
        return_value=inspect.signature(lambda query, logger: None)
    )
    _execute_search_tools([{"tool": "mock_tool", "params": {"query": "test"}}])
    assert "logger" in mock_tool.call_args[1]


def test_execute_search_tools_no_logger_not_injected(mocker):
    """Test that logger is NOT injected into tools that do not require it."""
    mock_tool = mocker.MagicMock(return_value="result")
    mocker.patch("api.services.chat_service.TOOL_REGISTRY", {"mock_tool": mock_tool})
    mocker.patch(
        "api.services.chat_service.inspect.signature",
        return_value=inspect.signature(lambda query: None)
    )
    _execute_search_tools([{"tool": "mock_tool", "params": {"query": "test"}}])
    assert "logger" not in mock_tool.call_args[1]


def test_execute_search_tools_returns_combined_results(mocker):
    """Test that results from multiple tools are combined correctly."""
    mock_a = mocker.MagicMock(return_value="result A")
    mock_b = mocker.MagicMock(return_value="result B")
    mocker.patch("api.services.chat_service.TOOL_REGISTRY", {"tool_a": mock_a, "tool_b": mock_b})
    mocker.patch(
        "api.services.chat_service.inspect.signature",
        return_value=inspect.signature(lambda query: None)
    )
    result = _execute_search_tools([
        {"tool": "tool_a", "params": {"query": "test"}},
        {"tool": "tool_b", "params": {"query": "test"}},
    ])
    assert "result A" in result
    assert "result B" in result


def test_execute_search_tools_mixed_valid_and_invalid(mocker):
    """Test that valid tools still execute when mixed with unknown tool names."""
    mock_logger = mocker.patch("api.services.chat_service.logger")
    mock_tool = mocker.MagicMock(return_value="valid result")
    mocker.patch("api.services.chat_service.TOOL_REGISTRY", {"valid_tool": mock_tool})
    mocker.patch(
        "api.services.chat_service.inspect.signature",
        return_value=inspect.signature(lambda query: None)
    )
    result = _execute_search_tools([
        {"tool": "unknown_tool", "params": {"query": "test"}},
        {"tool": "valid_tool", "params": {"query": "test"}},
    ])
    assert "valid result" in result
    mock_logger.warning.assert_called_once_with(
        "Unknown tool name '%s'. Skipping.", "unknown_tool"
    )
