"""Export eval configuration values for GitHub Actions outputs."""

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_EVAL_CONFIG = Path(__file__).resolve().parents[1] / "config.json"

OUTPUT_KEYS = (
    "question_count",
    "shard_size",
    "max_parallel",
    "response_model",
    "judge_model",
    "response_max_tokens",
    "response_num_ctx",
    "response_temperature",
    "response_request_timeout",
    "response_prompt_profile",
    "warm_prompt_cache",
    "judge_max_tokens",
    "judge_num_ctx",
    "metric_threshold",
    "minimum_metric_coverage",
    "missing_metric_retry_attempts",
    "missing_metric_retry_concurrency",
    "deepeval_per_task_timeout_seconds",
)


def format_output_value(value: Any) -> str:
    """
    Format a config value for the GitHub Actions output contract.

    Args:
        value (Any): Config value loaded from JSON.

    Returns:
        str: String representation accepted by GitHub Actions outputs.
    """
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def load_config(path: Path) -> dict[str, Any]:
    """
    Load the eval configuration JSON file.

    Args:
        path (Path): Path to the eval config file.

    Returns:
        dict[str, Any]: Parsed configuration values.

    Raises:
        ValueError: If the config root is not a JSON object.
    """
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("eval config must contain a JSON object")
    return config


def build_outputs(config: dict[str, Any]) -> dict[str, str]:
    """
    Select and format config values required by eval.yml.

    Args:
        config (dict[str, Any]): Parsed eval configuration values.

    Returns:
        dict[str, str]: GitHub Actions output names and values.

    Raises:
        KeyError: If a required config key is missing.
    """
    return {key: format_output_value(config[key]) for key in OUTPUT_KEYS}


def write_github_output(output_path: Path, outputs: dict[str, str]) -> None:
    """
    Append eval config values to a GitHub Actions output file.

    Args:
        output_path (Path): Path from the GITHUB_OUTPUT environment variable.
        outputs (dict[str, str]): Output names and values to append.
    """
    with output_path.open("a", encoding="utf-8") as output_file:
        for key, value in outputs.items():
            output_file.write(f"{key}={value}\n")


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for config export.

    Returns:
        argparse.Namespace: Parsed CLI arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_EVAL_CONFIG)
    parser.add_argument("--github-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """
    Export eval config values to GitHub Actions.

    Returns:
        int: Zero when the config is exported successfully.
    """
    args = parse_args()
    outputs = build_outputs(load_config(args.config))
    write_github_output(args.github_output, outputs)
    print(json.dumps(outputs, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
