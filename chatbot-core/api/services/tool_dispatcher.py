"""Selection and execution of the retrieval tools used by the agentic pipeline.

``get_agent_tool_calls`` asks the LLM which tools to call for a query and
falls back to a safe default whenever the model's output cannot be trusted.
``execute_search_tools`` runs the resulting calls against ``TOOL_REGISTRY``.
"""

import json
import inspect
from typing import Callable

from api.config.loader import CONFIG
from api.prompts.prompts import RETRIEVER_AGENT_PROMPT
from api.tools.sanitizer import sanitize_log_payload
from api.tools.tools import TOOL_REGISTRY
from api.tools.utils import get_default_tools_call, validate_tool_calls
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")
llm_config = CONFIG["llm"]

# Signature of the answer generator injected by the caller:
# (prompt, max_tokens=None) -> str
GenerateAnswer = Callable[..., str]


def get_agent_tool_calls(query: str, generate_answer: GenerateAnswer):
    """
    Uses a prompt to determine which tools should be used for information retrieval.

    Args:
        query (str): The user query.
        generate_answer (GenerateAnswer): Callable used to query the LLM.

    Returns:
        Any: A parsed representation of tool calls, validated or defaulted.
    """
    retriever_agent_prompt = RETRIEVER_AGENT_PROMPT.format(user_query=query)

    tool_calls = generate_answer(
        retriever_agent_prompt, llm_config["max_tokens_retriever_agent"] + (len(query) * 3))

    logger.debug("Tool calls: %s", sanitize_log_payload(tool_calls))
    try:
        tool_calls_parsed = json.loads(tool_calls)
        if not validate_tool_calls(tool_calls_parsed, logger):
            logger.warning("Tool calls are not respecting the signatures."
                           "Going for the default config")
            tool_calls_parsed = get_default_tools_call(query)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON syntax in the tools output.")
        logger.debug("Raw tool calls payload: %s",
                     sanitize_log_payload(tool_calls))
        logger.warning("Calling all the search tools with default settings.")
        tool_calls_parsed = get_default_tools_call(query)
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        logger.warning(
            "JSON structure or value error(%s %s) in the tools output.",
            type(e).__name__,
            e)
        logger.debug("Raw tool calls payload: %s",
                     sanitize_log_payload(tool_calls))
        logger.warning("Calling all the search tools with default settings.")
        tool_calls_parsed = get_default_tools_call(query)

    return tool_calls_parsed


def execute_search_tools(tool_calls) -> str:
    """
    Executes the tool calls to retrieve relevant context information.

    Args:
        tool_calls: A list of tool call specifications with tool names and parameters.

    Returns:
        str: Combined output from all retrieval tools.
    """
    retrieved_results = []
    for call in tool_calls:
        tool_name = call.get("tool")
        params = call.get("params") or {}

        tool_fn = TOOL_REGISTRY.get(tool_name)

        if tool_fn is None:
            logger.warning("Unknown tool '%s' — skipping.", tool_name)
            continue

        # Check if the tool actually expects a logger before injecting it
        if "logger" in inspect.signature(tool_fn).parameters:
            params.setdefault("logger", logger)

        result = tool_fn(**params)
        retrieved_results.append({
            "tool": tool_name,
            "output": result
        })

    return "\n\n".join(
        f"[Result of the search tool {res['tool']}]:\n{res.get('output', '')}".strip(
        )
        for res in retrieved_results
    )
