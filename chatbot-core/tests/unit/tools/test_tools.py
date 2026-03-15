"""Unit tests for the tools module."""
import unittest
from unittest.mock import MagicMock, patch


class TestSearchStackoverflowThreads(unittest.TestCase):
    """Test suite for search_stackoverflow_threads tool."""

    def _make_logger(self):
        return MagicMock()

    @patch("api.tools.tools.retrieve_documents")
    @patch("api.tools.tools.extract_top_chunks")
    def test_returns_extract_top_chunks_result(self, mock_extract, mock_retrieve):
        """Test that the function returns the result of extract_top_chunks."""
        mock_retrieve.return_value = ([], [], [], [])
        mock_extract.return_value = "some result"

        from api.tools.tools import search_stackoverflow_threads
        result = search_stackoverflow_threads("how to use jenkins", "jenkins", self._make_logger())

        self.assertEqual(result, "some result")

    @patch("api.tools.tools.retrieve_documents")
    @patch("api.tools.tools.extract_top_chunks")
    def test_calls_retrieve_documents_with_correct_args(self, mock_extract, mock_retrieve):
        """Test that retrieve_documents is called with query and keywords."""
        mock_retrieve.return_value = ([], [], [], [])
        mock_extract.return_value = ""
        logger = self._make_logger()

        from api.tools.tools import search_stackoverflow_threads
        search_stackoverflow_threads("pipeline error", "pipeline", logger)

        mock_retrieve.assert_called_once()
        call_kwargs = mock_retrieve.call_args.kwargs
        self.assertEqual(call_kwargs["query"], "pipeline error")
        self.assertEqual(call_kwargs["keywords"], "pipeline")

    @patch("api.tools.tools.retrieve_documents")
    @patch("api.tools.tools.extract_top_chunks")
    def test_does_not_return_hardcoded_nothing_relevant(self, mock_extract, mock_retrieve):
        """Test that the stub behaviour is gone — never returns hardcoded 'Nothing relevant'."""
        mock_retrieve.return_value = ([], [], [], [])
        mock_extract.return_value = "No context available."

        from api.tools.tools import search_stackoverflow_threads
        result = search_stackoverflow_threads("any query", "any", self._make_logger())

        self.assertNotEqual(result, "Nothing relevant")


class TestToolSignatures(unittest.TestCase):
    """Test that all tools have consistent signatures."""

    def test_stackoverflow_has_keywords_in_signature(self):
        """Test that TOOL_SIGNATURES includes keywords for stackoverflow."""
        from api.tools.utils import TOOL_SIGNATURES
        self.assertIn("keywords", TOOL_SIGNATURES["search_stackoverflow_threads"])

    def test_default_tool_calls_include_keywords_for_stackoverflow(self):
        """Test that get_default_tools_call includes keywords for stackoverflow."""
        from api.tools.utils import get_default_tools_call
        calls = get_default_tools_call("test query")
        so_call = next(c for c in calls if c["tool"] == "search_stackoverflow_threads")
        self.assertIn("keywords", so_call["params"])


if __name__ == "__main__":
    unittest.main()