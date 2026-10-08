"""Unit tests for api/tools/utils.py."""

import logging

import pytest

from api.tools.utils import validate_tool_calls


@pytest.fixture(name="logger")
def logger_fixture():
    """Logger whose records pytest can capture."""
    log = logging.getLogger("API")
    log.propagate = True
    return log


def test_validate_tool_calls_accepts_valid_call(logger):
    """Test that a well-formed call passes validation."""
    calls = [{"tool": "search_jenkins_docs", "params": {"query": "pipelines"}}]

    assert validate_tool_calls(calls, logger) is True


def test_validate_tool_calls_accepts_multi_param_tool(logger):
    """Test a tool whose signature has more than one parameter."""
    calls = [{
        "tool": "search_plugin_docs",
        "params": {"plugin_name": "git", "query": "checkout"},
    }]

    assert validate_tool_calls(calls, logger) is True


def test_validate_tool_calls_accepts_empty_list(logger):
    """Test that no tool calls is vacuously valid."""
    assert validate_tool_calls([], logger) is True


def test_validate_tool_calls_rejects_unknown_tool(logger, caplog):
    """Test that a tool outside the registry is rejected."""
    calls = [{"tool": "hallucinated_tool", "params": {"query": "x"}}]

    with caplog.at_level(logging.WARNING):
        assert validate_tool_calls(calls, logger) is False

    assert "Tool hallucinated_tool not available." in caplog.text


def test_validate_tool_calls_missing_param_returns_false(logger, caplog):
    """Test that a missing required param returns False instead of raising.

    Regression test for #306: the missing-param branch used to fall through
    to ``params[param_name]``, raising KeyError on the key it had just
    reported as absent.
    """
    calls = [{"tool": "search_jenkins_docs", "params": {"keywords": "test"}}]

    with caplog.at_level(logging.WARNING):
        result = validate_tool_calls(calls, logger)

    assert result is False
    assert "Param query is missing" in caplog.text


def test_validate_tool_calls_missing_param_does_not_raise(logger):
    """Test explicitly that no exception escapes when a param is absent."""
    calls = [{"tool": "search_plugin_docs", "params": {"plugin_name": "git"}}]

    try:
        result = validate_tool_calls(calls, logger)
    except KeyError as exc:  # pragma: no cover - the bug this guards against
        pytest.fail(f"validate_tool_calls raised KeyError: {exc}")

    assert result is False


def test_validate_tool_calls_rejects_wrong_param_type(logger, caplog):
    """Test that a param of the wrong type is rejected."""
    calls = [{"tool": "search_jenkins_docs", "params": {"query": 123}}]

    with caplog.at_level(logging.WARNING):
        assert validate_tool_calls(calls, logger) is False

    assert "Param query is not of the expected type str" in caplog.text


def test_validate_tool_calls_rejects_non_dict_params(logger, caplog):
    """Test that non-dict params are rejected without a TypeError.

    The membership test below the guard would raise TypeError on a
    non-container, so the guard has to stop processing this call.
    """
    calls = [{"tool": "search_jenkins_docs", "params": "query=pipelines"}]

    with caplog.at_level(logging.WARNING):
        result = validate_tool_calls(calls, logger)

    assert result is False
    assert "Params for tool search_jenkins_docs is not a dict." in caplog.text


def test_validate_tool_calls_rejects_missing_params_key(logger):
    """Test that a call with no params key at all is rejected cleanly."""
    assert validate_tool_calls([{"tool": "search_jenkins_docs"}], logger) is False


def test_validate_tool_calls_reports_every_invalid_call(logger, caplog):
    """Test that validation does not stop at the first bad call."""
    calls = [
        {"tool": "search_jenkins_docs", "params": {"keywords": "a"}},
        {"tool": "another_hallucination", "params": {"query": "b"}},
    ]

    with caplog.at_level(logging.WARNING):
        assert validate_tool_calls(calls, logger) is False

    assert "Param query is missing" in caplog.text
    assert "Tool another_hallucination not available." in caplog.text


def test_validate_tool_calls_valid_call_logs_nothing(logger, caplog):
    """Test that a valid call produces no warnings."""
    calls = [{"tool": "search_jenkins_docs", "params": {"query": "pipelines"}}]

    with caplog.at_level(logging.WARNING):
        validate_tool_calls(calls, logger)

    assert caplog.text == ""
