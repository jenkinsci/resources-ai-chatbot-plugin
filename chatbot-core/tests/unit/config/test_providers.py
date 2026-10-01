"""Tests for the lightweight provider catalog loader."""

import json
from pathlib import Path

import pytest

from api.config.providers import load_provider_catalog


def write_catalog(tmp_path: Path, providers: list[dict]) -> Path:
    """Write a temporary catalog for a loader test."""
    catalog_path = tmp_path / "providers.json"
    catalog_path.write_text(json.dumps({"providers": providers}), encoding="utf-8")
    return catalog_path


def test_load_catalog_reads_checked_in_catalog() -> None:
    """The repository catalog should load with all standard providers."""
    providers = load_provider_catalog()

    assert [provider.id for provider in providers] == [
        "local",
        "groq",
        "openrouter",
        "gemini",
        "anthropic",
        "openai",
    ]


def test_load_catalog_derives_api_key_environment_name(tmp_path: Path) -> None:
    """Provider IDs should determine stable API-key environment names."""
    catalog_path = write_catalog(
        tmp_path,
        [{"id": "openrouter", "label": "OpenRouter", "model": "openrouter/model"}],
    )

    provider = load_provider_catalog(catalog_path)[0]

    assert provider.api_key_env == "OPENROUTER_API_KEY"


def test_load_catalog_normalizes_provider_id(tmp_path: Path) -> None:
    """Provider IDs should be trimmed and normalized to lowercase."""
    catalog_path = write_catalog(
        tmp_path,
        [{"id": "  GroQ  ", "label": " Groq API ", "model": " model "}],
    )

    provider = load_provider_catalog(catalog_path)[0]

    assert provider.id == "groq"
    assert provider.label == "Groq API"
    assert provider.model == "model"
    assert provider.api_key_env == "GROQ_API_KEY"


def test_load_catalog_rejects_duplicate_ids(tmp_path: Path) -> None:
    """Provider IDs must uniquely identify catalog entries."""
    catalog_path = write_catalog(
        tmp_path,
        [
            {"id": "Groq", "label": "Groq", "model": "groq/model-a"},
            {"id": "groq", "label": "Groq Two", "model": "groq/model-b"},
        ],
    )

    with pytest.raises(ValueError, match="must be unique"):
        load_provider_catalog(catalog_path)


def test_load_catalog_rejects_empty_catalog(tmp_path: Path) -> None:
    """The application must have at least one selectable provider."""
    catalog_path = write_catalog(tmp_path, [])

    with pytest.raises(ValueError, match="at least 1 item"):
        load_provider_catalog(catalog_path)


def test_load_catalog_rejects_unknown_fields(tmp_path: Path) -> None:
    """Catalog entries should not silently accept unsupported settings."""
    catalog_path = write_catalog(
        tmp_path,
        [
            {
                "id": "groq",
                "label": "Groq",
                "model": "groq/model",
                "api_key_env": "GROQ_API_KEY",
            }
        ],
    )

    with pytest.raises(ValueError, match="Invalid provider configuration"):
        load_provider_catalog(catalog_path)


def test_load_catalog_rejects_invalid_json(tmp_path: Path) -> None:
    """Malformed catalog JSON should produce a concise configuration error."""
    catalog_path = tmp_path / "providers.json"
    catalog_path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON in provider catalog"):
        load_provider_catalog(catalog_path)


def test_load_catalog_rejects_missing_file(tmp_path: Path) -> None:
    """A missing catalog should produce a clear configuration error."""
    catalog_path = tmp_path / "missing-providers.json"

    with pytest.raises(ValueError, match="Provider catalog not found"):
        load_provider_catalog(catalog_path)
