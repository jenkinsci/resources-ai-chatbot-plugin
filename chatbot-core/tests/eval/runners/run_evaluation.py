"""Evaluate one generated response shard with DeepEval and Ollama."""

import argparse
from importlib import import_module
import json
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Any

from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig, CacheConfig, DisplayConfig, ErrorConfig
from deepeval.test_case import LLMTestCase

EVAL_ROOT = Path(__file__).resolve().parents[1]
if str(EVAL_ROOT) not in sys.path:
    sys.path.insert(0, str(EVAL_ROOT))

build_metrics = import_module("metrics").build_metrics
METRIC_NAMES = import_module("runners.eval_constants").METRIC_NAMES
has_valid_retrieval_context = import_module(
    "runners.validate_responses"
).has_valid_retrieval_context


def load_json_array(path: Path) -> list[dict[str, Any]]:
    """
    Load and validate a JSON array of objects from disk.

    Args:
        path (Path): Path to the JSON file.

    Returns:
        list[dict[str, Any]]: Parsed list of JSON objects.

    Raises:
        ValueError: If the file does not contain a JSON array of objects.
    """
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{path} must contain a JSON array of objects")
    return value


def build_test_cases(
    responses: list[dict[str, Any]],
    goldens: list[dict[str, Any]],
    response_model: str,
    expected_count: int,
) -> list[LLMTestCase]:
    """
    Join generated responses to goldens using the stable eval ID.

    Args:
        responses (list[dict[str, Any]]): Generated response artifact entries.
        goldens (list[dict[str, Any]]): Golden dataset records keyed by eval ID.
        response_model (str): Response model name stored in test-case metadata.
        expected_count (int): Exact number of response entries expected.

    Returns:
        list[LLMTestCase]: DeepEval test cases ready for metric execution.

    Raises:
        ValueError: If counts, IDs, inputs, outputs, or retrieval context do
        not match the expected evaluation contract.
    """
    if len(responses) != expected_count:
        raise ValueError(f"Expected {expected_count} responses, found {len(responses)}")

    goldens_by_id = {
        golden["additional_metadata"]["id"]: golden for golden in goldens
    }
    test_cases: list[LLMTestCase] = []
    for response in responses:
        response_id = response.get("id")
        golden = goldens_by_id.get(response_id)
        if golden is None:
            raise ValueError(f"No golden found for response {response_id}")
        if response.get("input") != golden.get("input"):
            raise ValueError(f"Input mismatch for {response_id}")

        actual_output = response.get("actual_output")
        retrieval_context = response.get("retrieval_context")
        if not isinstance(actual_output, str) or not actual_output.strip():
            raise ValueError(f"{response_id}: actual_output is empty")
        if not has_valid_retrieval_context(retrieval_context):
            raise ValueError(f"{response_id}: retrieval_context is empty")

        metadata = golden.get("additional_metadata", {})
        test_cases.append(
            LLMTestCase(
                name=response_id,
                input=response["input"],
                actual_output=actual_output.strip(),
                expected_output=golden["expected_output"],
                retrieval_context=retrieval_context,
                metadata={
                    "id": response_id,
                    "category": metadata.get("category"),
                    "response_model": response_model,
                },
            )
        )
    return test_cases


