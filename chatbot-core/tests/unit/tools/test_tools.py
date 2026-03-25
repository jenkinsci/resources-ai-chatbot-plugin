import pytest
from unittest.mock import patch, MagicMock
from api.tools.tools import (
    search_plugin_docs,
    search_jenkins_docs,
    search_stackoverflow_threads,
    search_community_threads,
)


class TestSearchStackoverflowThreads:
    def test_returns_nothing_relevant_for_valid_query(self):
        result = search_stackoverflow_threads("how to fix jenkins pipeline")
        assert result == "Nothing relevant"

    def test_returns_nothing_relevant_for_empty_query(self):
        result = search_stackoverflow_threads("")
        assert result == "Nothing relevant"


class TestSearchPluginDocs:
    @patch("api.tools.tools.extract_top_chunks")
    @patch("api.tools.tools.retrieve_documents")
    def test_returns_result_without_plugin_name(self, mock_retrieve, mock_extract):
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
        mock_retrieve.return_value = (["doc1"], [0.9], ["doc2"], [0.8])
        mock_is_valid.return_value = False
        mock_extract.return_value = "unfiltered result"
        logger = MagicMock()

        result = search_plugin_docs("query", "keywords", logger, plugin_name="invalid")

        assert result == "unfiltered result"


class TestSearchJenkinsDocs:
    @patch("api.tools.tools.extract_top_chunks")
    @patch("api.tools.tools.retrieve_documents")
    def test_returns_result(self, mock_retrieve, mock_extract):
        mock_retrieve.return_value = (["doc1"], [0.9], ["doc2"], [0.8])
        mock_extract.return_value = "jenkins docs result"
        logger = MagicMock()

        result = search_jenkins_docs("query", "keywords", logger)

        assert result == "jenkins docs result"
        mock_retrieve.assert_called_once()
        mock_extract.assert_called_once()


class TestSearchCommunityThreads:
    @patch("api.tools.tools.extract_top_chunks")
    @patch("api.tools.tools.retrieve_documents")
    def test_returns_result_with_semantic_weight(self, mock_retrieve, mock_extract):
        mock_retrieve.return_value = (["doc1"], [0.9], ["doc2"], [0.8])
        mock_extract.return_value = "community result"
        logger = MagicMock()

        result = search_community_threads("query", "keywords", logger)

        assert result == "community result"
        mock_extract.assert_called_once()
        call_kwargs = mock_extract.call_args.kwargs
        assert call_kwargs.get("semantic_weight") == 0.7