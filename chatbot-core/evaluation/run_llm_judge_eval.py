"""CLI entrypoint for the LLM-as-a-judge evaluation pipeline."""

# pylint: disable=line-too-long,wrong-import-position

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.llm_judge import (
    DEFAULT_DATASET_PATH,
    EvaluationConfig,
    run_evaluation,
    threshold_failures,
)


def _build_config_from_args(args: argparse.Namespace) -> EvaluationConfig:
    """Build EvaluationConfig from CLI arguments with environment fallbacks."""
    env_config = EvaluationConfig.from_env()

    return EvaluationConfig(
        dataset_path=Path(args.dataset_path) if args.dataset_path else env_config.dataset_path,
        output_path=Path(args.output_path) if args.output_path else env_config.output_path,
        sample_size=args.sample_size if args.sample_size is not None else env_config.sample_size,
        random_seed=args.random_seed if args.random_seed is not None else env_config.random_seed,
        min_samples=args.min_samples if args.min_samples is not None else env_config.min_samples,
        faithfulness_threshold=(
            args.faithfulness_threshold
            if args.faithfulness_threshold is not None
            else env_config.faithfulness_threshold
        ),
        context_recall_threshold=(
            args.context_recall_threshold
            if args.context_recall_threshold is not None
            else env_config.context_recall_threshold
        ),
        answer_relevance_threshold=(
            args.answer_relevance_threshold
            if args.answer_relevance_threshold is not None
            else env_config.answer_relevance_threshold
        ),
        candidate_base_url=args.candidate_base_url or env_config.candidate_base_url,
        candidate_api_key=args.candidate_api_key or env_config.candidate_api_key,
        candidate_model=args.candidate_model or env_config.candidate_model,
        judge_base_url=args.judge_base_url or env_config.judge_base_url,
        judge_api_key=args.judge_api_key or env_config.judge_api_key,
        judge_model=args.judge_model or env_config.judge_model,
        answer_max_tokens=(
            args.answer_max_tokens if args.answer_max_tokens is not None else env_config.answer_max_tokens
        ),
        judge_max_tokens=(
            args.judge_max_tokens if args.judge_max_tokens is not None else env_config.judge_max_tokens
        ),
        request_timeout_seconds=(
            args.timeout_seconds
            if args.timeout_seconds is not None
            else env_config.request_timeout_seconds
        ),
        store_sample_details=(
            args.store_sample_details
            if args.store_sample_details is not None
            else env_config.store_sample_details
        ),
        max_stored_text_chars=(
            args.max_stored_text_chars
            if args.max_stored_text_chars is not None
            else env_config.max_stored_text_chars
        ),
    )


def _argument_parser() -> argparse.ArgumentParser:
    """Build and return parser for CLI arguments."""
    parser = argparse.ArgumentParser(description="Run LLM-as-a-judge evaluation.")
    parser.add_argument("--dataset-path", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument(
        "--output-path",
        default=os.getenv("LLM_EVAL_REPORT_PATH", "evaluation/report/llm_judge_report.json"),
    )
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--random-seed", type=int, default=None)
    parser.add_argument("--min-samples", type=int, default=None)
    parser.add_argument("--faithfulness-threshold", type=float, default=None)
    parser.add_argument("--context-recall-threshold", type=float, default=None)
    parser.add_argument("--answer-relevance-threshold", type=float, default=None)
    parser.add_argument("--candidate-base-url", default=os.getenv("CANDIDATE_LLM_API_BASE_URL", ""))
    parser.add_argument("--candidate-api-key", default=os.getenv("CANDIDATE_LLM_API_KEY", ""))
    parser.add_argument("--candidate-model", default=os.getenv("CANDIDATE_LLM_MODEL", ""))
    parser.add_argument("--judge-base-url", default=os.getenv("JUDGE_LLM_API_BASE_URL", ""))
    parser.add_argument("--judge-api-key", default=os.getenv("JUDGE_LLM_API_KEY", ""))
    parser.add_argument("--judge-model", default=os.getenv("JUDGE_LLM_MODEL", ""))
    parser.add_argument("--answer-max-tokens", type=int, default=None)
    parser.add_argument("--judge-max-tokens", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=int, default=None)
    parser.add_argument(
        "--store-sample-details",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Whether to store question/answer/context text in the report (default: false).",
    )
    parser.add_argument(
        "--max-stored-text-chars",
        type=int,
        default=None,
        help="Maximum characters stored for each text field when details are enabled.",
    )
    parser.add_argument(
        "--enforce-thresholds",
        action="store_true",
        help="Exit with status 1 if aggregate scores are below configured thresholds.",
    )
    return parser


def main() -> int:
    """CLI main function."""
    parser = _argument_parser()
    args = parser.parse_args()
    config = _build_config_from_args(args)
    report = run_evaluation(config)

    print("LLM-as-a-judge evaluation completed.")
    print(f"Report: {config.output_path}")
    print(f"Samples evaluated: {report.evaluated_samples}/{report.total_dataset_samples}")
    print(f"Faithfulness:    {report.aggregate.faithfulness:.3f}")
    print(f"Context recall:  {report.aggregate.context_recall:.3f}")
    print(f"Answer relevance:{report.aggregate.answer_relevance:.3f}")

    failures = threshold_failures(report, config)
    if failures:
        print("Threshold check failures:")
        for failure in failures:
            print(f"- {failure}")
        if args.enforce_thresholds:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
