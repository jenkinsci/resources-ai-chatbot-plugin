"""Build a GitHub Actions matrix for a requested eval dataset prefix."""

import argparse
import json
from pathlib import Path


def build_matrix(question_count: int, shard_size: int) -> list[dict[str, int]]:
    """
    Split the requested question range into contiguous workflow shards.

    Args:
        question_count (int): Number of questions to distribute across shards.
        shard_size (int): Maximum number of questions per shard.

    Returns:
        list[dict[str, int]]: Shard records containing the shard number,
        zero-based offset, and record limit for each workflow job.

    Raises:
        ValueError: If either input is not positive.
    """
    if question_count < 1:
        raise ValueError("question_count must be positive")
    if shard_size < 1:
        raise ValueError("shard_size must be positive")

    return [
        {
            "shard": index + 1,
            "offset": offset,
            "limit": min(shard_size, question_count - offset),
        }
        for index, offset in enumerate(range(0, question_count, shard_size))
    ]


def load_dataset(path: Path) -> list[object]:
    """
    Load the eval dataset and require a non-empty JSON array.

    Args:
        path (Path): Path to the dataset JSON file.

    Returns:
        list[object]: Parsed dataset entries.

    Raises:
        ValueError: If the file does not contain a non-empty JSON array.
    """
    dataset = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(dataset, list) or not dataset:
        raise ValueError("dataset must contain a non-empty JSON array")
    return dataset


def write_github_output(
    output_path: Path,
    question_count: int,
    matrix: list[dict[str, int]],
) -> None:
    """
    Append the shard matrix contract to a GitHub Actions output file.

    Args:
        output_path (Path): GitHub Actions output file path.
        question_count (int): Number of questions selected for this run.
        matrix (list[dict[str, int]]): Generated shard matrix payload.
    """
    compact_matrix = json.dumps(matrix, separators=(",", ":"))
    with output_path.open("a", encoding="utf-8") as output_file:
        output_file.write(f"question_count={question_count}\n")
        output_file.write(f"shard_count={len(matrix)}\n")
        output_file.write(f"matrix={compact_matrix}\n")


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for shard matrix generation.

    Returns:
        argparse.Namespace: Parsed CLI arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--question-count", type=int, required=True)
    parser.add_argument("--shard-size", type=int, required=True)
    parser.add_argument("--github-output", type=Path)
    return parser.parse_args()


def main() -> int:
    """
    Validate dataset inputs and emit matrix output for GitHub Actions.

    Returns:
        int: Zero when the matrix is generated successfully.
    """
    args = parse_args()

    dataset = load_dataset(args.dataset)
    if args.question_count > len(dataset):
        raise ValueError(
            f"question_count {args.question_count} exceeds dataset size {len(dataset)}"
        )

    matrix = build_matrix(args.question_count, args.shard_size)
    output = {
        "question_count": args.question_count,
        "shard_count": len(matrix),
        "matrix": matrix,
    }
    print(json.dumps(output, indent=2))

    if args.github_output:
        write_github_output(args.github_output, args.question_count, matrix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
