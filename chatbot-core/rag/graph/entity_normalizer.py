"""Normalize plugin entity names against the known plugin index."""

import json
import re
from pathlib import Path


GRAPH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLUGIN_NAMES_PATH = GRAPH_ROOT / "data" / "raw" / "plugin_names.json"


def normalize_lookup_value(value: str) -> str:
    """
    Normalize a plugin name into a stable lookup key.

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
    Load canonical plugin IDs from the raw plugin index file.

    Args:
        path (Path): Path to the plugin names JSON file.

    Returns:
        list[str]: Canonical plugin IDs in file order.
    """
    with path.open(encoding="utf-8") as plugin_names_file:
        plugin_ids = json.load(plugin_names_file)
    return [plugin_id for plugin_id in plugin_ids if isinstance(plugin_id, str)]


def build_plugin_aliases(plugin_ids: list[str]) -> dict[str, str]:
    """
    Build normalized alias mappings for canonical plugin IDs.

    Args:
        plugin_ids (list[str]): Canonical plugin IDs.

    Returns:
        dict[str, str]: Mapping from normalized alias key to canonical ID.
    """
    alias_map = {}

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
                alias_map[alias_key] = plugin_id

    return alias_map


def resolve_plugin_name(
    plugin_name: str,
    plugin_aliases: dict[str, str],
) -> str | None:
    """
    Resolve a plugin name or alias to a canonical plugin ID.

    Args:
        plugin_name (str): Plugin name or alias from a query or chunk.
        plugin_aliases (dict[str, str]): Alias map built from canonical IDs.

    Returns:
        str | None: Canonical plugin ID when a match is found, otherwise None.
    """
    alias_key = normalize_lookup_value(plugin_name)
    if not alias_key:
        return None
    return plugin_aliases.get(alias_key)
