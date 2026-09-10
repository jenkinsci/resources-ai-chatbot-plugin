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


def load_expected_count(config_path: Path) -> int:
    """
    Load the configured eval question count.

    Args:
        config_path (Path): Path to the eval configuration JSON file.

    Returns:
        int: Configured number of expected response entries.

    Raises:
        ValueError: If the config does not contain a positive question count.
    """
    config = json.loads(config_path.read_text(encoding="utf-8"))
    question_count = config.get("question_count")
    if not isinstance(question_count, int) or question_count < 1:
        raise ValueError("config question_count must be a positive integer")
    return question_count


def validate_entries(
    entries: Any,
    expected_count: int | None = None,
    require_actual_output: bool = True,
) -> list[str]:
    """
    Validate generated response artifact entries.

    Args:
        entries (Any): Parsed JSON value loaded from a response artifact file.
        expected_count (int | None): Exact response count expected, if enforced.
        require_actual_output (bool): Whether every entry must include a
            non-empty generated answer.

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
        if require_actual_output and (not isinstance(output, str) or not output.strip()):
            errors.append(f"{label}: actual_output is empty.")
        context = entry.get("retrieval_context")
        if not has_valid_retrieval_context(context):
            errors.append(f"{label}: retrieval_context is empty or invalid.")
    return errors


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for response artifact validation.

    Returns:
        argparse.Namespace: Parsed CLI arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("response_file", type=Path)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Eval config used to derive expected-count when not provided.",
    )
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Validate retrieval_context without requiring actual_output.",
    )
    return parser.parse_args()


def main() -> int:
    """
    Validate a response JSON file from the command line.

    Returns:
        int: Zero when validation succeeds, otherwise one.
    """
    args = parse_args()

    try:
        entries = json.loads(args.response_file.read_text(encoding="utf-8"))
        expected_count = args.expected_count
        if expected_count is None and args.config is not None:
            expected_count = load_expected_count(args.config)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Validation failed: {exc}")
        return 1

    errors = validate_entries(
        entries,
        expected_count,
        require_actual_output=not args.retrieval_only,
    )
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validation passed for {len(entries)} responses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
