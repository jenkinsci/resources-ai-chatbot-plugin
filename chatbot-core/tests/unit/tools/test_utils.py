"""Unit tests for api/tools/utils.py"""
import unittest
from unittest.mock import MagicMock, patch


class TestMinMaxNormalize(unittest.TestCase):
    """Tests for _min_max_normalize helper."""

    def setUp(self):
        from api.tools.utils import _min_max_normalize
        self.normalize = _min_max_normalize

    def test_empty_list_returns_empty(self):
        self.assertEqual(self.normalize([]), [])

    def test_all_equal_values_returns_half(self):
        result = self.normalize([3.0, 3.0, 3.0])
        self.assertTrue(all(v == 0.5 for v in result))

    def test_normalizes_to_zero_one_range(self):
        result = self.normalize([0.0, 5.0, 10.0])
        self.assertAlmostEqual(min(result), 0.0)
        self.assertAlmostEqual(max(result), 1.0)

    def test_single_value_returns_half(self):
        result = self.normalize([7.0])
        self.assertEqual(result, [0.5])


class TestGetInvertedScores(unittest.TestCase):
    """Tests for get_inverted_scores."""

    def setUp(self):
        from api.tools.utils import get_inverted_scores
        self.get_inverted_scores = get_inverted_scores

    def test_returns_list(self):
        result = self.get_inverted_scores(
            ["a", "b"], [0.1, 0.2],
            ["a", "c"], [1.0, 2.0]
        )
        self.assertIsInstance(result, list)

    def test_all_scores_are_negative(self):
        """Inverted scores should all be negative (for max-heap use)."""
        result = self.get_inverted_scores(
            ["a", "b"], [0.1, 0.9],
            ["a", "b"], [2.0, 1.0]
        )
        for score, _ in result:
            self.assertLessEqual(score, 0.0)

    def test_invalid_semantic_weight_defaults_to_half(self):
        """Out-of-range semantic_weight should default to 0.5."""
        result_invalid = self.get_inverted_scores(
            ["a"], [0.5], ["a"], [1.0], semantic_weight=1.5
        )
        result_default = self.get_inverted_scores(
            ["a"], [0.5], ["a"], [1.0], semantic_weight=0.5
        )
        self.assertEqual(result_invalid[0][0], result_default[0][0])

    def test_empty_inputs_returns_empty(self):
        result = self.get_inverted_scores([], [], [], [])
        self.assertEqual(result, [])

    def test_chunk_ids_preserved_in_output(self):
        result = self.get_inverted_scores(
            ["chunk1"], [0.3],
            ["chunk2"], [1.5]
        )
        ids = [r[1] for r in result]
        self.assertIn("chunk1", ids)
        self.assertIn("chunk2", ids)


class TestValidateToolCalls(unittest.TestCase):
    """Tests for validate_tool_calls."""

    def setUp(self):
        from api.tools.utils import validate_tool_calls
        self.validate = validate_tool_calls
        self.logger = MagicMock()

    def test_valid_jenkins_docs_call(self):
        calls = [{"tool": "search_jenkins_docs", "params": {"query": "how to use jenkins"}}]
        self.assertTrue(self.validate(calls, self.logger))

    def test_invalid_tool_name_returns_false(self):
        calls = [{"tool": "nonexistent_tool", "params": {"query": "test"}}]
        self.assertFalse(self.validate(calls, self.logger))

    def test_missing_required_param_returns_false(self):
        calls = [{"tool": "search_jenkins_docs", "params": {}}]
        self.assertFalse(self.validate(calls, self.logger))

    def test_wrong_param_type_returns_false(self):
        calls = [{"tool": "search_jenkins_docs", "params": {"query": 123}}]
        self.assertFalse(self.validate(calls, self.logger))

    def test_params_not_dict_returns_false(self):
        calls = [{"tool": "search_jenkins_docs", "params": "not a dict"}]
        self.assertFalse(self.validate(calls, self.logger))

    def test_empty_tool_calls_returns_true(self):
        self.assertTrue(self.validate([], self.logger))


