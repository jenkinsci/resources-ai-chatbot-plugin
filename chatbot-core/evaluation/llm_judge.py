"""LLM-as-a-judge evaluation pipeline for chatbot quality regression checks."""

# pylint: disable=line-too-long,too-many-instance-attributes

from __future__ import annotations

import json
import os
import random
import shutil
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import faiss
import numpy as np
import requests
from langchain.memory import ConversationBufferMemory

from api.models.embedding_model import EMBEDDING_MODEL
from api.prompts.prompt_builder import build_prompt
from api.services.chat_service import retrieve_context
from rag.embedding.embedding_utils import embed_documents
from rag.vectorstore.vectorstore_utils import save_faiss_index, save_metadata
from utils import LoggerFactory

LOGGER = LoggerFactory.get_logger(__name__)
DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "dataset" / "golden_qa_dataset.jsonl"
EMBEDDINGS_DIR = Path(__file__).resolve().parent.parent / "data" / "embeddings"
PLUGIN_INDEX_PATH = EMBEDDINGS_DIR / "plugins_index.idx"
PLUGIN_METADATA_PATH = EMBEDDINGS_DIR / "plugins_metadata.pkl"


@dataclass(frozen=True)
class GoldenSample:
    """Single row of the golden evaluation dataset."""

    sample_id: str
    category: str
    question: str
    ground_truth: str
    reference_context: str


@dataclass(frozen=True)
class MetricScore:
    """Score and reason for one evaluation metric."""

    score: float
    reason: str


@dataclass(frozen=True)
class SampleEvaluationResult:
    """Evaluation output for a single sample."""

    sample_id: str
    category: str
    question: str
    candidate_answer: str
    retrieved_context: str
    faithfulness: MetricScore
    context_recall: MetricScore
    answer_relevance: MetricScore


@dataclass(frozen=True)
class AggregateMetrics:
    """Averaged metrics across all evaluated samples."""

    faithfulness: float
    context_recall: float
    answer_relevance: float


