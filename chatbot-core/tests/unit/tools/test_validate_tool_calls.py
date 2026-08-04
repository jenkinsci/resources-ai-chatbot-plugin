"""Unit tests for validate_tool_calls in api/tools/utils.py.

Mocks heavy transitive imports (sentence_transformers, faiss, etc.)
so the test can run without ML dependencies installed.
"""
import logging
import sys
import unittest
from unittest.mock import MagicMock

# ------------------------------------------------------------------
# Stub out heavy third-party modules BEFORE importing api.tools.utils.
# Each stub is a MagicMock so any attribute access (function imports)
# will automatically succeed.
# ------------------------------------------------------------------
_STUB_MODULES = [
    "sentence_transformers",
    "faiss",
    "retriv",
    "rag",
    "rag.retriever",
    "rag.retriever.retrieve",
    "rag.retriever.retriever_utils",
    "rag.retriever.retriever_bm25",
    "rag.embedding",
    "rag.embedding.embed_chunks",
    "rag.embedding.embedding_utils",
    "rag.embedding.bm25_indexer",
]
for _mod_name in _STUB_MODULES:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()

from api.tools.utils import validate_tool_calls  # noqa: E402  # pylint: disable=wrong-import-position


class TestValidateToolCalls(unittest.TestCase):
    """Test suite for validate_tool_calls covering crash and message fixes."""

    def setUp(self):
        self.logger = MagicMock(spec=logging.Logger)

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------
    def test_valid_tool_call_returns_true(self):
        """A well-formed tool call with all required params should pass."""
        calls = [{"tool": "search_jenkins_docs", "params": {"query": "pipeline"}}]
        self.assertTrue(validate_tool_calls(calls, self.logger))
        self.logger.warning.assert_not_called()

    def test_multiple_valid_calls(self):
        """Multiple correct calls should all pass."""
        calls = [
            {"tool": "search_jenkins_docs", "params": {"query": "pipeline"}},
            {"tool": "search_community_threads", "params": {"query": "error"}},
        ]
        self.assertTrue(validate_tool_calls(calls, self.logger))

    def test_empty_list_returns_true(self):
        """An empty tool-call list is vacuously valid."""
        self.assertTrue(validate_tool_calls([], self.logger))

    # ------------------------------------------------------------------
    # BUG FIX: missing required param must NOT crash with KeyError
    # ------------------------------------------------------------------
    def test_missing_required_param_returns_false_without_crash(self):
        """When a required param is absent the function must return False,
        not raise KeyError (the original bug)."""
        calls = [{"tool": "search_jenkins_docs", "params": {"keywords": "test"}}]
        result = validate_tool_calls(calls, self.logger)
        self.assertFalse(result)

    def test_missing_param_warning_says_missing(self):
        """The warning for an absent param must say 'missing', not
        'is not expected' (the original misleading message)."""
        calls = [{"tool": "search_jenkins_docs", "params": {}}]
        validate_tool_calls(calls, self.logger)

        warning_messages = [
            str(call) for call in self.logger.warning.call_args_list
        ]
        joined = " ".join(warning_messages)
        self.assertIn("missing", joined.lower())
        self.assertNotIn("is not expected", joined.lower())

    def test_missing_param_does_not_check_type(self):
        """When a param is missing, the type check must be skipped entirely
        (elif, not if)."""
        calls = [{"tool": "search_plugin_docs",
                  "params": {"plugin_name": "git"}}]  # missing 'query'
        validate_tool_calls(calls, self.logger)

        # Should get exactly one warning about 'query' being missing,
        # and no warning about type since the elif should skip it
        type_warnings = [
            call for call in self.logger.warning.call_args_list
            if "expected type" in str(call).lower()
        ]
        self.assertEqual(len(type_warnings), 0)

    # ------------------------------------------------------------------
    # Other invalid cases (pre-existing behaviour)
    # ------------------------------------------------------------------
    def test_unknown_tool_name_returns_false(self):
        """A tool name not in TOOL_SIGNATURES should fail."""
        calls = [{"tool": "nonexistent_tool", "params": {"query": "test"}}]
        self.assertFalse(validate_tool_calls(calls, self.logger))

    def test_wrong_param_type_returns_false(self):
        """A param with the wrong type should fail."""
        calls = [{"tool": "search_jenkins_docs", "params": {"query": 12345}}]
        self.assertFalse(validate_tool_calls(calls, self.logger))

    def test_params_not_dict_returns_false(self):
        """If params is not a dict, validation should fail."""
        calls = [{"tool": "search_jenkins_docs", "params": "not_a_dict"}]
        self.assertFalse(validate_tool_calls(calls, self.logger))


if __name__ == "__main__":
    unittest.main()
