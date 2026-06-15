"""Validate generated response artifacts."""

import argparse
import json
from pathlib import Path
from typing import Any


def has_valid_retrieval_context(retrieval_context: Any) -> bool:
    """
    Check whether retrieval context matches the eval artifact contract.

    Args:
        retrieval_context (Any): Retrieval context value to validate.

    Returns:
        bool: True when retrieval context is a non-empty list of non-empty
        strings, otherwise False.
    """
    return isinstance(retrieval_context, list) and bool(retrieval_context) and all(
        isinstance(value, str) and value.strip() for value in retrieval_context
    )


def validate_entries(entries: Any, expected_count: int | None = None) -> list[str]:
    """
    Validate generated response artifact entries.

    Args:
        entries (Any): Parsed JSON value loaded from a response artifact file.
        expected_count (int | None): Exact response count expected, if enforced.

    Returns:
        list[str]: Human-readable validation errors for malformed or incomplete
        response entries.
    """
    errors: list[str] = []
    if not isinstance(entries, list):
        return ["Response file must contain a JSON array."]
    if expected_count is not None and len(entries) != expected_count:
        errors.append(f"Expected {expected_count} responses, found {len(entries)}.")

    seen_ids: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"Entry {index} is not a JSON object.")
            continue

        entry_id = entry.get("id")
        label = entry_id if isinstance(entry_id, str) and entry_id else f"index {index}"
        if not isinstance(entry_id, str) or not entry_id.strip():
            errors.append(f"Entry {index} has no valid id.")
        elif entry_id in seen_ids:
            errors.append(f"Duplicate response id: {entry_id}.")
        else:
            seen_ids.add(entry_id)

        output = entry.get("actual_output")
        if not isinstance(output, str) or not output.strip():
            errors.append(f"{label}: actual_output is empty.")
        context = entry.get("retrieval_context")
        if not has_valid_retrieval_context(context):
            errors.append(f"{label}: retrieval_context is empty or invalid.")
    return errors


def main() -> int:
    """
    Validate a response JSON file from the command line.

    Returns:
        int: Zero when validation succeeds, otherwise one.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("response_file", type=Path)
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()

    try:
        entries = json.loads(args.response_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Validation failed: {exc}")
        return 1

    errors = validate_entries(entries, args.expected_count)
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validation passed for {len(entries)} responses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