@dataclass(frozen=True)
class EvaluationReport:
    """Full evaluation report saved as JSON and used by pytest checks."""

    created_at_utc: str
    dataset_path: str
    total_dataset_samples: int
    evaluated_samples: int
    sample_size_requested: int
    random_seed: int
    judge_model: str
    candidate_model: str
    thresholds: dict[str, float]
    aggregate: AggregateMetrics
    samples: list[SampleEvaluationResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize report dataclass tree into a plain dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class EvaluationConfig:
    """Runtime configuration for the LLM judge pipeline."""

    dataset_path: Path
    output_path: Path
    sample_size: int
    random_seed: int
    min_samples: int
    faithfulness_threshold: float
    context_recall_threshold: float
    answer_relevance_threshold: float
    candidate_base_url: str
    candidate_api_key: str
    candidate_model: str
    judge_base_url: str
    judge_api_key: str
    judge_model: str
    answer_max_tokens: int
    judge_max_tokens: int
    request_timeout_seconds: int
    store_sample_details: bool
    max_stored_text_chars: int

    @staticmethod
    def from_env() -> "EvaluationConfig":
        """Build evaluation config from environment variables."""
        dataset_path = Path(os.getenv("LLM_EVAL_DATASET_PATH", str(DEFAULT_DATASET_PATH)))
        output_path = Path(
            os.getenv("LLM_EVAL_REPORT_PATH", "evaluation/report/llm_judge_report.json")
        )

        candidate_base_url = os.getenv("CANDIDATE_LLM_API_BASE_URL", "").strip()
        candidate_api_key = os.getenv("CANDIDATE_LLM_API_KEY", "").strip()
        candidate_model = os.getenv("CANDIDATE_LLM_MODEL", "").strip()

        judge_base_url = os.getenv("JUDGE_LLM_API_BASE_URL", "").strip()
        judge_api_key = os.getenv("JUDGE_LLM_API_KEY", "").strip()
        judge_model = os.getenv("JUDGE_LLM_MODEL", "").strip()

        # Fallback: use judge endpoint for candidate generation if candidate values are not set.
        if not candidate_base_url:
            candidate_base_url = judge_base_url
        if not candidate_api_key:
            candidate_api_key = judge_api_key
        if not candidate_model:
            candidate_model = judge_model

        return EvaluationConfig(
            dataset_path=dataset_path,
            output_path=output_path,
            sample_size=int(os.getenv("LLM_EVAL_SAMPLE_SIZE", "30")),
            random_seed=int(os.getenv("LLM_EVAL_RANDOM_SEED", "42")),
            min_samples=int(os.getenv("LLM_EVAL_MIN_SAMPLES", "20")),
            faithfulness_threshold=float(os.getenv("LLM_EVAL_FAITHFULNESS_THRESHOLD", "0.85")),
            context_recall_threshold=float(os.getenv("LLM_EVAL_CONTEXT_RECALL_THRESHOLD", "0.85")),
            answer_relevance_threshold=float(
                os.getenv("LLM_EVAL_ANSWER_RELEVANCE_THRESHOLD", "0.85")
            ),
            candidate_base_url=candidate_base_url,
            candidate_api_key=candidate_api_key,
            candidate_model=candidate_model,
            judge_base_url=judge_base_url,
            judge_api_key=judge_api_key,
            judge_model=judge_model,
            answer_max_tokens=int(os.getenv("LLM_EVAL_ANSWER_MAX_TOKENS", "450")),
            judge_max_tokens=int(os.getenv("LLM_EVAL_JUDGE_MAX_TOKENS", "450")),
            request_timeout_seconds=int(os.getenv("LLM_EVAL_TIMEOUT_SECONDS", "120")),
            store_sample_details=os.getenv("LLM_EVAL_STORE_SAMPLE_DETAILS", "0") == "1",
            max_stored_text_chars=int(os.getenv("LLM_EVAL_MAX_STORED_TEXT_CHARS", "1200")),
        )


class OpenAICompatibleClient:
    """Thin client for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 120,
    ) -> None:
        if not base_url:
            raise ValueError("Base URL cannot be empty.")
        if not model:
            raise ValueError("Model cannot be empty.")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    @property
    def _chat_completions_url(self) -> str:
        """Return the final chat-completions endpoint URL."""
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate a response from the configured API endpoint."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = requests.post(
            self._chat_completions_url,
            headers=headers,
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No choices returned by completion API.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not content:
            raise ValueError("Completion API returned an empty message.")
        return str(content).strip()


def load_golden_dataset(dataset_path: Path) -> list[GoldenSample]:
    """Load golden dataset from a JSONL file."""
    if not dataset_path.exists():
        raise FileNotFoundError(f"Golden dataset file not found: {dataset_path}")

    samples: list[GoldenSample] = []
    with dataset_path.open("r", encoding="utf-8") as file_obj:
        for line_number, line in enumerate(file_obj, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON at {dataset_path}:{line_number}: {error.msg}"
                ) from error

            for required_field in (
                "id",
                "category",
                "question",
                "ground_truth",
                "reference_context",
            ):
                if required_field not in item:
                    raise ValueError(
                        f"Missing field '{required_field}' at {dataset_path}:{line_number}"
                    )

            samples.append(
                GoldenSample(
                    sample_id=str(item["id"]),
                    category=str(item["category"]),
                    question=str(item["question"]),
                    ground_truth=str(item["ground_truth"]),
                    reference_context=str(item["reference_context"]),
                )
            )
    return samples


def select_samples(
    samples: list[GoldenSample],
    sample_size: int,
    random_seed: int,
) -> list[GoldenSample]:
    """Select deterministic subset of samples if sample_size is positive."""
    if sample_size <= 0 or sample_size >= len(samples):
        return list(samples)
    rng = random.Random(random_seed)
    return rng.sample(samples, sample_size)


def _build_evaluation_index(samples: list[GoldenSample]) -> None:
    """Build a temporary plugin index from reference contexts of golden samples."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    metadata: list[dict[str, Any]] = []
    seen_contexts: set[str] = set()
    for sample in samples:
        context = sample.reference_context.strip()
        if not context or context in seen_contexts:
            continue
        seen_contexts.add(context)
        metadata.append(
            {
                "id": f"eval-{sample.sample_id}",
                "chunk_text": context,
                "metadata": {
                    "title": sample.sample_id,
                    "data_source": "golden_eval_dataset",
                },
                "code_blocks": [],
            }
        )

    if not metadata:
        raise ValueError("No reference contexts found in golden dataset.")

    vectors = embed_documents([item["chunk_text"] for item in metadata], EMBEDDING_MODEL, LOGGER)
    vectors_np = np.array(vectors, dtype="float32")
    if vectors_np.ndim != 2:
        raise ValueError(f"Expected 2D vectors, got shape: {vectors_np.shape}")

    dimension = vectors_np.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors_np)  # pylint: disable=no-value-for-parameter

    save_faiss_index(index, str(PLUGIN_INDEX_PATH), LOGGER)
    save_metadata(metadata, str(PLUGIN_METADATA_PATH), LOGGER)


