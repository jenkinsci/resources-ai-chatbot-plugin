"""Regression tests for provider key synchronization."""

from pathlib import Path

import pytest
from dotenv import dotenv_values

from api.config.env_sync import sync_provider_env
from api.config.providers import ProviderDefinition


@pytest.mark.parametrize("assignment", [
    "GROQ_API_KEY=example-only",
    "GROQ_API_KEY = example-only",
    "export GROQ_API_KEY=example-only",
    'export GROQ_API_KEY = "example-only" # keep comment',
    "GROQ_API_KEY\t=\t'example-only'",
    "GROQ_API_KEY='example # value = with spaces'",
])
@pytest.mark.parametrize("managed", [False, True])
def test_sync_preserves_valid_assignments(tmp_path: Path, assignment: str, managed: bool):
    """Accepted dotenv syntax keeps its value across repeated synchronization."""
    env_path = tmp_path / ".env"
    source = assignment + "\n"
    if managed:
        source = ("# LiteLLM provider keys - managed\n" + source
                  + "# End LiteLLM provider keys\n")
    env_path.write_text("UNRELATED=keep\n" + source, encoding="utf-8")
    before = dotenv_values(env_path)
    providers = [ProviderDefinition(id="groq", label="Groq", model="groq/example")]

    sync_provider_env(providers, env_path)

    assert dotenv_values(env_path) == before
    first_output = env_path.read_text(encoding="utf-8")
    assert first_output.count("GROQ_API_KEY") == 1
    sync_provider_env(providers, env_path)
    assert env_path.read_text(encoding="utf-8") == first_output


def test_sync_uses_last_assignment_and_adds_missing_key(tmp_path: Path):
    """Duplicate keys follow dotenv precedence; absent providers get placeholders."""
    env_path = tmp_path / ".env"
    env_path.write_text(
        "GROQ_API_KEY=old\nexport GROQ_API_KEY = new\n", encoding="utf-8"
    )
    providers = [
        ProviderDefinition(id="groq", label="Groq", model="groq/example"),
        ProviderDefinition(id="openai", label="OpenAI", model="openai/example"),
    ]

    sync_provider_env(providers, env_path)

    assert dotenv_values(env_path) == {"GROQ_API_KEY": "new", "OPENAI_API_KEY": ""}
    assert env_path.read_text(encoding="utf-8").count("GROQ_API_KEY") == 1
