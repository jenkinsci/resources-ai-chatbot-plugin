"""Unit tests for prompt constant integrity."""

import json
import re

from api.prompts.prompts import RETRIEVER_AGENT_PROMPT


def _extract_tool_call_examples(prompt: str) -> list[list[dict]]:
    """Extract and parse JSON tool-call arrays from retriever prompt examples."""
    pattern = r"Tool calls:\s*(\[[\s\S]*?\])\s*###"
    raw_examples = re.findall(pattern, prompt)
    parsed_examples = []

    for example in raw_examples:
        normalized = example.replace("{{", "{").replace("}}", "}")
        parsed_examples.append(json.loads(normalized))

    return parsed_examples


def test_retriever_agent_prompt_examples_are_valid_json_and_keep_keywords():
    """Ensure retriever examples stay parseable and retain expected community keywords."""
    examples = _extract_tool_call_examples(RETRIEVER_AGENT_PROMPT)
    assert len(examples) == 2

    community_calls = [
        call
        for example in examples
        for call in example
        if call.get("tool") == "search_community_threads"
    ]
    assert community_calls
    assert community_calls[0]["params"]["keywords"] == "plugin missing dependency upgrade"
