"""Shared JSON loading helpers for GraphRAG input artifacts."""

import json
from pathlib import Path


def load_json_list(path: Path) -> list[object]:
    """
    Load a JSON array from an artifact file.

    Args:
        path (Path): JSON artifact path.

    Returns:
        list[object]: Values stored in the JSON array.

    Raises:
        ValueError: If the JSON root is not an array.
    """
    with path.open(encoding="utf-8") as json_file:
        records = json.load(json_file)

    if not isinstance(records, list):
        raise ValueError(f"JSON artifact must contain a list: {path}")

    return records
