"""Aggregate generated responses and DeepEval scores from all shards."""

import argparse
import json
from pathlib import Path
import statistics
from typing import Any

try:
    from runners.eval_constants import METRIC_NAMES
    from runners.merge_shards import merge_shards
except ModuleNotFoundError:
    from eval_constants import METRIC_NAMES
    from merge_shards import merge_shards


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
    path.write_text(json.dumps(value, indent=4) + "\n", encoding="utf-8")


def aggregate_scores(
    shards_dir: Path,
    question_count: int,
    expected_shards: int,
) -> tuple[dict[str, Any], list[str]]:
    """
    Aggregate shard-level evaluation summaries into one report.

    Args:
        shards_dir (Path): Directory containing per-shard evaluation outputs.
        question_count (int): Total number of questions expected overall.
        expected_shards (int): Number of shard summaries expected on disk.

    Returns:
        tuple[dict[str, Any], list[str]]: Aggregate summary payload and any
        validation errors discovered while combining shard results.
    """
    summary_files = sorted(shards_dir.glob("*/evaluation-summary.json"))
    if len(summary_files) != expected_shards:
        raise ValueError(
            f"Expected {expected_shards} evaluation summaries, found {len(summary_files)}"
        )

    shard_summaries = [load_json(path) for path in summary_files]
    cases = [case for summary in shard_summaries for case in summary.get("cases", [])]
    errors = [error for summary in shard_summaries for error in summary.get("errors", [])]
    metrics: dict[str, Any] = {}
    for metric_name in METRIC_NAMES:
        scores: list[float] = []
        pass_count = 0
        for case in cases:
            metric = case.get("metrics", {}).get(metric_name, {})
            score = metric.get("score")
            if isinstance(score, (int, float)):
                scores.append(float(score))
                pass_count += int(bool(metric.get("success")))
        metrics[metric_name] = {
            "average_score": round(statistics.fmean(scores), 4) if scores else None,
            "minimum_score": round(min(scores), 4) if scores else None,
            "maximum_score": round(max(scores), 4) if scores else None,
            "pass_count": pass_count,
            "evaluated_count": len(scores),
            "pass_rate": round(pass_count / len(scores), 4) if scores else None,
        }
        if len(scores) != question_count:
            errors.append(
                f"{metric_name}: expected {question_count} scores, found {len(scores)}"
            )

    first_summary = shard_summaries[0]
    return (
        {
            "response_model": first_summary.get("response_model"),
            "judge_model": first_summary.get("judge_model"),
            "question_count": question_count,
            "shard_count": expected_shards,
            "metrics": metrics,
            "cases": cases,
            "errors": errors,
            "shards": shard_summaries,
        },
        errors,
    )


def write_report(summary: dict[str, Any], path: Path) -> None:
    """
    Write the Markdown report consumed by GitHub Actions summaries.

    Args:
        summary (dict[str, Any]): Aggregate evaluation summary payload.
        path (Path): Output Markdown report path.
    """
    lines = [
        "# Chatbot evaluation report",
        "",
        f"- Response model: `{summary['response_model']}`",
        f"- Judge model: `{summary['judge_model']}`",
        f"- Questions: {summary['question_count']}",
        f"- Shards: {summary['shard_count']}",
        "",
        "| Metric | Average | Min | Max | Evaluated | Pass rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in METRIC_NAMES:
        metric = summary["metrics"][name]
        lines.append(
            f"| {name} | {metric['average_score']} | {metric['minimum_score']} | "
            f"{metric['maximum_score']} | {metric['evaluated_count']} | "
            f"{metric['pass_rate']} |"
        )
    if summary["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in summary["errors"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    """
    Merge response artifacts and aggregate evaluation scores from the CLI.

    Returns:
        int: Zero when aggregation succeeds without errors, otherwise one.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--shards-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--question-count", type=int, required=True)
    parser.add_argument("--expected-shards", type=int, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    merge_errors = merge_shards(
        args.source,
        args.shards_dir,
        args.output_dir / "responses.json",
        args.question_count,
        args.expected_shards,
    )
    try:
        summary, evaluation_errors = aggregate_scores(
            args.shards_dir, args.question_count, args.expected_shards
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Aggregation failed: {exc}")
        return 1

    summary["errors"] = merge_errors + evaluation_errors
    save_json(args.output_dir / "evaluation-summary.json", summary)
    write_report(summary, args.output_dir / "evaluation-report.md")
    if summary["errors"]:
        print("Aggregation completed with errors.")
        return 1
    print(f"Aggregated {args.question_count} evaluated responses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