@contextmanager
def temporary_plugin_index(samples: list[GoldenSample]) -> Iterator[None]:
    """Swap plugin FAISS index/metadata with evaluation-specific temporary index."""
    backups: dict[Path, Path] = {}
    for current_path in (PLUGIN_INDEX_PATH, PLUGIN_METADATA_PATH):
        if current_path.exists():
            backup_path = current_path.with_suffix(
                f"{current_path.suffix}.backup-{uuid.uuid4().hex}"
            )
            shutil.move(str(current_path), str(backup_path))
            backups[current_path] = backup_path

    try:
        _build_evaluation_index(samples)
        yield
    finally:
        for generated_path in (PLUGIN_INDEX_PATH, PLUGIN_METADATA_PATH):
            if generated_path.exists():
                generated_path.unlink()

        for original_path, backup_path in backups.items():
            if backup_path.exists():
                shutil.move(str(backup_path), str(original_path))


def _extract_json_object(raw_text: str) -> str:
    """Extract first JSON object from a raw text completion."""
    start_index = raw_text.find("{")
    if start_index < 0:
        raise ValueError("No JSON object found in judge output.")

    depth = 0
    for index in range(start_index, len(raw_text)):
        char = raw_text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return raw_text[start_index : index + 1]
    raise ValueError("Incomplete JSON object in judge output.")


def _normalize_score(value: Any) -> float:
    """Normalize numeric scores to [0.0, 1.0]."""
    try:
        score = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Score '{value}' is not numeric.") from error
    return max(0.0, min(1.0, score))


def _parse_metric(metric_name: str, payload: dict[str, Any]) -> MetricScore:
    """Parse one metric from judge JSON payload."""
    metric_payload = payload.get(metric_name, {})
    if not isinstance(metric_payload, dict):
        raise ValueError(f"Metric '{metric_name}' is not an object.")
    score = _normalize_score(metric_payload.get("score"))
    reason = str(metric_payload.get("reason", "")).strip()
    if not reason:
        reason = "No reason provided by judge."
    return MetricScore(score=score, reason=reason)


def _judge_prompt(
    question: str,
    ground_truth: str,
    retrieved_context: str,
    candidate_answer: str,
) -> str:
    """Build strict JSON prompt for judge model."""
    return f"""
You are an expert evaluator for a Jenkins chatbot.
Score the candidate answer using three metrics in [0.0, 1.0]:
1) faithfulness: Is the answer supported by retrieved context?
2) context_recall: Does retrieved context contain information needed by ground truth?
3) answer_relevance: Does the answer actually address the question?

Scoring rubric:
- 1.0: excellent
- 0.7-0.9: mostly correct with minor gaps
- 0.4-0.6: partially correct
- 0.0-0.3: poor or incorrect

Return ONLY valid JSON with this schema:
{{
  "faithfulness": {{"score": <float>, "reason": "<short reason>"}},
  "context_recall": {{"score": <float>, "reason": "<short reason>"}},
  "answer_relevance": {{"score": <float>, "reason": "<short reason>"}}
}}

Question:
{question}

Ground truth:
{ground_truth}

Retrieved context:
{retrieved_context}

Candidate answer:
{candidate_answer}
""".strip()


