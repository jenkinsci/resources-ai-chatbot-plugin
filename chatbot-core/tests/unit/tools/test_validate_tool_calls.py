"""Unit tests for api/tools/utils.py – validate_tool_calls."""
from unittest.mock import MagicMock
from api.tools.utils import validate_tool_calls


class TestValidateToolCalls:
    """Tests for the validate_tool_calls function."""

    def _make_logger(self):
        return MagicMock()

    def test_valid_single_tool_call(self):
        logger = self._make_logger()
        calls = [{"tool": "search_jenkins_docs", "params": {"query": "test"}}]
        assert validate_tool_calls(calls, logger) is True

    def test_valid_multiple_tool_calls(self):
        logger = self._make_logger()
        calls = [
            {"tool": "search_jenkins_docs", "params": {"query": "test"}},
            {"tool": "search_plugin_docs", "params": {"plugin_name": "git", "query": "test"}},
        ]
        assert validate_tool_calls(calls, logger) is True

    def test_unknown_tool_name_returns_false(self):
        logger = self._make_logger()
        calls = [{"tool": "nonexistent_tool", "params": {}}]
        assert validate_tool_calls(calls, logger) is False
        logger.warning.assert_called_once()

    def test_missing_required_param_returns_false_no_crash(self):
        """Issue #306: must not raise KeyError when a required param is absent."""
        logger = self._make_logger()
        calls = [{"tool": "search_jenkins_docs", "params": {"keywords": "test"}}]
        assert validate_tool_calls(calls, logger) is False

    def test_missing_param_logs_correct_message(self):
        """Issue #306: warning should say 'is missing', not 'is not expected'."""
        logger = self._make_logger()
        calls = [{"tool": "search_jenkins_docs", "params": {}}]
        validate_tool_calls(calls, logger)
        warning_msg = logger.warning.call_args[0][0]
        assert "missing" in warning_msg

    def test_wrong_param_type_returns_false(self):
        logger = self._make_logger()
        calls = [{"tool": "search_jenkins_docs", "params": {"query": 123}}]
        assert validate_tool_calls(calls, logger) is False

    def test_none_params_returns_false(self):
        logger = self._make_logger()
        calls = [{"tool": "search_jenkins_docs", "params": None}]
        assert validate_tool_calls(calls, logger) is False

    def test_empty_tool_calls_list(self):
        logger = self._make_logger()
        assert validate_tool_calls([], logger) is True

    def test_missing_multiple_params(self):
        logger = self._make_logger()
        calls = [{"tool": "search_plugin_docs", "params": {}}]
        assert validate_tool_calls(calls, logger) is False
        assert logger.warning.call_count == 2
