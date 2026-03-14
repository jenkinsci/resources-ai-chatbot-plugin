"""Unit tests for api.tools.utils contract helpers."""

from unittest.mock import MagicMock

from api.tools.utils import get_default_tools_call, validate_tool_calls


def _get_tool_call(tool_calls, tool_name):
    """Return a specific tool call dict by tool name."""
    return next(call for call in tool_calls if call["tool"] == tool_name)


def test_get_default_tools_call_includes_keywords_for_hybrid_tools():
    """Fallback tool calls must include keywords where required by tool signatures."""
    query = "jenkins plugin dependency issue"
    tool_calls = get_default_tools_call(query)

    jenkins_docs_call = _get_tool_call(tool_calls, "search_jenkins_docs")
    plugin_docs_call = _get_tool_call(tool_calls, "search_plugin_docs")
    community_call = _get_tool_call(tool_calls, "search_community_threads")
    stackoverflow_call = _get_tool_call(tool_calls, "search_stackoverflow_threads")

    assert jenkins_docs_call["params"]["keywords"] == query
    assert plugin_docs_call["params"]["keywords"] == query
    assert community_call["params"]["keywords"] == query
    assert "keywords" not in stackoverflow_call["params"]


def test_validate_tool_calls_accepts_optional_plugin_name_none():
    """validator should accept plugin_name=None because tool signature allows it."""
    logger = MagicMock()
    tool_calls = [
        {
            "tool": "search_plugin_docs",
            "params": {
                "query": "how to configure github plugin",
                "keywords": "configure github plugin",
                "plugin_name": None,
            },
        }
    ]

    assert validate_tool_calls(tool_calls, logger) is True
    logger.warning.assert_not_called()


def test_validate_tool_calls_rejects_missing_keywords_without_crashing():
    """Missing required params should fail validation and not raise exceptions."""
    logger = MagicMock()
    tool_calls = [
        {
            "tool": "search_jenkins_docs",
            "params": {"query": "how to configure credentials"},
        }
    ]

    assert validate_tool_calls(tool_calls, logger) is False
    logger.warning.assert_called_with(
        "Tool: %s: Param %s is missing.", "search_jenkins_docs", "keywords"
    )


def test_validate_tool_calls_handles_non_dict_params():
    """Non-dict params payload must fail validation gracefully."""
    logger = MagicMock()
    tool_calls = [
        {
            "tool": "search_community_threads",
            "params": None,
        }
    ]

    assert validate_tool_calls(tool_calls, logger) is False
    logger.warning.assert_called_with(
        "Params for tool %s is not a dict.", "search_community_threads"
    )
