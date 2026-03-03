"""Regression tests for JSON examples embedded in prompt templates.

Ensures that f-string escaping ({{ / }}) in prompt templates produces
valid JSON when the template placeholders are filled.
"""

import json
import re
import pytest

from api.prompts.prompts import RETRIEVER_AGENT_PROMPT


class TestRetrieverAgentPromptJSON:
    """Validate that JSON tool-call examples in RETRIEVER_AGENT_PROMPT parse correctly."""

    @staticmethod
    def _extract_json_arrays(text: str):
        """Extract all JSON-array-like blocks from rendered prompt text."""
        # Match balanced [ ... ] blocks that look like JSON arrays
        pattern = re.compile(r"\[\s*\{.*?\}\s*\]", re.DOTALL)
        return pattern.findall(text)

    def test_json_examples_are_valid(self):
        """Every tool-call JSON example in the rendered prompt must parse."""
        rendered = RETRIEVER_AGENT_PROMPT.format(
            tools_description="(test tools)",
            user_query="How do I install Jenkins?"
        )
        arrays = self._extract_json_arrays(rendered)
        assert len(arrays) >= 2, (
            f"Expected at least 2 JSON arrays in prompt, found {len(arrays)}"
        )
        for i, block in enumerate(arrays):
            try:
                parsed = json.loads(block)
            except json.JSONDecodeError as exc:
                pytest.fail(
                    f"JSON array #{i} in RETRIEVER_AGENT_PROMPT is invalid: "
                    f"{exc}\n\nBlock:\n{block}"
                )
            assert isinstance(parsed, list)
            for tool_call in parsed:
                assert "tool" in tool_call, f"Missing 'tool' key in {tool_call}"
                assert "params" in tool_call, f"Missing 'params' key in {tool_call}"

    def test_keywords_field_has_closing_quote(self):
        """Regression: the keywords field must not have a missing closing quote (issue #226)."""
        rendered = RETRIEVER_AGENT_PROMPT.format(
            tools_description="(test tools)",
            user_query="test query"
        )
        # All "keywords": "..." values should have balanced quotes
        keyword_pattern = re.compile(r'"keywords"\s*:\s*"([^"]*)"')
        matches = keyword_pattern.findall(rendered)
        assert len(matches) >= 1, "Expected at least one keywords field in prompt"
        for value in matches:
            # Value should be non-empty and not contain unescaped quotes
            assert len(value.strip()) > 0, "keywords value is empty"
