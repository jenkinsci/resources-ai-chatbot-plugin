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


def summarize_metric_cases(
    cases: list[dict[str, Any]],
    metric_name: str,
    question_count: int,
) -> tuple[dict[str, Any], float | None, float]:
    """
    Summarize one metric across all aggregated cases.

    Args:
        cases (list[dict[str, Any]]): Aggregated case summaries.
        metric_name (str): Metric name to summarize.
        question_count (int): Total expected question count.

    Returns:
        tuple[dict[str, Any], float | None, float]: Metric summary, average
        score, and coverage fraction.
    """
    scores: list[float] = []
    pass_count = 0
    for case in cases:
        metric = case.get("metrics", {}).get(metric_name, {})
        score = metric.get("score")
        if isinstance(score, (int, float)):
            scores.append(float(score))
            pass_count += int(bool(metric.get("success")))

    coverage = len(scores) / question_count
    average_score = statistics.fmean(scores) if scores else None
    summary = {
        "average_score": round(average_score, 4) if average_score is not None else None,
        "minimum_score": round(min(scores), 4) if scores else None,
        "maximum_score": round(max(scores), 4) if scores else None,
        "pass_count": pass_count,
        "evaluated_count": len(scores),
        "coverage": round(coverage, 4),
        "pass_rate": round(pass_count / len(scores), 4) if scores else None,
    }
    return summary, average_score, coverage


def collect_shard_summaries(
    shards_dir: Path,
    expected_shards: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """
    Load shard summaries and separate non-fatal shard warnings.

    Args:
        shards_dir (Path): Directory containing per-shard evaluation outputs.
        expected_shards (int): Number of shard summaries expected on disk.

    Returns:
        tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]: Loaded
        shard summaries, flattened case summaries, and non-fatal warnings.

    Raises:
        ValueError: If the expected shard summaries are not present.
    """
    summary_files = sorted(shards_dir.glob("*/evaluation-summary.json"))
    if len(summary_files) != expected_shards:
        found_files = ", ".join(str(path) for path in summary_files) or "none"
        raise ValueError(
            f"Expected {expected_shards} evaluation summaries, found "
            f"{len(summary_files)}. Found summary files: {found_files}"
        )

    shard_summaries = [load_json(path) for path in summary_files]
    cases = [case for summary in shard_summaries for case in summary.get("cases", [])]
    warnings = [
        error for summary in shard_summaries for error in summary.get("errors", [])
    ]
    return shard_summaries, cases, warnings


def aggregate_scores(
    shards_dir: Path,
    question_count: int,
    expected_shards: int,
    minimum_metric_coverage: float,
    threshold_score: float,
) -> tuple[dict[str, Any], list[str]]:
    """
    Aggregate shard-level evaluation summaries into one report.

    Args:
        shards_dir (Path): Directory containing per-shard evaluation outputs.
        question_count (int): Total number of questions expected overall.
        expected_shards (int): Number of shard summaries expected on disk.
        minimum_metric_coverage (float): Required fraction of questions with
            a numeric score for each metric.
        threshold_score (float): Required average score threshold for each metric.

    Returns:
        tuple[dict[str, Any], list[str]]: Aggregate summary payload and fatal
        validation errors discovered while combining shard results.
    """
    shard_summaries, cases, warnings = collect_shard_summaries(
        shards_dir, expected_shards
    )
    errors: list[str] = []
    metrics: dict[str, Any] = {}
    for metric_name in METRIC_NAMES:
        metric_summary, average_score, coverage = summarize_metric_cases(
            cases, metric_name, question_count
        )
        metrics[metric_name] = metric_summary
        if coverage < minimum_metric_coverage:
            errors.append(
                f"{metric_name}: coverage {coverage:.2%} is below "
                f"{minimum_metric_coverage:.2%}"
            )
        if average_score is None or average_score < threshold_score:
            score_text = "missing" if average_score is None else f"{average_score:.4f}"
            errors.append(
                f"{metric_name}: average score {score_text} is below "
                f"threshold {threshold_score:.4f}"
            )

    return (
        {
            "response_model": shard_summaries[0].get("response_model"),
            "judge_model": shard_summaries[0].get("judge_model"),
            "question_count": question_count,
            "shard_count": expected_shards,
            "minimum_metric_coverage": minimum_metric_coverage,
            "threshold_score": threshold_score,
            "metrics": metrics,
            "cases": cases,
            "warnings": warnings,
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
        f"- Minimum metric coverage: {summary['minimum_metric_coverage']}",
        f"- Threshold score: {summary['threshold_score']}",
        "",
    ]
    if summary["errors"]:
        lines.extend(
            [
                (
                    "> **Warning:** merge is blocked because one or more "
                    "evaluation requirements failed."
                ),
                "",
            ]
        )
    lines.extend(
        [
            "| Metric | Average | Min | Max | Evaluated | Coverage | Pass rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in METRIC_NAMES:
        metric = summary["metrics"][name]
        lines.append(
            f"| {name} | {metric['average_score']} | {metric['minimum_score']} | "
            f"{metric['maximum_score']} | {metric['evaluated_count']} | "
            f"{metric['coverage']} | {metric['pass_rate']} |"
        )
    if summary["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in summary["errors"])
    if summary.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in summary["warnings"])
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
    parser.add_argument("--minimum-metric-coverage", type=float, required=True)
    parser.add_argument("--threshold-score", type=float, required=True)
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
            args.shards_dir,
            args.question_count,
            args.expected_shards,
            args.minimum_metric_coverage,
            args.threshold_score,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Aggregation failed: {exc}")
        return 1

    summary["errors"] = merge_errors + evaluation_errors
    save_json(args.output_dir / "evaluation-summary.json", summary)
    write_report(summary, args.output_dir / "evaluation-report.md")
    if summary["errors"]:
        print("Aggregation completed with errors.")
        for error in summary["errors"]:
            print(f"- {error}")
        return 1
    print(f"Aggregated {args.question_count} evaluated responses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
