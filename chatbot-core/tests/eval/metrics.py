"""DeepEval metric policy for JenkinsBot response evaluation."""

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRecallMetric,
    FaithfulnessMetric,
)

THRESHOLD = 0.5
# The Threshold is 0.5 for testing purposes

def build_metrics():
    """Build temporary DeepEval metrics for response generation testing."""
    return [
        AnswerRelevancyMetric(threshold=THRESHOLD),
        ContextualRecallMetric(threshold=THRESHOLD),
        FaithfulnessMetric(threshold=THRESHOLD),
    ]
