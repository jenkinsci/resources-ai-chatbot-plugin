"""Unit tests for the context retriever.

The retriever takes its collaborators as arguments, so these tests pass plain
stubs for the document retriever, the GraphRAG builder and the answer
generator. Nothing here reaches for ``api.services.chat_service``.
"""

import logging

import pytest

from api.config.loader import CONFIG
from api.services import context_retriever


def stub_generator(*responses):
    """Build a generate_answer stub that returns the given responses in order."""
    queue = list(responses)

    def _generate(_prompt, max_tokens=None):  # pylint: disable=unused-argument
        return queue.pop(0) if queue else ""

    return _generate


def documents_returning(*items):
    """Build a get_relevant_documents stub returning the same items per source."""

    def _get_documents(_query, _model, **_kwargs):
        return list(items), None

    return _get_documents


@pytest.mark.parametrize(
    "response,expected",
    [
        ("Label: 1", 1),
        ("Label: 0", 0),
        ("label:1", 1),
        ("no label at all", 0),
        ("Label: 7", 0),
    ],
)
def test_extract_relevance_score(response, expected):
    """Test that only an explicit 0/1 label is honoured, defaulting to 0."""
    assert context_retriever.extract_relevance_score(response) == expected


def test_get_query_context_relevance_uses_injected_generator():
    """Test that the relevance score comes from the injected generator."""
    score = context_retriever.get_query_context_relevance(
        "query", "context", stub_generator("Label: 1"))

    assert score == 1


def test_retrieve_context_returns_empty_message_without_documents():
    """Test the configured empty-context message when no source returns anything."""
    result = context_retriever.retrieve_context(
        "a query", get_documents=documents_returning())

    assert result == CONFIG["retrieval"]["empty_context_message"]


def test_retrieve_context_warns_when_graph_unavailable(caplog):
    """Test that a missing GraphRAG builder degrades to semantic retrieval with a warning."""
    logging.getLogger("API").propagate = True

    with caplog.at_level(logging.WARNING):
        context_retriever.retrieve_context(
            "a query",
            get_documents=documents_returning(
                {"id": "doc-1", "chunk_text": "text", "code_blocks": []}),
            build_graph_context=None,
        )

    assert "GraphRAG is unavailable" in caplog.text


def test_retrieve_context_appends_graph_context():
    """Test that GraphRAG output is appended when a builder is supplied."""
    result = context_retriever.retrieve_context(
        "a query",
        get_documents=documents_returning(
            {"id": "doc-1", "chunk_text": "semantic text", "code_blocks": []}),
        build_graph_context=lambda _query, _logger: "[Source: graph]\na RELATES_TO b",
    )

    assert "semantic text" in result
    assert "[Source: graph]\na RELATES_TO b" in result


def test_retrieve_context_rejects_missing_tool_names(mocker):
    """Test that a config without tool_names fails loudly rather than silently."""
    mocker.patch.dict(CONFIG, {"tool_names": {}}, clear=False)

    with pytest.raises(ValueError, match="tool_names missing from config"):
        context_retriever.retrieve_context(
            "a query", get_documents=documents_returning())


def test_get_reply_simple_query_pipeline_answers_when_relevant(mocker):
    """Test that a relevant context short-circuits the loop and produces an answer."""
    mocker.patch.object(
        context_retriever, "get_agent_tool_calls", return_value=[])
    mocker.patch.object(
        context_retriever, "execute_search_tools", return_value="some context")
    mocker.patch.object(
        context_retriever, "build_prompt", return_value="built prompt")

    # First call scores relevance, second generates the final answer.
    generate = stub_generator("Label: 1", "the answer")

    result = context_retriever.get_reply_simple_query_pipeline(
        "a query", memory=mocker.MagicMock(), generate_answer=generate)

    assert result == "the answer"


def test_get_reply_simple_query_pipeline_falls_back_when_never_relevant(mocker):
    """Test the fallback message when context never scores as relevant."""
    mocker.patch.object(
        context_retriever, "get_agent_tool_calls", return_value=[])
    mocker.patch.object(
        context_retriever, "execute_search_tools", return_value="junk")

    def always_irrelevant(_prompt, max_tokens=None):  # pylint: disable=unused-argument
        return "Label: 0"

    result = context_retriever.get_reply_simple_query_pipeline(
        "a query", memory=mocker.MagicMock(), generate_answer=always_irrelevant)

    assert result == (
        "Unfortunately we are not able to respond to your question about a query.")


def test_get_reply_simple_query_pipeline_respects_iteration_cap(mocker):
    """Test that retrieval is retried no more than the configured number of times."""
    tool_calls = mocker.patch.object(
        context_retriever, "get_agent_tool_calls", return_value=[])
    mocker.patch.object(
        context_retriever, "execute_search_tools", return_value="junk")

    def always_irrelevant(_prompt, max_tokens=None):  # pylint: disable=unused-argument
        return "Label: 0"

    context_retriever.get_reply_simple_query_pipeline(
        "a query", memory=mocker.MagicMock(), generate_answer=always_irrelevant)

    expected = CONFIG["retrieval"]["max_reformulate_iterations"] + 1
    assert tool_calls.call_count == expected
