"""
Generate response entries for responses.json.

This runner reads questions from the golden dataset and writes response entries.
Retrieval is routed through the production chat service search tool executor so
the eval dataset uses the same retrievers as the chatbot.

The runner intentionally skips chat_service._get_agent_tool_calls(). That helper
uses the local chat LLM to choose tools and produce tool parameters. For this
eval dataset, the runner directly executes all configured retrieval tools with
the input question. In normal mode it then generates actual_output from the
retrieved context with local Ollama.
"""

import argparse
from dataclasses import dataclass
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

# Default dataset paths for eval generation.
CORE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLDEN_DATASET = CORE_ROOT / "tests/eval/datasets/golden_dataset.json"
DEFAULT_RESPONSES = CORE_ROOT / "tests/eval/datasets/responses.json"
DEFAULT_RESPONSE_MODEL = "qwen3:4b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
RESPONSE_TEMPERATURE = 0.2

if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

# Use test configuration to avoid local LLM initialization.
os.environ.setdefault("PYTEST_VERSION", "eval-runner")

try:
    from api.prompts.prompts import SYSTEM_INSTRUCTION
    from api.services import chat_service
    from utils import LoggerFactory
except ImportError as exc:
    raise RuntimeError("Could not import chatbot-core eval modules") from exc

logger = LoggerFactory.instance().get_logger("eval-generate-responses")
execute_search_tools = getattr(chat_service, "_execute_search_tools")


@dataclass(frozen=True)
class GenerationConfig:
    """
    Output-generation settings.

    Args:
        retrieval_only (bool): Whether to skip output generation.
        response_model (str): Ollama model for output generation.
        ollama_url (str): Ollama base URL.
    """

    retrieval_only: bool
    response_model: str
    ollama_url: str


