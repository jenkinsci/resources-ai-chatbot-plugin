"""
LLM-as-a-Judge Evaluation Pipeline for Jenkins AI Chatbot.

Sends predefined test questions to the chatbot API, then uses
a secondary LLM evaluation to score responses on three dimensions:
  - Faithfulness: Is the response grounded in Jenkins documentation?
  - Relevance: Does the response address the question asked?
  - Completeness: Does the response cover the key topics expected?

Usage:
    python -m evaluation.evaluate

    # With a custom API URL:
    python -m evaluation.evaluate --api-url http://localhost:8000

    # Save results to a specific file:
    python -m evaluation.evaluate --output results/eval_run_1.json

Requirements:
    - The chatbot API must be running (e.g., via `make api` or `make dev-lite`)
    - For full evaluation with LLM scoring, set GROQ_API_KEY in your environment
      or in a .env file. Without it, only topic-match scoring is performed.
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path

import requests

# Optional: LLM-based scoring via Groq (free tier, Llama 3)
try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ============================================================
# Configuration
# ============================================================

DEFAULT_API_URL = "http://localhost:8000"
QUESTIONS_FILE = Path(__file__).parent / "test_questions.json"
DEFAULT_OUTPUT = Path(__file__).parent / "results" / "evaluation_report.json"

JUDGE_PROMPT = """You are an expert evaluator for a Jenkins CI/CD documentation chatbot.

Given a question and the chatbot's response, score the response on three dimensions.
Each score should be an integer from 1 to 5.

**Faithfulness** (1-5): Is the information accurate and grounded in real Jenkins
documentation? Deduct points for hallucinated features, wrong plugin names, or
incorrect instructions.

**Relevance** (1-5): Does the response directly address the question asked?
Deduct points for off-topic content or generic filler.

**Completeness** (1-5): Does the response cover the key aspects a Jenkins user
would need? Deduct points for missing critical steps or important caveats.

Question: {question}

Chatbot Response: {response}

