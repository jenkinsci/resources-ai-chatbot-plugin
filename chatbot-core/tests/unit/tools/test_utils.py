"""Unit tests for api.tools.utils."""

from api.tools.utils import is_valid_plugin


def test_is_valid_plugin_returns_true_for_known_plugin():
    """Regression: plugin-name lookup should use the correct catalog path."""
    assert is_valid_plugin("git") is True


def test_is_valid_plugin_returns_false_for_unknown_plugin():
    """Unknown plugins should not match catalog entries."""
    assert is_valid_plugin("plugin-that-does-not-exist-12345") is False