def _score_sample(
    sample: GoldenSample,
    candidate_answer: str,
    retrieved_context: str,
    judge_client: OpenAICompatibleClient,
    judge_max_tokens: int,
) -> tuple[MetricScore, MetricScore, MetricScore]:
    """Score one sample with judge LLM and parse metric payload."""
    prompt = _judge_prompt(
        question=sample.question,
        ground_truth=sample.ground_truth,
        retrieved_context=retrieved_context,
        candidate_answer=candidate_answer,
    )
    judge_raw = judge_client.generate(prompt=prompt, max_tokens=judge_max_tokens)
    json_payload = json.loads(_extract_json_object(judge_raw))

    faithfulness = _parse_metric("faithfulness", json_payload)
    context_recall = _parse_metric("context_recall", json_payload)
    answer_relevance = _parse_metric("answer_relevance", json_payload)
    return faithfulness, context_recall, answer_relevance


def _evaluate_samples(
    samples: list[GoldenSample],
    answer_client: OpenAICompatibleClient,
    judge_client: OpenAICompatibleClient,
    config: EvaluationConfig,
) -> list[SampleEvaluationResult]:
    """Run retrieval + answer generation + judge scoring for each sample."""
    results: list[SampleEvaluationResult] = []
    for sample in samples:
        LOGGER.info("Evaluating sample %s (%s)", sample.sample_id, sample.category)

        memory = ConversationBufferMemory(return_messages=True)
        retrieved_context = retrieve_context(sample.question)
        prompt = build_prompt(
            user_query=sample.question,
            context=retrieved_context,
            memory=memory,
        )
        candidate_answer = answer_client.generate(prompt=prompt, max_tokens=config.answer_max_tokens)
        faithfulness, context_recall, answer_relevance = _score_sample(
            sample=sample,
            candidate_answer=candidate_answer,
            retrieved_context=retrieved_context,
            judge_client=judge_client,
            judge_max_tokens=config.judge_max_tokens,
        )

        results.append(
            SampleEvaluationResult(
                sample_id=sample.sample_id,
                category=sample.category,
                question=sample.question,
                candidate_answer=candidate_answer,
                retrieved_context=retrieved_context,
                faithfulness=faithfulness,
                context_recall=context_recall,
                answer_relevance=answer_relevance,
            )
        )
    return results


def _aggregate(results: list[SampleEvaluationResult]) -> AggregateMetrics:
    """Compute aggregate mean for each metric."""
    if not results:
        return AggregateMetrics(0.0, 0.0, 0.0)

    faithfulness_scores = [result.faithfulness.score for result in results]
    context_recall_scores = [result.context_recall.score for result in results]
    answer_relevance_scores = [result.answer_relevance.score for result in results]

    return AggregateMetrics(
        faithfulness=float(np.mean(faithfulness_scores)),
        context_recall=float(np.mean(context_recall_scores)),
        answer_relevance=float(np.mean(answer_relevance_scores)),
    )


def _truncate_text(text: str, limit: int) -> str:
    """Truncate text to reduce accidental sensitive content persistence."""
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def _sanitize_sample_result(
    result: SampleEvaluationResult,
    config: EvaluationConfig,
) -> SampleEvaluationResult:
    """Redact or truncate sample payload fields before writing report."""
    if not config.store_sample_details:
        return SampleEvaluationResult(
            sample_id=result.sample_id,
            category=result.category,
            question="[REDACTED]",
            candidate_answer="[REDACTED]",
            retrieved_context="[REDACTED]",
            faithfulness=result.faithfulness,
            context_recall=result.context_recall,
            answer_relevance=result.answer_relevance,
        )
    return SampleEvaluationResult(
        sample_id=result.sample_id,
        category=result.category,
        question=_truncate_text(result.question, config.max_stored_text_chars),
        candidate_answer=_truncate_text(result.candidate_answer, config.max_stored_text_chars),
        retrieved_context=_truncate_text(result.retrieved_context, config.max_stored_text_chars),
        faithfulness=result.faithfulness,
        context_recall=result.context_recall,
        answer_relevance=result.answer_relevance,
    )


