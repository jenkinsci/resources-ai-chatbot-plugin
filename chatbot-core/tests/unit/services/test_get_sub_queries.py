"""Unit tests for _get_sub_queries hardening (issue #228).

Covers: non-list payloads, mixed types, empty-after-normalization,
whitespace-only strings, and the normal happy path.
"""

import pytest
from unittest.mock import MagicMock, patch


@patch("api.services.chat_service.generate_answer")
@patch("api.services.chat_service.logger")
class TestGetSubQueries:
    """Tests for _get_sub_queries type/shape validation."""

    def _call(self, raw_llm_output, mock_logger, mock_generate):
        """Helper: patch generate_answer to return *raw_llm_output*, then call."""
        mock_generate.return_value = raw_llm_output
        from api.services.chat_service import _get_sub_queries
        return _get_sub_queries("original query")

    # --- happy path ---

    def test_valid_list_of_strings(self, mock_logger, mock_generate):
        result = self._call('["sub query 1", "sub query 2"]', mock_logger, mock_generate)
        assert result == ["sub query 1", "sub query 2"]

    def test_single_element_list(self, mock_logger, mock_generate):
        result = self._call('["only one"]', mock_logger, mock_generate)
        assert result == ["only one"]

    # --- non-list payloads ---

    def test_parsed_dict_falls_back(self, mock_logger, mock_generate):
        result = self._call('{"key": "value"}', mock_logger, mock_generate)
        assert result == ["original query"]
        mock_logger.warning.assert_called()

    def test_parsed_int_falls_back(self, mock_logger, mock_generate):
        result = self._call("42", mock_logger, mock_generate)
        assert result == ["original query"]
        mock_logger.warning.assert_called()

    def test_parsed_string_falls_back(self, mock_logger, mock_generate):
        result = self._call('"just a string"', mock_logger, mock_generate)
        assert result == ["original query"]
        mock_logger.warning.assert_called()

    def test_parsed_none_falls_back(self, mock_logger, mock_generate):
        result = self._call("None", mock_logger, mock_generate)
        assert result == ["original query"]
        mock_logger.warning.assert_called()

    # --- mixed-type lists ---

    def test_mixed_types_filters_non_strings(self, mock_logger, mock_generate):
        result = self._call('["valid", 123, None, "also valid"]', mock_logger, mock_generate)
        assert result == ["valid", "also valid"]

    def test_list_of_ints_falls_back(self, mock_logger, mock_generate):
        result = self._call("[1, 2, 3]", mock_logger, mock_generate)
        assert result == ["original query"]

    def test_nested_list_filters_inner_lists(self, mock_logger, mock_generate):
        result = self._call('[["nested"], "flat"]', mock_logger, mock_generate)
        assert result == ["flat"]

    # --- empty-after-normalization ---

    def test_empty_list_falls_back(self, mock_logger, mock_generate):
        result = self._call("[]", mock_logger, mock_generate)
        assert result == ["original query"]

    def test_whitespace_only_strings_falls_back(self, mock_logger, mock_generate):
        result = self._call('["  ", "\\t", "\\n"]', mock_logger, mock_generate)
        assert result == ["original query"]

    # --- parse errors ---

    def test_unparseable_string_falls_back(self, mock_logger, mock_generate):
        result = self._call("not valid python", mock_logger, mock_generate)
        assert result == ["original query"]
        mock_logger.warning.assert_called()

    def test_malformed_json_falls_back(self, mock_logger, mock_generate):
        result = self._call('["missing closing bracket"', mock_logger, mock_generate)
        assert result == ["original query"]

    # --- whitespace normalization ---

    def test_strips_whitespace_from_items(self, mock_logger, mock_generate):
        result = self._call('["  padded  ", "\\tquery\\n"]', mock_logger, mock_generate)
        assert result == ["padded", "query"]

    def test_fallback_strips_original_query(self, mock_logger, mock_generate):
        """Ensure fallback also strips whitespace from original query."""
        mock_generate.return_value = "not valid python"
        from api.services.chat_service import _get_sub_queries
        result = _get_sub_queries("  padded original  ")
        assert result == ["padded original"]

    # --- tuple input (allowed by isinstance check) ---

    def test_tuple_input_is_accepted(self, mock_logger, mock_generate):
        result = self._call('("sub1", "sub2")', mock_logger, mock_generate)
        assert result == ["sub1", "sub2"]