Respond in this exact JSON format and nothing else:
{{"faithfulness": <score>, "relevance": <score>, "completeness": <score>, "reasoning": "<brief explanation>"}}
"""


# ============================================================
# Topic-Match Scoring (works without external LLM)
# ============================================================

def compute_topic_coverage(response_text, expected_topics):
    """
    Computes what fraction of expected topics appear in the response.

    Args:
        response_text: The chatbot's response string.
        expected_topics: List of topic keywords to check for.

    Returns:
        float: Score between 0.0 and 1.0.
    """
    if not expected_topics:
        return 1.0

    response_lower = response_text.lower()
    hits = sum(1 for topic in expected_topics if topic.lower() in response_lower)
    return round(hits / len(expected_topics), 2)


# ============================================================
# LLM-as-a-Judge Scoring (requires Groq API key)
# ============================================================

def get_llm_judge_scores(question, response_text):
    """
    Uses a secondary LLM to evaluate the chatbot response quality.

    Returns:
        dict with faithfulness, relevance, completeness scores and reasoning,
        or None if LLM scoring is unavailable.
    """
    if not GROQ_AVAILABLE:
        return None

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        prompt = JUDGE_PROMPT.format(question=question, response=response_text)
        result = llm.invoke(prompt)

        # Parse JSON from response
        content = result.content.strip()
        # Handle potential markdown code fences
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        scores = json.loads(content)
        return {
            "faithfulness": int(scores.get("faithfulness", 0)),
            "relevance": int(scores.get("relevance", 0)),
            "completeness": int(scores.get("completeness", 0)),
            "reasoning": scores.get("reasoning", ""),
        }
    except Exception as e:
        print(f"  Warning: LLM judge scoring failed: {e}")
        return None


# ============================================================
# Chatbot API Client
# ============================================================

def create_session(api_url):
    """Creates a new chatbot session and returns the session_id."""
    resp = requests.post(f"{api_url}/api/chatbot/sessions", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("session_id")


def send_message(api_url, session_id, message):
    """Sends a message to the chatbot and returns the reply."""
    resp = requests.post(
        f"{api_url}/api/chatbot/sessions/{session_id}/message",
        json={"message": message},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("reply", "")


def delete_session(api_url, session_id):
    """Deletes a chatbot session."""
    try:
        requests.delete(
            f"{api_url}/api/chatbot/sessions/{session_id}", timeout=10
        )
    except requests.RequestException:
        pass


# ============================================================
# Main Evaluation Loop
# ============================================================

def run_evaluation(api_url, output_path):
    """
    Runs the full evaluation pipeline:
    1. Load test questions
    2. For each question, create a session, send the question, collect the response
    3. Score the response (topic coverage + optional LLM judge)
    4. Aggregate results and write report
    """
    # Load questions
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"Loaded {len(questions)} test questions")
    print(f"API URL: {api_url}")
    print(f"LLM Judge: {'enabled (Groq)' if GROQ_AVAILABLE and os.getenv('GROQ_API_KEY') else 'disabled (topic-match only)'}")
    print("-" * 60)

    results = []
    total_topic_score = 0
    total_llm_scores = {"faithfulness": 0, "relevance": 0, "completeness": 0}
    llm_scored_count = 0

    for i, q in enumerate(questions, 1):
        qid = q["id"]
        question = q["question"]
        expected_topics = q.get("expected_topics", [])

        print(f"[{i}/{len(questions)}] {qid}: {question[:60]}...")

        # Create session, send question, get response
        session_id = None
        try:
            session_id = create_session(api_url)
            start_time = time.time()
            response_text = send_message(api_url, session_id, question)
            latency_ms = round((time.time() - start_time) * 1000)
        except requests.RequestException as e:
            print(f"  Error: API request failed: {e}")
            results.append({
                "id": qid,
                "question": question,
                "error": str(e),
            })
            continue
        finally:
            if session_id:
                delete_session(api_url, session_id)

        # Score: topic coverage
        topic_score = compute_topic_coverage(response_text, expected_topics)
        total_topic_score += topic_score

        # Score: LLM judge (if available)
        llm_scores = get_llm_judge_scores(question, response_text)
        if llm_scores:
            llm_scored_count += 1
            for key in total_llm_scores:
                total_llm_scores[key] += llm_scores[key]

        result_entry = {
            "id": qid,
            "question": question,
            "category": q.get("category", ""),
            "difficulty": q.get("difficulty", ""),
            "response": response_text[:500],
            "response_length": len(response_text),
            "latency_ms": latency_ms,
            "topic_coverage": topic_score,
            "expected_topics": expected_topics,
        }

        if llm_scores:
            result_entry["llm_judge"] = llm_scores

        results.append(result_entry)
        print(f"  Topic coverage: {topic_score:.0%} | Latency: {latency_ms}ms", end="")
        if llm_scores:
            print(f" | F:{llm_scores['faithfulness']} R:{llm_scores['relevance']} C:{llm_scores['completeness']}", end="")
        print()

    # Aggregate summary
    answered = [r for r in results if "error" not in r]
    n = len(answered)

    summary = {
        "total_questions": len(questions),
        "successfully_answered": n,
        "errors": len(questions) - n,
        "avg_topic_coverage": round(total_topic_score / n, 2) if n else 0,
        "avg_latency_ms": round(sum(r.get("latency_ms", 0) for r in answered) / n) if n else 0,
    }

    if llm_scored_count > 0:
        summary["llm_judge_avg"] = {
            key: round(val / llm_scored_count, 2)
            for key, val in total_llm_scores.items()
        }
        summary["llm_judge_scored_count"] = llm_scored_count

    report = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_url": api_url,
            "questions_file": str(QUESTIONS_FILE),
            "llm_judge_enabled": llm_scored_count > 0,
        },
        "summary": summary,
        "results": results,
    }

    # Write report
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Questions answered: {n}/{len(questions)}")
    print(f"Avg topic coverage: {summary['avg_topic_coverage']:.0%}")
    print(f"Avg latency: {summary['avg_latency_ms']}ms")
    if "llm_judge_avg" in summary:
        avg = summary["llm_judge_avg"]
        print(f"LLM Judge Avg - Faithfulness: {avg['faithfulness']}/5, "
              f"Relevance: {avg['relevance']}/5, "
              f"Completeness: {avg['completeness']}/5")
    print(f"\nReport saved to: {output_path}")

    return report


# ============================================================
# CLI Entry Point
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the Jenkins AI Chatbot response quality"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"Chatbot API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output path for the evaluation report (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    run_evaluation(args.api_url, args.output)


if __name__ == "__main__":
    main()
