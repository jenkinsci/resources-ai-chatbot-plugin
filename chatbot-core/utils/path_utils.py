"""Utilities for resolving data directories relative to module location."""

import os


def resolve_data_dir(base_file: str, data_dir: str) -> str:
    """
    Resolve a data directory path relative to the module's location.

    Args:
        base_file: The __file__ of the calling module.
        data_dir: The data directory from config (e.g., 'data/raw').

    Returns:
        Absolute path to the resolved data directory.
    """
    script_dir = os.path.dirname(os.path.abspath(base_file))
    return os.path.join(script_dir, "..", data_dir.replace("data/", ""))
