"""Unit tests for api/tools/tools.py."""
from unittest.mock import patch, MagicMock

from api.config.loader import CONFIG
from api.tools.tools import (
    search_plugin_docs,
    search_jenkins_docs,
    search_stackoverflow_threads,
    search_community_threads,
)


class TestSearchStackoverflowThreads:
    """Tests for search_stackoverflow_threads function."""

    def test_returns_nothing_relevant_for_valid_query(self):
        """Test that a valid query returns nothing relevant."""
        result = search_stackoverflow_threads("how to fix jenkins pipeline")
        assert result == "Nothing relevant"

    def test_returns_nothing_relevant_for_empty_query(self):
        """Test that an empty query returns nothing relevant."""
        result = search_stackoverflow_threads("")
        assert result == "Nothing relevant"


class TestSearchPluginDocs:
    """Tests for search_plugin_docs function."""

    @patch("api.tools.tools.extract_top_chunks")
    @patch("api.tools.tools.retrieve_documents")
    def test_returns_result_without_plugin_name(self, mock_retrieve, mock_extract):
        """Test result is returned when no plugin name is provided."""
        mock_retrieve.return_value = (["doc1"], [0.9], ["doc2"], [0.8])
        mock_extract.return_value = "plugin result"
        logger = MagicMock()
        result = search_plugin_docs("query", "keywords", logger)
        assert result == "plugin result"
        mock_retrieve.assert_called_once()
        mock_extract.assert_called_once()

    @patch("api.tools.tools.extract_top_chunks")
    @patch("api.tools.tools.filter_retrieved_data")
    @patch("api.tools.tools.is_valid_plugin")
    @patch("api.tools.tools.retrieve_documents")
    def test_filters_data_when_valid_plugin_name(
        self, mock_retrieve, mock_is_valid, mock_filter, mock_extract
    ):
        """Test that data is filtered when a valid plugin name is given."""
        mock_retrieve.return_value = (["doc1"], [0.9], ["doc2"], [0.8])
        mock_is_valid.return_value = True
        mock_filter.return_value = (["filtered1"], ["filtered2"])
        mock_extract.return_value = "filtered result"
        logger = MagicMock()
        result = search_plugin_docs("query", "keywords", logger, plugin_name="git")
        assert result == "filtered result"
        mock_filter.assert_called_once()

    @patch("api.tools.tools.extract_top_chunks")
    @patch("api.tools.tools.is_valid_plugin")
    @patch("api.tools.tools.retrieve_documents")
    def test_skips_filter_when_invalid_plugin_name(
        self, mock_retrieve, mock_is_valid, mock_extract
    ):
        """Test that filter is skipped when plugin name is invalid."""
        mock_retrieve.return_value = (["doc1"], [0.9], ["doc2"], [0.8])
        mock_is_valid.return_value = False
        mock_extract.return_value = "unfiltered result"
        logger = MagicMock()
        result = search_plugin_docs("query", "keywords", logger, plugin_name="invalid")
        assert result == "unfiltered result"

    @patch("api.tools.tools.build_graph_runtime_context")
    @patch("api.tools.tools.retrieve_documents")
    @patch("api.tools.tools.extract_top_chunks")
    def test_appends_graph_context(
        self, mock_extract, mock_retrieve, mock_graph_context
    ):
        """Test plugin search appends GraphRAG context when available."""
        mock_retrieve.return_value = (["doc1"], [0.9], ["doc2"], [0.8])
        mock_extract.return_value = "plugin result"
        mock_graph_context.return_value = "graph result"

        result = search_plugin_docs("query", "keywords", MagicMock())

        assert result == "plugin result\n\ngraph result"

    @patch("api.tools.tools.build_graph_runtime_context")
    @patch("api.tools.tools.retrieve_documents")
    @patch("api.tools.tools.extract_top_chunks")
    def test_returns_graph_context_when_plugin_context_empty(
        self, mock_extract, mock_retrieve, mock_graph_context
    ):
        """Test graph context replaces the empty plugin retrieval message."""
        mock_retrieve.return_value = ([], [], [], [])
        mock_extract.return_value = CONFIG["retrieval"]["empty_context_message"]
        mock_graph_context.return_value = "graph result"

        result = search_plugin_docs("query", "keywords", MagicMock())

        assert result == "graph result"


class TestSearchJenkinsDocs:
    """Tests for search_jenkins_docs function."""

    @patch("api.tools.tools.extract_top_chunks")
    @patch("api.tools.tools.retrieve_documents")
    def test_returns_result(self, mock_retrieve, mock_extract):
        """Test that jenkins docs search returns a result."""
        mock_retrieve.return_value = (["doc1"], [0.9], ["doc2"], [0.8])
        mock_extract.return_value = "jenkins docs result"
        logger = MagicMock()
        result = search_jenkins_docs("query", "keywords", logger)
        assert result == "jenkins docs result"
        mock_retrieve.assert_called_once()
        mock_extract.assert_called_once()

    @patch("api.tools.tools.extract_top_chunks")
    @patch("api.tools.tools.retrieve_documents")
    def test_returns_result_for_empty_query(self, mock_retrieve, mock_extract):
        """Test that jenkins docs search handles empty query."""
        mock_retrieve.return_value = ([], [], [], [])
        mock_extract.return_value = ""
        logger = MagicMock()
        result = search_jenkins_docs("", "", logger)
        assert result == ""


class TestSearchCommunityThreads:
    """Tests for search_community_threads function."""

    @patch("api.tools.tools.extract_top_chunks")
    @patch("api.tools.tools.retrieve_documents")
    def test_returns_result_with_semantic_weight(self, mock_retrieve, mock_extract):
        """Test that community threads search uses correct semantic weight."""
        mock_retrieve.return_value = (["doc1"], [0.9], ["doc2"], [0.8])
        mock_extract.return_value = "community result"
        logger = MagicMock()
        result = search_community_threads("query", "keywords", logger)
        assert result == "community result"
        mock_extract.assert_called_once()
        call_kwargs = mock_extract.call_args.kwargs
        assert call_kwargs.get("semantic_weight") == 0.7

    @patch("api.tools.tools.extract_top_chunks")
    @patch("api.tools.tools.retrieve_documents")
    def test_returns_result_for_empty_query(self, mock_retrieve, mock_extract):
        """Test that community threads search handles empty query."""
        mock_retrieve.return_value = ([], [], [], [])
        mock_extract.return_value = ""
        logger = MagicMock()
        result = search_community_threads("", "", logger)
        assert result == ""
