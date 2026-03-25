"""Unit tests for tool functions in api.tools.tools."""

from unittest.mock import MagicMock

from api.tools.tools import search_jenkins_docs
from api.config.loader import CONFIG


def test_search_jenkins_docs_returns_empty_context_when_embedding_unavailable(mocker):
    """Tool should gracefully degrade when embedding model cannot be initialized."""
    mocker.patch("api.tools.tools.get_embedding_model", return_value=None)
    mock_retrieve = mocker.patch("api.tools.tools.retrieve_documents")
    logger = MagicMock()

    result = search_jenkins_docs("jenkins setup", "jenkins setup", logger)

    assert result == CONFIG["retrieval"]["empty_context_message"]
    mock_retrieve.assert_not_called()
    logger.warning.assert_called_once()


def test_search_jenkins_docs_uses_cached_embedding_model(mocker):
    """Tool should call retrieve_documents with the lazily loaded embedding model."""
    mocker.patch("api.tools.tools.get_embedding_model", return_value="model-instance")
    mock_retrieve = mocker.patch(
        "api.tools.tools.retrieve_documents",
        return_value=([], [], [], []),
    )
    logger = MagicMock()

    result = search_jenkins_docs("jenkins setup", "jenkins setup", logger)

    assert result == CONFIG["retrieval"]["empty_context_message"]
    mock_retrieve.assert_called_once_with(
        query="jenkins setup",
        keywords="jenkins setup",
        logger=logger,
        source_name=CONFIG["tool_names"]["jenkins_docs"],
        embedding_model="model-instance",
    )
