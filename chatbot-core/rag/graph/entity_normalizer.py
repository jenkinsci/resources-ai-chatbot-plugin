"""Normalize plugin entity names against the known plugin index."""

import re
from dataclasses import dataclass
from pathlib import Path

from rag.graph.json_loader import load_json_list


GRAPH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLUGIN_NAMES_PATH = GRAPH_ROOT / "data" / "raw" / "plugin_names.json"
EXPLICIT_PLUGIN_WORDING_IDS = frozenset(
    {
        "coverage",
        "credentials",
        "github",
        "notification",
        "python",
        "release",
        "repository",
        "s3",
        "seed",
        "ssh",
    }
)


@dataclass(frozen=True)
class PluginAliasRule:
    """Metadata used to resolve one plugin alias."""

    plugin_id: str
    requires_explicit_plugin_word: bool = False


def normalize_lookup_value(value: str) -> str:
    """
    Normalize plugin text into a stable lookup key.

    Args:
        value (str): Plugin name or alias to normalize.

    Returns:
        str: Lowercase alphanumeric lookup key.
    """
    normalized_value = value.strip().lower()
    return re.sub(r"[^a-z0-9]+", "", normalized_value)


def load_canonical_plugin_ids(
    path: Path = DEFAULT_PLUGIN_NAMES_PATH,
) -> list[str]:
    """
    Load canonical plugin IDs from the raw plugin index.

    Args:
        path (Path): Path to the plugin names JSON file.

    Returns:
        list[str]: Canonical plugin IDs in file order.
    """
    plugin_ids = load_json_list(path)
    return [
        plugin_id
        for plugin_id in plugin_ids
        if isinstance(plugin_id, str) and plugin_id.strip()
    ]


def build_plugin_aliases(plugin_ids: list[str]) -> dict[str, PluginAliasRule]:
    """
    Build alias mappings for canonical plugin IDs.

    Args:
        plugin_ids (list[str]): Canonical plugin IDs.

    Returns:
        dict[str, PluginAliasRule]: Mapping from alias keys to resolution rules.
    """
    alias_map: dict[str, PluginAliasRule] = {}

    for plugin_id in plugin_ids:
        alias_candidates = {
            plugin_id,
            plugin_id.replace("-", " "),
        }

        if plugin_id.endswith("-plugin"):
            base_name = plugin_id[: -len("-plugin")]
            alias_candidates.update(
                {
                    base_name,
                    base_name.replace("-", " "),
                }
            )

        for alias in alias_candidates:
            alias_key = normalize_lookup_value(alias)
            if alias_key and alias_key not in alias_map:
                alias_map[alias_key] = PluginAliasRule(
                    plugin_id=plugin_id,
                    requires_explicit_plugin_word=(
                        plugin_id in EXPLICIT_PLUGIN_WORDING_IDS
                    ),
                )

    return alias_map


def resolve_plugin_name(
    plugin_name: str,
    plugin_aliases: dict[str, PluginAliasRule],
) -> str | None:
    """
    Resolve plugin text to a canonical plugin ID.

    Args:
        plugin_name (str): Plugin name or alias from a query or chunk.
        plugin_aliases (dict[str, PluginAliasRule]): Alias rules built from
            canonical IDs.

    Returns:
        str | None: Canonical plugin ID when a match is found, otherwise None.
    """
    alias_key = normalize_lookup_value(plugin_name)
    if not alias_key:
        return None
    rule = plugin_aliases.get(alias_key)
    return rule.plugin_id if rule else None


def resolve_plugin_alias(
    plugin_name: str,
    plugin_aliases: dict[str, PluginAliasRule],
) -> PluginAliasRule | None:
    """Resolve plugin text to its complete alias rule."""
    alias_key = normalize_lookup_value(plugin_name)
    return plugin_aliases.get(alias_key) if alias_key else None
