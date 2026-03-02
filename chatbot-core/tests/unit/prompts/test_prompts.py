"""Unit tests for prompt constant integrity."""

from api.prompts.prompts import RETRIEVER_AGENT_PROMPT


def test_retriever_agent_prompt_contains_closed_keywords_quote():
    """Regression test: the community-thread example must keep a closed keywords quote."""
    assert '"keywords": "plugin missing dependency upgrade"' in RETRIEVER_AGENT_PROMPT
