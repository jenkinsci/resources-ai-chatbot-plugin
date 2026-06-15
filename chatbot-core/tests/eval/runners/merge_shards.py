"""Merge generated response shards into the retrieval-complete dataset."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

try:
    from runners.validate_responses import validate_entries
except ModuleNotFoundError:
    from validate_responses import validate_entries


def load_json(path: Path) -> Any:
    """
    Load JSON data from a file.

    Args:
        path (Path): Path to the JSON file.

    Returns:
        Any: Parsed JSON content.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Any) -> None:
    """
    Write formatted JSON data to a file.

    Args:
        path (Path): Output JSON file path.
        value (Any): JSON-serializable value to write.
    """
    path.write_text(
        json.dumps(value, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def merge_shards(
    source_file: Path,
    shards_dir: Path,
    output_file: Path,
    question_count: int,
    expected_shards: int,
) -> list[str]:
    """
    Merge generated response shards back into the canonical source order.

    Args:
        source_file (Path): Retrieval-complete source dataset used for sharding.
        shards_dir (Path): Directory containing per-shard `responses.json` files.
        output_file (Path): Path where the merged dataset should be written.
        question_count (int): Number of source questions expected in the merge.
        expected_shards (int): Number of shard response files expected.

    Returns:
        list[str]: Validation and merge errors collected while rebuilding the
        combined response artifact.
    """
    source_entries = load_json(source_file)[:question_count]
    response_files = sorted(shards_dir.glob("*/responses.json"))
    errors: list[str] = []
    if len(response_files) != expected_shards:
        errors.append(
            f"Expected {expected_shards} shard response files, found {len(response_files)}."
        )

    outputs_by_id: dict[str, str] = {}
    for response_file in response_files:
        entries = load_json(response_file)
        errors.extend(
            f"{response_file.parent.name}: {error}"
            for error in validate_entries(entries)
        )
        if not isinstance(entries, list):
            continue
        for entry in entries:
            entry_id = entry.get("id")
            if entry_id in outputs_by_id:
                errors.append(f"Duplicate response across shards: {entry_id}.")
                continue
            if not isinstance(entry_id, str):
                continue

            actual_output = entry.get("actual_output")
            if not isinstance(actual_output, str):
                errors.append(
                    f"{response_file.parent.name}: {entry_id}: actual_output is empty."
                )
                continue

            outputs_by_id[entry_id] = actual_output.strip()

    merged_entries = deepcopy(source_entries)
    for entry in merged_entries:
        entry["actual_output"] = outputs_by_id.get(entry.get("id"), "")

    errors.extend(validate_entries(merged_entries, question_count))
    output_file.parent.mkdir(parents=True, exist_ok=True)
    save_json(output_file, merged_entries)
    return errors


def main() -> int:
    """
    Merge response shard artifacts from the command line.

    Returns:
        int: Zero when shard merge succeeds without errors, otherwise one.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--shards-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--question-count", type=int, required=True)
    parser.add_argument("--expected-shards", type=int, required=True)
    args = parser.parse_args()

    errors = merge_shards(
        source_file=args.source,
        shards_dir=args.shards_dir,
        output_file=args.output,
        question_count=args.question_count,
        expected_shards=args.expected_shards,
    )
    if errors:
        print("Merge failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Merged {args.question_count} generated responses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
