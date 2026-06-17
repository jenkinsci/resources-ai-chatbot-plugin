"""DeepEval metric policy for chatbot response evaluation."""

import os

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRecallMetric,
    FaithfulnessMetric,
)
from deepeval.models import OllamaModel

METRIC_THRESHOLD = 0.5

def build_metrics(
    judge_model_name: str,
    base_url: str,
    threshold: float = METRIC_THRESHOLD,
):
    """
    Build the DeepEval metrics used for chatbot response evaluation.

    Args:
        judge_model_name (str): Ollama judge model name passed to DeepEval.
        base_url (str): Ollama server base URL.
        threshold (float): Minimum passing score for each metric.

    Returns:
        list: Configured Faithfulness, Answer Relevancy, and Contextual Recall
        metric instances backed by the same Ollama judge model.
    """
    judge_model = OllamaModel(
        model=judge_model_name,
        base_url=base_url,
        temperature=0.1,
        generation_kwargs={
            "num_ctx": int(os.getenv("DEEPEVAL_JUDGE_NUM_CTX", "16384")),
            "num_predict": int(os.getenv("DEEPEVAL_JUDGE_NUM_PREDICT", "4028")),
            "seed": 42,
        },
    )
    metric_kwargs = {
        "model": judge_model,
        "threshold": threshold,
        "async_mode": False,
        "include_reason": False,
    }
    return [
        FaithfulnessMetric(**metric_kwargs),
        AnswerRelevancyMetric(**metric_kwargs),
        ContextualRecallMetric(**metric_kwargs),
    ]
