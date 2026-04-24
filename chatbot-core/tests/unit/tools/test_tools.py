"""Unit tests for api.tools.tools."""

import logging
from unittest.mock import patch

from api.tools import tools


def test_search_stackoverflow_threads_uses_hybrid_retrieval():
    """StackOverflow tool should call retrieval and chunk extraction helpers."""
    query = "jenkins plugin dependency error after upgrade"
    request_logger = logging.getLogger("test-tools")
    semantic_data = [{"id": "chunk-1", "chunk_text": "semantic result", "code_blocks": []}]
    semantic_scores = [0.2]
    keyword_data = [{"id": "chunk-1", "chunk_text": "keyword result", "code_blocks": []}]
    keyword_scores = [5.3]
    expected_result = "stack overflow context"

    with patch(
        "api.tools.tools.retrieve_documents",
        return_value=(semantic_data, semantic_scores, keyword_data, keyword_scores)
    ) as mock_retrieve, patch(
        "api.tools.tools.extract_top_chunks",
        return_value=expected_result
    ) as mock_extract:
        result = tools.search_stackoverflow_threads(query, request_logger)

    assert result == expected_result
    mock_retrieve.assert_called_once_with(
        query=query,
        keywords=query,
        logger=request_logger,
        source_name=tools.CONFIG.get("tool_names", {}).get(
            "stackoverflow_threads",
            "stackoverflow"
        ),
        embedding_model=tools.EMBEDDING_MODEL
    )
    mock_extract.assert_called_once_with(
        semantic_data,
        semantic_scores,
        keyword_data,
        keyword_scores,
        top_k=tools.retrieval_config.get(
            "top_k_stackoverflow",
            tools.retrieval_config["top_k_discourse"]
        ),
        logger=request_logger,
        semantic_weight=0.7
    )


def test_search_stackoverflow_threads_with_blank_query_returns_empty_context_message():
    """Blank query should short-circuit with default empty context message."""
    request_logger = logging.getLogger("test-tools")
    with patch("api.tools.tools.retrieve_documents") as mock_retrieve:
        result = tools.search_stackoverflow_threads("   ", request_logger)

    assert result == tools.retrieval_config["empty_context_message"]
    mock_retrieve.assert_not_called()


def test_search_stackoverflow_threads_uses_configured_source_name(monkeypatch):
    """When configured, the StackOverflow source alias should be used."""
    request_logger = logging.getLogger("test-tools")
    monkeypatch.setitem(
        tools.CONFIG["tool_names"],
        "stackoverflow_threads",
        "stack-overflow-custom-source"
    )

    with patch(
        "api.tools.tools.retrieve_documents",
        return_value=([], [], [], [])
    ) as mock_retrieve:
        tools.search_stackoverflow_threads("jenkins websocket error", request_logger)

    assert mock_retrieve.call_args.kwargs["source_name"] == "stack-overflow-custom-source"