def summarize_case(
    result: dict[str, Any],
    index: int,
    scores: dict[str, list[float]],
    passes: dict[str, int],
) -> tuple[dict[str, Any], list[str]]:
    """
    Normalize one DeepEval case result and update aggregate score buckets.

    Args:
        result (dict[str, Any]): Raw DeepEval case result payload.
        index (int): Zero-based result index used for fallback identifiers.
        scores (dict[str, list[float]]): Aggregate per-metric score lists.
        passes (dict[str, int]): Aggregate per-metric pass counters.

    Returns:
        tuple[dict[str, Any], list[str]]: Normalized case summary and any
        metric-level errors found in the raw result.
    """
    metadata = result.get("metadata") or {}
    case_id = str(metadata.get("id") or result.get("name") or f"index-{index}")
    metrics_by_name = {
        metric.get("name"): metric
        for metric in result.get("metrics_data", [])
        if isinstance(metric, dict)
    }
    case_metrics: dict[str, Any] = {}
    errors: list[str] = []
    for metric_name in METRIC_NAMES:
        metric = metrics_by_name.get(metric_name)
        if metric is None:
            errors.append(f"{case_id}: {metric_name} result is missing")
            continue
        score = metric.get("score")
        if isinstance(score, (int, float)):
            scores[metric_name].append(float(score))
            passes[metric_name] += int(bool(metric.get("success")))
        else:
            errors.append(f"{case_id}: {metric_name} has no numeric score")
        if metric.get("error"):
            errors.append(f"{case_id}: {metric_name} failed: {metric['error']}")
        case_metrics[metric_name] = {
            key: metric.get(key)
            for key in ("score", "success", "threshold", "error")
        }
    return {"id": case_id, "metrics": case_metrics}, errors


def get_result_case_id(result: dict[str, Any], index: int) -> str:
    """
    Return the stable case identifier from one DeepEval result.

    Args:
        result (dict[str, Any]): Raw DeepEval case result payload.
        index (int): Zero-based fallback index.

    Returns:
        str: Stable case identifier.
    """
    metadata = result.get("metadata") or {}
    return str(metadata.get("id") or result.get("name") or f"index-{index}")


def count_complete_metrics(result: dict[str, Any]) -> int:
    """
    Count metric rows that have usable numeric scores and no metric error.

    Args:
        result (dict[str, Any]): Raw DeepEval case result payload.

    Returns:
        int: Number of complete metric rows for the case.
    """
    metrics_by_name = {
        metric.get("name"): metric
        for metric in result.get("metrics_data", [])
        if isinstance(metric, dict)
    }
    complete_count = 0
    for metric_name in METRIC_NAMES:
        metric = metrics_by_name.get(metric_name)
        if not metric:
            continue
        if isinstance(metric.get("score"), (int, float)) and not metric.get("error"):
            complete_count += 1
    return complete_count


def find_incomplete_case_ids(raw_result: dict[str, Any]) -> set[str]:
    """
    Find cases missing at least one usable metric result.

    Args:
        raw_result (dict[str, Any]): Raw DeepEval evaluation result.

    Returns:
        set[str]: Case IDs that should be retried.
    """
    results = raw_result.get("test_results")
    if not isinstance(results, list):
        return set()
    incomplete_ids: set[str] = set()
    for index, result in enumerate(results):
        if not isinstance(result, dict):
            continue
        if count_complete_metrics(result) != len(METRIC_NAMES):
            incomplete_ids.add(get_result_case_id(result, index))
    return incomplete_ids