def save_report(report: EvaluationReport, output_path: Path) -> None:
    """Persist report as prettified JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(report.to_dict(), file_obj, indent=2, ensure_ascii=False)


def threshold_failures(report: EvaluationReport, config: EvaluationConfig) -> list[str]:
    """Return a list of threshold violations."""
    failures: list[str] = []
    if report.evaluated_samples < config.min_samples:
        failures.append(
            f"evaluated_samples={report.evaluated_samples} is below min_samples={config.min_samples}"
        )
    if report.aggregate.faithfulness < config.faithfulness_threshold:
        failures.append(
            f"faithfulness={report.aggregate.faithfulness:.3f} "
            f"< threshold={config.faithfulness_threshold:.3f}"
        )
    if report.aggregate.context_recall < config.context_recall_threshold:
        failures.append(
            f"context_recall={report.aggregate.context_recall:.3f} "
            f"< threshold={config.context_recall_threshold:.3f}"
        )
    if report.aggregate.answer_relevance < config.answer_relevance_threshold:
        failures.append(
            f"answer_relevance={report.aggregate.answer_relevance:.3f} "
            f"< threshold={config.answer_relevance_threshold:.3f}"
        )
    return failures


def validate_config(config: EvaluationConfig) -> None:
    """Validate mandatory config values before starting network calls."""
    if not config.dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {config.dataset_path}")
    if not config.judge_base_url:
        raise ValueError("JUDGE_LLM_API_BASE_URL is required.")
    if not config.judge_model:
        raise ValueError("JUDGE_LLM_MODEL is required.")
    if not config.candidate_base_url:
        raise ValueError("CANDIDATE_LLM_API_BASE_URL is required.")
    if not config.candidate_model:
        raise ValueError("CANDIDATE_LLM_MODEL is required.")


def run_evaluation(config: EvaluationConfig) -> EvaluationReport:
    """Execute full LLM-as-a-judge evaluation pipeline and save report."""
    validate_config(config)

    dataset = load_golden_dataset(config.dataset_path)
    selected_samples = select_samples(dataset, config.sample_size, config.random_seed)
    if not selected_samples:
        raise ValueError("No samples available for evaluation.")

    answer_client = OpenAICompatibleClient(
        base_url=config.candidate_base_url,
        api_key=config.candidate_api_key,
        model=config.candidate_model,
        timeout_seconds=config.request_timeout_seconds,
    )
    judge_client = OpenAICompatibleClient(
        base_url=config.judge_base_url,
        api_key=config.judge_api_key,
        model=config.judge_model,
        timeout_seconds=config.request_timeout_seconds,
    )

    with temporary_plugin_index(selected_samples):
        results = _evaluate_samples(selected_samples, answer_client, judge_client, config)

    report = EvaluationReport(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        dataset_path=str(config.dataset_path),
        total_dataset_samples=len(dataset),
        evaluated_samples=len(results),
        sample_size_requested=config.sample_size,
        random_seed=config.random_seed,
        judge_model=config.judge_model,
        candidate_model=config.candidate_model,
        thresholds={
            "faithfulness": config.faithfulness_threshold,
            "context_recall": config.context_recall_threshold,
            "answer_relevance": config.answer_relevance_threshold,
            "min_samples": float(config.min_samples),
        },
        aggregate=_aggregate(results),
        samples=[_sanitize_sample_result(result, config) for result in results],
    )
    save_report(report, config.output_path)
    return report
