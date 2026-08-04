"""Unit tests for plugin name caching and validation in tools/utils.py."""
import json
import unittest
from unittest.mock import patch, mock_open

from api.tools.utils import (
    is_valid_plugin,
    load_plugin_names,
    filter_retrieved_data,
)

SAMPLE_PLUGINS = json.dumps(
    ["git", "blue-ocean", "credentials", "github-branch-source"]
)


class TestIsValidPlugin(unittest.TestCase):
    """Tests for the is_valid_plugin function."""

    def setUp(self):
        load_plugin_names.cache_clear()

    def tearDown(self):
        load_plugin_names.cache_clear()

    @patch(
        "builtins.open",
        mock_open(read_data=SAMPLE_PLUGINS),
    )
    @patch("os.path.dirname", return_value="/fake/dir")
    def test_exact_match(self, _mock_dir):
        """Exact plugin name should be valid."""
        self.assertTrue(is_valid_plugin("git"))

    @patch(
        "builtins.open",
        mock_open(read_data=SAMPLE_PLUGINS),
    )
    @patch("os.path.dirname", return_value="/fake/dir")
    def test_case_insensitive_match(self, _mock_dir):
        """Plugin names should match case-insensitively."""
        self.assertTrue(is_valid_plugin("Git"))
        self.assertTrue(is_valid_plugin("GIT"))

    @patch(
        "builtins.open",
        mock_open(read_data=SAMPLE_PLUGINS),
    )
    @patch("os.path.dirname", return_value="/fake/dir")
    def test_hyphen_insensitive_match(self, _mock_dir):
        """Hyphens should be ignored during matching."""
        self.assertTrue(is_valid_plugin("blue ocean"))
        self.assertTrue(is_valid_plugin("blueocean"))
        self.assertTrue(is_valid_plugin("Blue-Ocean"))

    @patch(
        "builtins.open",
        mock_open(read_data=SAMPLE_PLUGINS),
    )
    @patch("os.path.dirname", return_value="/fake/dir")
    def test_invalid_plugin_returns_false(self, _mock_dir):
        """Non-existent plugin name should return False."""
        self.assertFalse(is_valid_plugin("nonexistent-plugin"))
        self.assertFalse(is_valid_plugin(""))


class TestFilterRetrievedData(unittest.TestCase):
    """Tests for filter_retrieved_data using the shared tokenizer."""

    def test_filters_matching_entries(self):
        """Only entries whose title matches the plugin name should remain."""
        semantic_data = [
            {"metadata": {"title": "blue-ocean"}, "chunk_text": "a"},
            {"metadata": {"title": "credentials"}, "chunk_text": "b"},
        ]
        keyword_data = [
            {"metadata": {"title": "Blue Ocean"}, "chunk_text": "c"},
            {"metadata": {"title": "git"}, "chunk_text": "d"},
        ]
        sem, kw = filter_retrieved_data(
            semantic_data, keyword_data, "blue-ocean"
        )
        self.assertEqual(len(sem), 1)
        self.assertEqual(sem[0]["chunk_text"], "a")
        self.assertEqual(len(kw), 1)
        self.assertEqual(kw[0]["chunk_text"], "c")

    def test_returns_empty_when_no_match(self):
        """No results should be returned when nothing matches."""
        data = [{"metadata": {"title": "git"}, "chunk_text": "x"}]
        sem, kw = filter_retrieved_data(data, data, "nonexistent")
        self.assertEqual(len(sem), 0)
        self.assertEqual(len(kw), 0)

    def test_empty_input(self):
        """Empty input lists should return empty lists."""
        sem, kw = filter_retrieved_data([], [], "git")
        self.assertEqual(sem, [])
        self.assertEqual(kw, [])


class TestPluginNameCacheIntegration(unittest.TestCase):
    """Integration tests verifying lru_cache behaviour through the public API.

    These tests confirm that plugin_names.json is read from disk exactly
    once, regardless of how many times public functions that depend on the
    cached data are called.
    """

    def setUp(self):
        load_plugin_names.cache_clear()

    def tearDown(self):
        load_plugin_names.cache_clear()

    @patch("os.path.dirname", return_value="/fake/dir")
    def test_multiple_is_valid_plugin_calls_read_file_once(self, _mock_dir):
        """Repeated is_valid_plugin() calls should hit the cache, not disk."""
        with patch(
            "builtins.open", mock_open(read_data=SAMPLE_PLUGINS)
        ) as mocked_file:
            is_valid_plugin("git")
            is_valid_plugin("blue-ocean")
            is_valid_plugin("nonexistent")
            mocked_file.assert_called_once()

    @patch("os.path.dirname", return_value="/fake/dir")
    def test_cache_shared_across_public_functions(self, _mock_dir):
        """is_valid_plugin and load_plugin_names should share the same cache."""
        with patch(
            "builtins.open", mock_open(read_data=SAMPLE_PLUGINS)
        ) as mocked_file:
            # First access via is_valid_plugin populates the cache
            is_valid_plugin("git")
            # Direct call should reuse the cached result
            result = load_plugin_names()
            self.assertIsInstance(result, frozenset)
            mocked_file.assert_called_once()

    @patch("os.path.dirname", return_value="/fake/dir")
    def test_cache_clear_forces_reload(self, _mock_dir):
        """After cache_clear(), the next call should re-read the file."""
        with patch(
            "builtins.open", mock_open(read_data=SAMPLE_PLUGINS)
        ) as mocked_file:
            is_valid_plugin("git")
            self.assertEqual(mocked_file.call_count, 1)

            load_plugin_names.cache_clear()

            is_valid_plugin("git")
            self.assertEqual(mocked_file.call_count, 2)


if __name__ == "__main__":
    unittest.main()
