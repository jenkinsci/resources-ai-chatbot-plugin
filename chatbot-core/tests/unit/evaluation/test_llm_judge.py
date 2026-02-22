"""Unit tests for LLM judge helpers."""

# pylint: disable=protected-access

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.llm_judge import (
    AggregateMetrics,
    EvaluationConfig,
    EvaluationReport,
    _extract_json_object,
    load_golden_dataset,
    threshold_failures,
)


def test_extract_json_object_parses_wrapped_output():
    """Should extract valid JSON object from mixed text output."""
    wrapped = "Result:\n```json\n{\"faithfulness\": {\"score\": 0.9}}\n```"
    assert _extract_json_object(wrapped) == "{\"faithfulness\": {\"score\": 0.9}}"


def test_extract_json_object_raises_on_invalid_payload():
    """Should fail when no JSON object is present."""
    with pytest.raises(ValueError):
        _extract_json_object("No JSON payload.")


def test_load_golden_dataset_rejects_missing_fields(tmp_path: Path):
    """Should validate required fields for each dataset line."""
    dataset_path = tmp_path / "bad.jsonl"
    dataset_path.write_text(json.dumps({"id": "core-001", "question": "Q"}) + "\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_golden_dataset(dataset_path)


def test_threshold_failures_reports_metric_violations(tmp_path: Path):
    """Should list all failed threshold checks."""
    report = EvaluationReport(
        created_at_utc="2026-01-01T00:00:00+00:00",
        dataset_path="dataset.jsonl",
        total_dataset_samples=120,
        evaluated_samples=10,
        sample_size_requested=10,
        random_seed=42,
        judge_model="judge-model",
        candidate_model="candidate-model",
        thresholds={},
        aggregate=AggregateMetrics(
            faithfulness=0.80,
            context_recall=0.81,
            answer_relevance=0.82,
        ),
        samples=[],
    )

    config = EvaluationConfig(
        dataset_path=tmp_path / "dataset.jsonl",
        output_path=tmp_path / "report.json",
        sample_size=10,
        random_seed=42,
        min_samples=20,
        faithfulness_threshold=0.85,
        context_recall_threshold=0.85,
        answer_relevance_threshold=0.85,
        candidate_base_url="https://example.com/v1",
        candidate_api_key="candidate",
        candidate_model="candidate-model",
        judge_base_url="https://example.com/v1",
        judge_api_key="judge",
        judge_model="judge-model",
        answer_max_tokens=250,
        judge_max_tokens=250,
        request_timeout_seconds=30,
        store_sample_details=False,
        max_stored_text_chars=500,
    )

    failures = threshold_failures(report, config)
    assert len(failures) == 4
    assert "evaluated_samples=10 is below min_samples=20" in failures[0]