def load_json_list(path: Path) -> list[dict[str, Any]]:
    """
    Load a JSON file containing a list of objects.

    Args:
        path (Path): Path to the JSON file.

    Returns:
        list[dict[str, Any]]: Parsed JSON records.
    """
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json_list(path: Path, data: list[dict[str, Any]]) -> None:
    """
    Write a list of objects to a JSON file.

    Args:
        path (Path): Path where the JSON file should be written.
        data (list[dict[str, Any]]): JSON-serializable records to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_seed_records(golden_dataset: Path) -> list[dict[str, str]]:
    """
    Load eval question IDs and inputs from the golden dataset.

    Args:
        golden_dataset (Path): Path to the golden dataset JSON file.

    Returns:
        list[dict[str, str]]: Records containing the eval ID and input question.
    """
    return [
        {
            "id": item["additional_metadata"]["id"],
            "input": item["input"],
        }
        for item in load_json_list(golden_dataset)
    ]


def retrieve_context_from_tools(question: str) -> list[str]:
    """
    Retrieve context through the production search tool executor.

    The production chatbot first calls chat_service._get_agent_tool_calls() to
    let the local LLM decide which tools to call. This eval runner skips that
    planning step and executes every configured retrieval tool directly because
    it only needs retrieval_context, not an LLM-planned answer.

    Args:
        question (str): User question to retrieve context for.

    Returns:
        list[str]: Retrieved context as a single-item list, or an empty list
        when no context is returned.
    """
    # Use the input question as both query and keywords so each retrieval tool
    # can run without LLM-generated tool parameters.
    tool_calls = [
        {
            "tool": "search_jenkins_docs",
            "params": {
                "query": question,
                "keywords": question,
            },
        },
        {
            "tool": "search_plugin_docs",
            "params": {
                "query": question,
                "keywords": question,
                "plugin_name": None,
            },
        },
        {
            "tool": "search_stackoverflow_threads",
            "params": {
                "query": question,
            },
        },
        {
            "tool": "search_community_threads",
            "params": {
                "query": question,
                "keywords": question,
            },
        },
    ]
    retrieved_context = execute_search_tools(tool_calls)
    return [retrieved_context] if retrieved_context.strip() else []


def build_response_prompt(question: str, retrieval_context: list[str]) -> str:
    """
    Build the response-generation prompt using the production system prompt.

    Args:
        question (str): Eval input question.
        retrieval_context (list[str]): Retrieved Jenkins context.

    Returns:
        str: Prompt for the response-generation model.
    """
    context_text = "\n\n".join(retrieval_context).strip()
    return f"""{SYSTEM_INSTRUCTION}
            Chat History:

            Context (Documentation & Knowledge Base):
            {context_text}
            User Question:
            {question.strip()}

            Answer:
            """


def generate_output_with_ollama(
    question: str,
    retrieval_context: list[str],
    model: str,
    ollama_url: str,
) -> str:
    """
    Generate actual_output with an Ollama model.

    Args:
        question (str): Eval input question.
        retrieval_context (list[str]): Context used to ground the answer.
        model (str): Ollama model name.
        ollama_url (str): Base URL for Ollama.

    Returns:
        str: Generated answer text.

    Raises:
        RuntimeError: If Ollama is unavailable or returns an invalid response.
    """
    payload = {
        "model": model,
        "prompt": build_response_prompt(question, retrieval_context),
        "stream": False,
        "options": {
            "temperature": RESPONSE_TEMPERATURE,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    endpoint = ollama_url.rstrip("/") + "/api/generate"
    req = request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as response:  # nosec B310
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(
            "Could not generate eval output with Ollama. "
            f"Ensure Ollama is running and '{model}' is pulled."
        ) from exc

    generated = result.get("response")
    if not isinstance(generated, str):
        raise RuntimeError("Ollama returned an invalid generation response.")
    return generated.strip()


def build_response_entry(
    seed: dict[str, str],
    allow_empty_retrieval: bool,
    generation_config: GenerationConfig,
) -> dict[str, Any]:
    """
    Build an eval response entry.

    Args:
        seed (dict[str, str]): Eval seed record with ID and input question.
        allow_empty_retrieval (bool): Whether to allow entries with empty
            retrieval context.
        generation_config (GenerationConfig): Output-generation settings.

    Returns:
        dict[str, Any]: Response entry with actual_output and retrieved context.

    Raises:
        RuntimeError: If no context is retrieved and empty retrieval is not
        allowed.
    """
    question = seed["input"]
    retrieval_context = retrieve_context_from_tools(question)
    if not retrieval_context and not allow_empty_retrieval:
        raise RuntimeError(
            f"No RAG context retrieved for {seed['id']}. "
            "Check retrieval indexes and runtime dependencies."
        )

    actual_output = ""
    if not generation_config.retrieval_only:
        actual_output = generate_output_with_ollama(
            question=question,
            retrieval_context=retrieval_context,
            model=generation_config.response_model,
            ollama_url=generation_config.ollama_url,
        )

    return {
        "id": seed["id"],
        "input": question,
        "actual_output": actual_output,
        "retrieval_context": retrieval_context,
    }


def generate_responses(
    golden_dataset: Path,
    allow_empty_retrieval: bool,
    generation_config: GenerationConfig,
    max_items: int | None = None,
) -> list[dict[str, Any]]:
    """
    Generate eval responses from the golden dataset.

    Args:
        golden_dataset (Path): Path to the golden dataset JSON file.
        allow_empty_retrieval (bool): Whether to allow empty retrieval context.
        generation_config (GenerationConfig): Output-generation settings.
        max_items (int | None): Optional maximum number of records to process.

    Returns:
        list[dict[str, Any]]: Generated response entries.

    Raises:
        ValueError: If duplicate eval IDs are found.
    """
    seed_records = load_seed_records(golden_dataset)

    seen_ids: set[str] = set()
    responses: list[dict[str, Any]] = []

    selected_records = seed_records[:max_items] if max_items else seed_records

    for seed in selected_records:
        question_id = seed["id"]

        if question_id in seen_ids:
            raise ValueError(f"Duplicate eval id found: {question_id}")

        seen_ids.add(question_id)

        responses.append(
            build_response_entry(
                seed=seed,
                allow_empty_retrieval=allow_empty_retrieval,
                generation_config=generation_config,
            )
        )

    return responses


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for response generation.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate retrieval_context and actual_output entries for responses.json."
    )
    parser.add_argument(
        "--golden-dataset",
        type=Path,
        default=DEFAULT_GOLDEN_DATASET,
        help="Path to the golden dataset JSON file.",
    )
    parser.add_argument(
        "--responses",
        type=Path,
        default=DEFAULT_RESPONSES,
        help="Path where generated responses JSON should be written.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Optional maximum number of golden records to process.",
    )
    parser.add_argument(
        "--allow-empty-retrieval",
        action="store_true",
        help="Allow response entries when no retrieval context is returned.",
    )
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Only fill retrieval_context and leave actual_output empty.",
    )
    parser.add_argument(
        "--response-model",
        default=os.getenv("EVAL_RESPONSE_MODEL", DEFAULT_RESPONSE_MODEL),
        help="Ollama model used for output generation.",
    )
    parser.add_argument(
        "--ollama-url",
        default=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL),
        help="Ollama base URL used for output generation.",
    )
    return parser.parse_args()


def main() -> None:
    """Generate and write the responses dataset."""
    args = parse_args()
    generation_config = GenerationConfig(
        retrieval_only=args.retrieval_only,
        response_model=args.response_model,
        ollama_url=args.ollama_url,
    )
    responses = generate_responses(
        golden_dataset=args.golden_dataset,
        allow_empty_retrieval=args.allow_empty_retrieval,
        generation_config=generation_config,
        max_items=args.max_items,
    )

    write_json_list(args.responses, responses)

    logger.info(
        "Created %s with %d response entries.",
        args.responses,
        len(responses),
    )

if __name__ == "__main__":
    main()
