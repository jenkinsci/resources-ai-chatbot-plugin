"""Unit tests for GraphRAG entity normalization."""

import json

from rag.graph.entity_normalizer import (
    build_plugin_aliases,
    load_canonical_plugin_ids,
    normalize_lookup_value,
    resolve_plugin_name,
)


def test_normalize_lookup_value_removes_case_and_separators():
    """
    Verify plugin aliases normalize to stable lookup keys.
    """
    assert normalize_lookup_value("Blue Ocean") == "blueocean"
    assert normalize_lookup_value("BLUE OCEAN") == "blueocean"
    assert normalize_lookup_value("matrix-auth-plugin") == "matrixauthplugin"


def test_load_canonical_plugin_ids_keeps_string_values(tmp_path):
    """
    Verify plugin IDs are loaded from JSON and non-string values are skipped.
    """
    plugin_names_path = tmp_path / "plugin_names.json"
    plugin_names_path.write_text(
        json.dumps(["blueocean", 123, "git", None]),
        encoding="utf-8",
    )

    plugin_ids = load_canonical_plugin_ids(plugin_names_path)

    assert plugin_ids == ["blueocean", "git"]


def test_build_plugin_aliases_resolves_common_name_forms():
    """
    Verify aliases resolve spaced, cased, and plugin-suffixed forms.
    """
    aliases = build_plugin_aliases(
        [
            "blueocean",
            "matrix-auth-plugin",
            "git-client",
        ]
    )

    assert resolve_plugin_name("Blue Ocean", aliases) == "blueocean"
    assert resolve_plugin_name("BLUE OCEAN", aliases) == "blueocean"
    assert resolve_plugin_name("blueocean", aliases) == "blueocean"
    assert resolve_plugin_name("matrix auth", aliases) == "matrix-auth-plugin"
    assert resolve_plugin_name("Matrix Auth Plugin", aliases) == "matrix-auth-plugin"
    assert resolve_plugin_name("git client", aliases) == "git-client"


def test_resolve_plugin_name_returns_none_for_unknown_alias():
    """
    Verify unknown plugin names do not resolve to graph entities.
    """
    aliases = build_plugin_aliases(["blueocean"])

    assert resolve_plugin_name("not a real plugin", aliases) is None
    assert resolve_plugin_name("   ", aliases) is None
