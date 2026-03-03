"""
Unit tests for api/tools/utils.py
"""

import json
import pytest
from unittest.mock import MagicMock, patch


class TestValidateToolCalls:
    """Tests for validate_tool_calls function."""

    def test_valid_tool_calls_returns_true(self):
        from api.tools.utils import validate_tool_calls
        mock_logger = MagicMock()
        tool_calls = [
            {"tool": "search_jenkins_docs", "params": {"query": "test"}},
            {"tool": "search_plugin_docs", "params": {"plugin_name": "git", "query": "test"}},
        ]
        result = validate_tool_calls(tool_calls, mock_logger)
        assert result is True

    def test_invalid_tool_name_returns_false(self):
        from api.tools.utils import validate_tool_calls
        mock_logger = MagicMock()
        tool_calls = [
            {"tool": "nonexistent_tool", "params": {"query": "test"}},
        ]
        result = validate_tool_calls(tool_calls, mock_logger)
        assert result is False
        mock_logger.warning.assert_called()

    def test_missing_params_returns_false(self):
        from api.tools.utils import validate_tool_calls
        mock_logger = MagicMock()
        tool_calls = [
            {"tool": "search_jenkins_docs", "params": {}},
        ]
        result = validate_tool_calls(tool_calls, mock_logger)
        assert result is False

    def test_invalid_param_type_returns_false(self):
        from api.tools.utils import validate_tool_calls
        mock_logger = MagicMock()
        tool_calls = [
            {"tool": "search_jenkins_docs", "params": {"query": 123}},
        ]
        result = validate_tool_calls(tool_calls, mock_logger)
        assert result is False

    def test_params_not_dict_returns_false(self):
        from api.tools.utils import validate_tool_calls
        mock_logger = MagicMock()
        tool_calls = [
            {"tool": "search_jenkins_docs", "params": "not a dict"},
        ]
        result = validate_tool_calls(tool_calls, mock_logger)
        assert result is False


class TestMinMaxNormalize:
    """Tests for _min_max_normalize function."""

    def test_normalizes_to_0_1_range(self):
        from api.tools.utils import _min_max_normalize
        values = [0, 25, 50, 75, 100]
        result = _min_max_normalize(values)
        assert result == [0.0, 0.25, 0.5, 0.75, 1.0]

    def test_empty_list_returns_empty(self):
        from api.tools.utils import _min_max_normalize
        result = _min_max_normalize([])
        assert result == []

    def test_identical_values_returns_0_5(self):
        from api.tools.utils import _min_max_normalize
        values = [5, 5, 5]
        result = _min_max_normalize(values)
        assert result == [0.5, 0.5, 0.5]


class TestGetInvertedScores:
    """Tests for get_inverted_scores function."""

    def test_combines_semantic_and_keyword_scores(self):
        from api.tools.utils import get_inverted_scores
        semantic_ids = ["doc1", "doc2"]
        semantic_scores = [0.1, 0.2]
        keyword_ids = ["doc1", "doc3"]
        keyword_scores = [10, 20]

        result = get_inverted_scores(
            semantic_ids, semantic_scores,
            keyword_ids, keyword_scores,
            semantic_weight=0.5
        )
        assert len(result) == 3
        for score, _ in result:
            assert isinstance(score, float)

    def test_handles_empty_inputs(self):
        from api.tools.utils import get_inverted_scores
        result = get_inverted_scores([], [], [], [], semantic_weight=0.5)
        assert result == []

    def test_default_weight_is_0_5(self):
        from api.tools.utils import get_inverted_scores
        semantic_ids = ["doc1"]
        semantic_scores = [0.1]
        keyword_ids = ["doc1"]
        keyword_scores = [10]

        result = get_inverted_scores(
            semantic_ids, semantic_scores,
            keyword_ids, keyword_scores
        )
        assert len(result) == 1


class TestExtractChunksContent:
    """Tests for extract_chunks_content function."""

    def test_extracts_chunk_text(self):
        from api.tools.utils import extract_chunks_content
        mock_logger = MagicMock()
        chunks = [
            {"id": "doc1", "chunk_text": "Hello world", "code_blocks": []},
            {"id": "doc2", "chunk_text": "Foo bar", "code_blocks": []},
        ]
        result = extract_chunks_content(chunks, mock_logger)
        assert "Hello world" in result
        assert "Foo bar" in result

    def test_warns_on_missing_id(self):
        from api.tools.utils import extract_chunks_content
        mock_logger = MagicMock()
        chunks = [
            {"chunk_text": "Hello world", "code_blocks": []},
        ]
        result = extract_chunks_content(chunks, mock_logger)
        mock_logger.warning.assert_called()
        assert result == ""

    def test_warns_on_missing_text(self):
        from api.tools.utils import extract_chunks_content
        mock_logger = MagicMock()
        chunks = [
            {"id": "doc1", "code_blocks": []},
        ]
        result = extract_chunks_content(chunks, mock_logger)
        mock_logger.warning.assert_called()


class TestIsValidPlugin:
    """Tests for is_valid_plugin function."""

    @patch("api.tools.utils.open")
    @patch("os.path.abspath")
    def test_valid_plugin_returns_true(self, mock_abspath, mock_open):
        from api.tools.utils import is_valid_plugin
        mock_abspath.return_value = "/fake/path"
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
            ["git", "docker", "kubernetes"]
        )
        result = is_valid_plugin("git")
        assert result is True

    @patch("api.tools.utils.open")
    @patch("os.path.abspath")
    def test_invalid_plugin_returns_false(self, mock_abspath, mock_open):
        from api.tools.utils import is_valid_plugin
        mock_abspath.return_value = "/fake/path"
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
            ["git", "docker"]
        )
        result = is_valid_plugin("nonexistent")
        assert result is False

    @patch("api.tools.utils.open")
    @patch("os.path.abspath")
    def test_handles_hyphen_in_plugin_name(self, mock_abspath, mock_open):
        from api.tools.utils import is_valid_plugin
        mock_abspath.return_value = "/fake/path"
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
            ["pipeline-aws"]
        )
        result = is_valid_plugin("pipeline-aws")
        assert result is True
