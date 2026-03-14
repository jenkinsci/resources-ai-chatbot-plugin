"""Unit tests for chat service logic."""

import logging
from unittest.mock import MagicMock
import pytest
from api.services.chat_service import generate_answer, get_chatbot_reply, retrieve_context
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

def test_retrieve_context_detects_logs_and_calls_generator(mocker, caplog):
    """Test that log patterns trigger the query generator and use the result for retrieval."""
    # Mock dependencies
    mock_generate_query = mocker.patch("api.services.chat_service._generate_search_query_from_logs")
    mock_get_documents = mocker.patch("api.services.chat_service.get_relevant_documents")

    # Setup inputs
    log_content = "Error: Something went wrong..."
    user_input = (
        f"I found a build failure. Here are the last 5000 characters of the log:\n"
        f"```\n{log_content}\n```\nAnalyze this."
    )
    generated_query = "Build failure with Error: Something went wrong"

    mock_generate_query.return_value = generated_query
    mock_get_documents.return_value = ([], None) # Return empty so we focus on the call args

    # Force dev_mode to False to ensure RAG runs
    mocker.patch.dict(CONFIG, {"dev_mode": False})

    # Execute
    retrieve_context(user_input)

    # Assertions
    mock_generate_query.assert_called_once_with(log_content.strip())

    # Verify get_relevant_documents was called with the GENERATED query
    args, _ = mock_get_documents.call_args
    assert args[0] == generated_query

    # Verify logs
    assert "Log pattern detected in user input" in caplog.text
    assert f"Generated search query from logs: {generated_query}" in caplog.text


def test_retrieve_context_uses_raw_input_if_no_logs_detected(mocker):
    """Test that normal questions bypass the log analysis logic."""
    mock_generate_query = mocker.patch("api.services.chat_service._generate_search_query_from_logs")
    mock_get_documents = mocker.patch("api.services.chat_service.get_relevant_documents")

    user_input = "How do I configure the git plugin?"
    mock_get_documents.return_value = ([], None)
    mocker.patch.dict(CONFIG, {"dev_mode": False})

    retrieve_context(user_input)

    mock_generate_query.assert_not_called()

    # Verify retrieval used the original raw input
    args, _ = mock_get_documents.call_args
    assert args[0] == user_input


def test_retrieve_context_handles_generator_exception(mocker, caplog):
    """Test that the system falls back to raw input if log summarization fails."""
    mock_generate_query = mocker.patch("api.services.chat_service._generate_search_query_from_logs")
    mock_get_documents = mocker.patch("api.services.chat_service.get_relevant_documents")

    user_input = "Here are the last 5000 characters of the log:\n```\nSome Error\n```"

    # Simulate an error in the LLM generator
    mock_generate_query.side_effect = Exception("LLM generation failed")
    mock_get_documents.return_value = ([], None)
    mocker.patch.dict(CONFIG, {"dev_mode": False})

    retrieve_context(user_input)

    # Verify error was logged and fallback occurred
    assert "Failed to generate search query from logs: LLM generation failed" in caplog.text

    # Should fall back to the original input
    args, _ = mock_get_documents.call_args
    assert args[0] == user_input
