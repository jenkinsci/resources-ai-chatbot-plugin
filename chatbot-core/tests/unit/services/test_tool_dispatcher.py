"""Unit tests for the retrieval tool dispatcher.

Tool selection is driven with a stub ``generate_answer`` and tool execution is
driven by patching only ``TOOL_REGISTRY`` on this module, so neither test needs
the LLM provider or the session memory.
"""

import inspect
import json
import logging

from api.services import tool_dispatcher


def stub_generator(response):
    """Build a generate_answer stub that always returns the given response."""

    def _generate(_prompt, max_tokens=None):  # pylint: disable=unused-argument
        return response

    return _generate


def test_get_agent_tool_calls_parses_valid_payload():
    """Test that a valid, signature-respecting payload is returned untouched."""
    payload = [{"tool": "search_jenkins_docs", "params": {"query": "pipelines"}}]

    result = tool_dispatcher.get_agent_tool_calls(
        "How do pipelines work?", stub_generator(json.dumps(payload)))

    assert result == payload


def test_get_agent_tool_calls_defaults_on_invalid_json(caplog):
    """Test that malformed JSON falls back to the default tool calls."""
    logging.getLogger("API").propagate = True

    with caplog.at_level(logging.WARNING):
        result = tool_dispatcher.get_agent_tool_calls(
            "Some query", stub_generator("{not json"))

    assert result == tool_dispatcher.get_default_tools_call("Some query")
    assert "Invalid JSON syntax in the tools output." in caplog.text


def test_get_agent_tool_calls_defaults_on_bad_signature(caplog):
    """Test that a well-formed payload with the wrong shape falls back too."""
    logging.getLogger("API").propagate = True
    # Param is present but the wrong type, so validation returns False
    # rather than raising.
    payload = [{"tool": "search_jenkins_docs", "params": {"query": 123}}]

    with caplog.at_level(logging.WARNING):
        result = tool_dispatcher.get_agent_tool_calls(
            "Some query", stub_generator(json.dumps(payload)))

    assert result == tool_dispatcher.get_default_tools_call("Some query")
    assert "not respecting the signatures" in caplog.text


def test_execute_search_tools_skips_unknown_tool(caplog):
    """Test that a hallucinated tool name is skipped instead of crashing."""
    logging.getLogger("API").propagate = True

    with caplog.at_level(logging.WARNING):
        result = tool_dispatcher.execute_search_tools(
            [{"tool": "not_a_real_tool", "params": {"query": "test"}}])

    assert result == ""
    assert "Unknown tool 'not_a_real_tool'" in caplog.text


def test_execute_search_tools_injects_logger_only_when_expected(mocker):
    """Test that the logger is injected into tools that accept one, and only those."""
    seen = {}

    def wants_logger(query, logger):
        seen["with_logger"] = logger
        return f"logged:{query}"

    def no_logger(query):
        seen["without_logger"] = True
        return f"plain:{query}"

    mocker.patch.object(
        tool_dispatcher,
        "TOOL_REGISTRY",
        {"wants_logger": wants_logger, "no_logger": no_logger},
    )

    result = tool_dispatcher.execute_search_tools([
        {"tool": "wants_logger", "params": {"query": "a"}},
        {"tool": "no_logger", "params": {"query": "b"}},
    ])

    assert seen["with_logger"] is tool_dispatcher.logger
    assert seen["without_logger"] is True
    assert "logged:a" in result
    assert "plain:b" in result
    # Each tool's output is labelled with the tool that produced it.
    assert "[Result of the search tool wants_logger]" in result
    assert "[Result of the search tool no_logger]" in result


def test_execute_search_tools_handles_missing_params(mocker):
    """Test that a call without a params key still invokes the tool."""
    mocker.patch.object(
        tool_dispatcher, "TOOL_REGISTRY", {"no_args": lambda: "done"})

    result = tool_dispatcher.execute_search_tools([{"tool": "no_args"}])

    assert "done" in result


def test_execute_search_tools_empty_calls():
    """Test that an empty tool call list produces an empty context."""
    assert tool_dispatcher.execute_search_tools([]) == ""


def test_get_agent_tool_calls_signature_is_injectable():
    """Test that the LLM call is a parameter, not a module-level import.

    This is what lets the dispatcher be tested without ``chat_service``.
    """
    params = inspect.signature(tool_dispatcher.get_agent_tool_calls).parameters

    assert "generate_answer" in params