class TestGetDefaultToolsCall(unittest.TestCase):
    """Tests for get_default_tools_call."""

    def setUp(self):
        from api.tools.utils import get_default_tools_call
        self.get_default = get_default_tools_call

    def test_returns_four_tools(self):
        result = self.get_default("test query")
        self.assertEqual(len(result), 4)

    def test_all_tools_have_query(self):
        result = self.get_default("jenkins pipeline")
        for call in result:
            self.assertIn("query", call["params"])
            self.assertEqual(call["params"]["query"], "jenkins pipeline")

    def test_tool_names_are_correct(self):
        result = self.get_default("test")
        tool_names = [call["tool"] for call in result]
        self.assertIn("search_jenkins_docs", tool_names)
        self.assertIn("search_plugin_docs", tool_names)
        self.assertIn("search_stackoverflow_threads", tool_names)
        self.assertIn("search_community_threads", tool_names)


class TestFilterRetrievedData(unittest.TestCase):
    """Tests for filter_retrieved_data."""

    def setUp(self):
        from api.tools.utils import filter_retrieved_data
        self.filter_data = filter_retrieved_data

    def _make_chunk(self, title):
        return {"id": title, "metadata": {"title": title}, "chunk_text": "some text"}

    def test_filters_matching_plugin(self):
        semantic = [self._make_chunk("git-plugin"), self._make_chunk("docker-plugin")]
        keyword = [self._make_chunk("git-plugin")]
        sem_result, kw_result = self.filter_data(semantic, keyword, "git-plugin")
        self.assertEqual(len(sem_result), 1)
        self.assertEqual(len(kw_result), 1)

    def test_no_match_returns_empty(self):
        semantic = [self._make_chunk("docker-plugin")]
        keyword = [self._make_chunk("docker-plugin")]
        sem_result, kw_result = self.filter_data(semantic, keyword, "git-plugin")
        self.assertEqual(sem_result, [])
        self.assertEqual(kw_result, [])

    def test_case_insensitive_matching(self):
        semantic = [self._make_chunk("Git-Plugin")]
        keyword = []
        sem_result, _ = self.filter_data(semantic, keyword, "git-plugin")
        self.assertEqual(len(sem_result), 1)


class TestExtractChunksContent(unittest.TestCase):
    """Tests for extract_chunks_content."""

    def setUp(self):
        from api.tools.utils import extract_chunks_content
        self.extract = extract_chunks_content
        self.logger = MagicMock()

    def test_returns_combined_text(self):
        chunks = [
            {"id": "1", "chunk_text": "Hello world", "code_blocks": []},
            {"id": "2", "chunk_text": "Jenkins rocks", "code_blocks": []}
        ]
        result = self.extract(chunks, self.logger)
        self.assertIn("Hello world", result)
        self.assertIn("Jenkins rocks", result)

    def test_empty_chunks_returns_fallback_message(self):
        result = self.extract([], self.logger)
        self.assertEqual(result, "No context available.")

    def test_chunk_missing_id_is_skipped(self):
        chunks = [{"id": "", "chunk_text": "should be skipped", "code_blocks": []}]
        result = self.extract(chunks, self.logger)
        self.assertEqual(result, "No context available.")

    def test_chunk_missing_text_is_skipped(self):
        chunks = [{"id": "1", "chunk_text": "", "code_blocks": []}]
        result = self.extract(chunks, self.logger)
        self.assertEqual(result, "No context available.")

    def test_code_block_placeholder_replaced(self):
        chunks = [{
            "id": "1",
            "chunk_text": "Run this: [[CODE_BLOCK_0]]",
            "code_blocks": ["print('hello')"]
        }]
        result = self.extract(chunks, self.logger)
        self.assertIn("print('hello')", result)


class TestMakePlaceholderReplacer(unittest.TestCase):
    """Tests for make_placeholder_replacer."""

    def setUp(self):
        from api.tools.utils import make_placeholder_replacer
        self.make_replacer = make_placeholder_replacer
        self.logger = MagicMock()

    def test_returns_next_code_block(self):
        code_iter = iter(["print('hello')"])
        replacer = self.make_replacer(code_iter, "chunk1", self.logger)
        result = replacer(MagicMock())
        self.assertEqual(result, "print('hello')")

    def test_returns_missing_code_when_exhausted(self):
        code_iter = iter([])
        replacer = self.make_replacer(code_iter, "chunk1", self.logger)
        result = replacer(MagicMock())
        self.assertEqual(result, "[MISSING_CODE]")
        self.logger.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()