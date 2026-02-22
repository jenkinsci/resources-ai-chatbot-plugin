"""Opt-in pytest suite for the LLM-as-a-judge evaluation pipeline."""

from __future__ import annotations

import os
from dataclasses import replace

import pytest

from evaluation.llm_judge import (
    EvaluationConfig,
    load_golden_dataset,
    run_evaluation,
    threshold_failures,
)


@pytest.mark.evaluation
def test_llm_judge_thresholds(tmp_path):
    """Run LLM evaluation and enforce aggregate thresholds."""
    if os.getenv("RUN_LLM_EVAL") != "1":
        pytest.skip("Set RUN_LLM_EVAL=1 to run the LLM-as-a-judge suite.")

    config = EvaluationConfig.from_env()
    config = replace(config, output_path=tmp_path / "llm_judge_report.json")

    dataset = load_golden_dataset(config.dataset_path)
    assert len(dataset) >= 100, "Golden dataset must contain at least 100 samples."

    report = run_evaluation(config)
    failures = threshold_failures(report, config)
    if os.getenv("LLM_EVAL_ENFORCE_THRESHOLDS", "1") == "1":
        assert not failures, " ; ".join(failures)