def merge_retry_results(
    raw_result: dict[str, Any],
    retry_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Replace incomplete case results when retry output has better coverage.

    Args:
        raw_result (dict[str, Any]): Original raw DeepEval result.
        retry_result (dict[str, Any]): Raw DeepEval retry result.

    Returns:
        dict[str, Any]: Raw result with improved retry rows merged in.
    """
    results = raw_result.get("test_results")
    retry_results = retry_result.get("test_results")
    if not isinstance(results, list) or not isinstance(retry_results, list):
        return raw_result

    retry_by_id = {
        get_result_case_id(result, index): result
        for index, result in enumerate(retry_results)
        if isinstance(result, dict)
    }
    merged_results = []
    for index, result in enumerate(results):
        if not isinstance(result, dict):
            merged_results.append(result)
            continue
        case_id = get_result_case_id(result, index)
        retry_case = retry_by_id.get(case_id)
        if retry_case and count_complete_metrics(retry_case) > count_complete_metrics(
            result
        ):
            merged_results.append(retry_case)
        else:
            merged_results.append(result)

    raw_result["test_results"] = merged_results
    return raw_result


def run_deepeval(
    test_cases: list[LLMTestCase],
    metrics: list[Any],
    identifier: str,
    max_concurrent: int,
):
    """
    Run DeepEval with the configured display and error policy.

    Args:
        test_cases (list[LLMTestCase]): Test cases to evaluate.
        metrics (list[Any]): DeepEval metric instances.
        identifier (str): DeepEval run identifier.
        max_concurrent (int): Maximum async concurrency.

    Returns:
        Any: DeepEval evaluation result object.
    """
    return evaluate(
        test_cases=test_cases,
        metrics=metrics,
        identifier=identifier,
        async_config=AsyncConfig(
            run_async=max_concurrent > 1,
            max_concurrent=max_concurrent,
        ),
        display_config=DisplayConfig(
            print_results=True,
            verbose_mode=False,
            truncate_passing_cases=False,
            inspect_after_run=False,
        ),
        cache_config=CacheConfig(write_cache=False, use_cache=False),
        error_config=ErrorConfig(ignore_errors=True, skip_on_missing_params=False),
    )


def summarize_metrics(
    scores: dict[str, list[float]], passes: dict[str, int]
) -> dict[str, Any]:
    """
    Build aggregate score statistics for each configured metric.

    Args:
        scores (dict[str, list[float]]): Recorded numeric scores per metric.
        passes (dict[str, int]): Pass counts per metric.

    Returns:
        dict[str, Any]: Aggregate score summary keyed by metric name.
    """
    metric_summary: dict[str, Any] = {}
    for metric_name in METRIC_NAMES:
        metric_scores = scores[metric_name]
        metric_summary[metric_name] = {
            "average_score": round(statistics.fmean(metric_scores), 4)
            if metric_scores
            else None,
            "minimum_score": round(min(metric_scores), 4) if metric_scores else None,
            "maximum_score": round(max(metric_scores), 4) if metric_scores else None,
            "pass_count": passes[metric_name],
            "evaluated_count": len(metric_scores),
            "pass_rate": round(passes[metric_name] / len(metric_scores), 4)
            if metric_scores
            else None,
        }
    return metric_summary


def summarize_result(
    raw_result: dict[str, Any],
    response_model: str,
    judge_model: str,
    threshold: float,
    expected_count: int,
) -> tuple[dict[str, Any], list[str]]:
    """
    Convert raw DeepEval output into stable per-case and aggregate JSON.

    Args:
        raw_result (dict[str, Any]): Raw DeepEval result payload.
        response_model (str): Response model evaluated in this shard.
        judge_model (str): Judge model used for metric evaluation.
        threshold (float): Pass threshold used for all metrics.
        expected_count (int): Number of test results expected for the shard.

    Returns:
        tuple[dict[str, Any], list[str]]: Stable summary JSON and any
        validation errors detected while normalizing the results.
    """
    results = raw_result.get("test_results")
    if not isinstance(results, list):
        return {}, ["DeepEval result does not contain test_results"]

    errors: list[str] = []
    if len(results) != expected_count:
        errors.append(f"Expected {expected_count} test results, found {len(results)}")
    scores: dict[str, list[float]] = {name: [] for name in METRIC_NAMES}
    passes = dict.fromkeys(METRIC_NAMES, 0)
    cases: list[dict[str, Any]] = []
    for index, result in enumerate(results):
        case, case_errors = summarize_case(result, index, scores, passes)
        cases.append(case)
        errors.extend(case_errors)

    return (
        {
            "response_model": response_model,
            "judge_model": judge_model,
            "threshold": threshold,
            "question_count": expected_count,
            "metrics": summarize_metrics(scores, passes),
            "cases": cases,
            "errors": errors,
        },
        errors,
    )


def save_json(path: Path, value: Any) -> None:
    """
    Write formatted JSON data to a file.

    Args:
        path (Path): Output JSON file path.
        value (Any): JSON-serializable value to write.
    """
    path.write_text(json.dumps(value, indent=4) + "\n", encoding="utf-8")


def write_report(summary: dict[str, Any], path: Path) -> None:
    """
    Write a concise Markdown report for one evaluation shard.

    Args:
        summary (dict[str, Any]): Normalized shard evaluation summary.
        path (Path): Output Markdown report path.
    """
    lines = [
        "# DeepEval shard report",
        "",
        f"- Response model: `{summary['response_model']}`",
        f"- Judge model: `{summary['judge_model']}`",
        f"- Questions: {summary['question_count']}",
        "",
        "| Metric | Average | Min | Max | Pass rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name in METRIC_NAMES:
        metric = summary["metrics"][name]
        lines.append(
            f"| {name} | {metric['average_score']} | {metric['minimum_score']} | "
            f"{metric['maximum_score']} | {metric['pass_rate']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    """
    Run DeepEval for one shard and persist machine-readable reports.

    Args:
        args (argparse.Namespace): Parsed CLI arguments for the shard run.

    Returns:
        int: Zero when evaluation succeeds without summary errors, otherwise one.
    """
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        test_cases = build_test_cases(
            load_json_array(args.responses),
            load_json_array(args.goldens),
            args.response_model,
            args.expected_count,
        )
        metrics = build_metrics(args.judge_model, args.base_url, args.threshold)
        started = time.perf_counter()
        result = run_deepeval(
            test_cases=test_cases,
            metrics=metrics,
            identifier=args.identifier,
            max_concurrent=1,
        )
        raw_result = result.model_dump(mode="json")
        test_cases_by_id = {test_case.name: test_case for test_case in test_cases}
        for attempt in range(1, args.retry_attempts + 1):
            incomplete_case_ids = find_incomplete_case_ids(raw_result)
            if not incomplete_case_ids:
                break
            retry_cases = [
                test_cases_by_id[case_id]
                for case_id in sorted(incomplete_case_ids)
                if case_id in test_cases_by_id
            ]
            if not retry_cases:
                break
            print(
                f"Retrying {len(retry_cases)} cases with incomplete metrics "
                f"(attempt {attempt}/{args.retry_attempts})."
            )
            retry_metrics = build_metrics(args.judge_model, args.base_url, args.threshold)
            retry_result = run_deepeval(
                test_cases=retry_cases,
                metrics=retry_metrics,
                identifier=f"{args.identifier}-retry-{attempt}",
                max_concurrent=args.retry_concurrency,
            )
            raw_result = merge_retry_results(
                raw_result, retry_result.model_dump(mode="json")
            )
        summary, errors = summarize_result(
            raw_result,
            args.response_model,
            args.judge_model,
            args.threshold,
            args.expected_count,
        )
        summary["duration_seconds"] = round(time.perf_counter() - started, 3)
        save_json(args.output_dir / "deepeval-result.json", raw_result)
        save_json(args.output_dir / "evaluation-summary.json", summary)
        write_report(summary, args.output_dir / "evaluation-report.md")
        if errors:
            print(
                "Shard evaluation completed with metric gaps; "
                "aggregate job will enforce coverage and score gates."
            )
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        save_json(
            args.output_dir / "evaluation-summary.json",
            {"errors": [f"{type(exc).__name__}: {exc}"]},
        )
        print(f"Evaluation failed: {type(exc).__name__}: {exc}")
        return 1


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the evaluation runner.

    Returns:
        argparse.Namespace: Parsed CLI arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--goldens", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--response-model", required=True)
    parser.add_argument("--judge-model", required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--identifier", required=True)
    parser.add_argument("--retry-attempts", type=int, default=0)
    parser.add_argument("--retry-concurrency", type=int, default=1)
    parser.add_argument(
        "--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
