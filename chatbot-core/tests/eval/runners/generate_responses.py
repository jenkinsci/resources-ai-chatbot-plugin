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
from importlib import import_module
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

# Default dataset paths for eval generation.
CORE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVAL_CONFIG = CORE_ROOT / "tests/eval/config.json"
DEFAULT_GOLDEN_DATASET = CORE_ROOT / "tests/eval/datasets/golden_dataset.json"
DEFAULT_RESPONSES = CORE_ROOT / "tests/eval/datasets/responses.json"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_REQUEST_TIMEOUT = 300.0

if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

# Use test configuration to avoid local LLM initialization.
os.environ.setdefault("PYTEST_VERSION", "eval-runner")

logger = logging.getLogger("eval-generate-responses")


def configure_logging() -> None:
    """
    Configure runner logs for live GitHub Actions output.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        stream=sys.stdout,
    )


def load_retrieval_context_validator() -> Any:
    """
    Load the shared retrieval-context validator in both local and CI contexts.

    Returns:
        Any: Callable retrieval-context validation helper.
    """
    try:
        module = import_module("runners.validate_responses")
    except ModuleNotFoundError:
        module = import_module("tests.eval.runners.validate_responses")
    return module.has_valid_retrieval_context


has_valid_retrieval_context = load_retrieval_context_validator()


def load_eval_config(path: Path = DEFAULT_EVAL_CONFIG) -> dict[str, Any]:
    """
    Load the eval pipeline configuration used by local runs and CI.

    Args:
        path (Path): Path to the eval configuration JSON file.

    Returns:
        dict[str, Any]: Parsed eval configuration.
    """
    return json.loads(path.read_text(encoding="utf-8"))


EVAL_CONFIG = load_eval_config()
DEFAULT_RESPONSE_MODEL = str(EVAL_CONFIG["response_model"])
DEFAULT_MAX_TOKENS = int(EVAL_CONFIG["response_max_tokens"])
DEFAULT_NUM_CTX = int(EVAL_CONFIG["response_num_ctx"])
DEFAULT_TEMPERATURE = float(EVAL_CONFIG["response_temperature"])


@dataclass(frozen=True)
class GenerationConfig:
    """
    Output-generation settings.

    Args:
        response_model (str): Ollama model for output generation.
        ollama_url (str): Ollama base URL.
        max_tokens (int): Maximum generated tokens per response.
        num_ctx (int): Ollama context window size.
        temperature (float): Sampling temperature.
        request_timeout (float): HTTP request timeout in seconds.
    """

    response_model: str
    ollama_url: str
    max_tokens: int = DEFAULT_MAX_TOKENS
    num_ctx: int = DEFAULT_NUM_CTX
    temperature: float = DEFAULT_TEMPERATURE
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT


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
    try:
        chat_service = import_module("api.services.chat_service")
    except ImportError as exc:
        raise RuntimeError("Could not import chatbot retrieval modules") from exc

    execute_search_tools = getattr(chat_service, "_execute_search_tools")

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
    try:
        prompts = import_module("api.prompts.prompts")
    except ImportError as exc:
        raise RuntimeError("Could not import chatbot response prompt") from exc

    system_instruction = getattr(prompts, "SYSTEM_INSTRUCTION")
    context_text = "\n\n".join(retrieval_context).strip()
    return f"""{system_instruction}
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
    generation_config: GenerationConfig,
) -> str:
    """
    Generate actual_output with an Ollama model.

    Args:
        question (str): Eval input question.
        retrieval_context (list[str]): Context used to ground the answer.
        generation_config (GenerationConfig): Ollama generation settings.

    Returns:
        str: Generated answer text.

    Raises:
        RuntimeError: If Ollama is unavailable or returns an invalid response.
    """
    payload = {
        "model": generation_config.response_model,
        "prompt": build_response_prompt(question, retrieval_context),
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "num_predict": generation_config.max_tokens,
            "num_ctx": generation_config.num_ctx,
            "temperature": generation_config.temperature,
            "seed": 42,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    endpoint = generation_config.ollama_url.rstrip("/") + "/api/generate"
    req = request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(
            req, timeout=generation_config.request_timeout
        ) as response:  # nosec B310
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(
            "Could not generate eval output with Ollama. "
            f"Ensure Ollama is running and '{generation_config.response_model}' "
            "is pulled."
        ) from exc

    generated = result.get("response")
    if not isinstance(generated, str):
        raise RuntimeError("Ollama returned an invalid generation response.")
    return generated.strip()


def build_response_entry(
    seed: dict[str, str],
    allow_empty_retrieval: bool,
    generation_config: GenerationConfig | None,
) -> dict[str, Any]:
    """
    Build an eval response entry.

    Args:
        seed (dict[str, str]): Eval seed record with ID and input question.
        allow_empty_retrieval (bool): Whether to allow entries with empty
            retrieval context.
        generation_config (GenerationConfig | None): Output-generation settings,
            or None to leave actual_output empty.

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
    if generation_config is not None:
        actual_output = generate_output_with_ollama(
            question=question,
            retrieval_context=retrieval_context,
            generation_config=generation_config,
        )

    return {
        "id": seed["id"],
        "input": question,
        "actual_output": actual_output,
        "retrieval_context": retrieval_context,
    }


def select_records(
    records: list[dict[str, Any]],
    offset: int,
    limit: int | None,
) -> list[dict[str, Any]]:
    """Select a contiguous range of records for one workflow shard."""
    if offset < 0 or offset >= len(records):
        raise ValueError(f"offset must be between 0 and {len(records) - 1}")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")

    selected = records[offset:] if limit is None else records[offset : offset + limit]
    if limit is not None and len(selected) != limit:
        raise ValueError(
            f"Requested {limit} records at offset {offset}, found {len(selected)}"
        )
    return selected


def generate_outputs_from_responses(
    source_responses: Path,
    generation_config: GenerationConfig,
    offset: int = 0,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Fill actual_output using retrieval context stored in a response artifact."""
    source_records = load_json_list(source_responses)
    selected_records = select_records(source_records, offset, limit)
    generated_records: list[dict[str, Any]] = []

    for index, source_record in enumerate(selected_records, start=1):
        question_id = source_record.get("id")
        question = source_record.get("input")
        retrieval_context = source_record.get("retrieval_context")
        if not isinstance(question_id, str) or not question_id:
            raise ValueError("Every response entry must contain a valid id")
        if not isinstance(question, str) or not question:
            raise ValueError(f"{question_id}: input is invalid")
        if not has_valid_retrieval_context(retrieval_context):
            raise ValueError(f"{question_id}: retrieval_context is empty or invalid")

        logger.info(
            "[%d/%d] Generating %s input_chars=%d context_chars=%d",
            index,
            len(selected_records),
            question_id,
            len(question),
            sum(len(value) for value in retrieval_context),
        )
        started = time.perf_counter()
        actual_output = generate_output_with_ollama(
            question=question,
            retrieval_context=retrieval_context,
            generation_config=generation_config,
        )
        logger.info(
            "%s completed in %.3f seconds output_chars=%d",
            question_id,
            time.perf_counter() - started,
            len(actual_output),
        )
        logger.info("%s actual_output:\n%s", question_id, actual_output)

        generated_records.append(
            {
                "id": question_id,
                "input": question,
                "actual_output": actual_output,
                "retrieval_context": retrieval_context,
            }
        )

    return generated_records


def generate_responses(
    golden_dataset: Path,
    allow_empty_retrieval: bool,
    generation_config: GenerationConfig | None,
    offset: int = 0,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Generate eval responses from the golden dataset.

    Args:
        golden_dataset (Path): Path to the golden dataset JSON file.
        allow_empty_retrieval (bool): Whether to allow empty retrieval context.
        generation_config (GenerationConfig | None): Output-generation settings,
            or None for retrieval-only mode.
        offset (int): Zero-based dataset offset.
        limit (int | None): Optional number of records to process.

    Returns:
        list[dict[str, Any]]: Generated response entries.

    Raises:
        ValueError: If duplicate eval IDs are found.
    """
    seed_records = load_seed_records(golden_dataset)

    seen_ids: set[str] = set()
    responses: list[dict[str, Any]] = []

    selected_records = select_records(seed_records, offset, limit)

    for index, seed in enumerate(selected_records, start=1):
        question_id = seed["id"]

        if question_id in seen_ids:
            raise ValueError(f"Duplicate eval id found: {question_id}")

        seen_ids.add(question_id)

        logger.info(
            "[%d/%d] Building response entry %s",
            index,
            len(selected_records),
            question_id,
        )
        started = time.perf_counter()
        responses.append(
            build_response_entry(
                seed=seed,
                allow_empty_retrieval=allow_empty_retrieval,
                generation_config=generation_config,
            )
        )
        elapsed = time.perf_counter() - started
        logger.info("%s completed in %.3f seconds", question_id, elapsed)

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
        "--source-responses",
        type=Path,
        default=None,
        help="Retrieval-complete responses artifact used by --generation-only.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Zero-based record offset used for sharded execution.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional number of records to process from the offset.",
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
        "--generation-only",
        action="store_true",
        help="Fill actual_output from an existing retrieval-complete artifact.",
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
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="Maximum generated tokens per response.",
    )
    parser.add_argument(
        "--num-ctx",
        type=int,
        default=DEFAULT_NUM_CTX,
        help="Ollama context window size.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help="Ollama sampling temperature.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=DEFAULT_REQUEST_TIMEOUT,
        help="Ollama request timeout in seconds.",
    )
    return parser.parse_args()


def main() -> None:
    """Generate and write the responses dataset."""
    configure_logging()
    args = parse_args()
    if args.retrieval_only and args.generation_only:
        raise ValueError("--retrieval-only and --generation-only are mutually exclusive")

    generation_config = GenerationConfig(
        response_model=args.response_model,
        ollama_url=args.ollama_url,
        max_tokens=args.max_tokens,
        num_ctx=args.num_ctx,
        temperature=args.temperature,
        request_timeout=args.request_timeout,
    )
    if args.generation_only:
        source_responses = args.source_responses or args.responses
        responses = generate_outputs_from_responses(
            source_responses=source_responses,
            generation_config=generation_config,
            offset=args.offset,
            limit=args.limit,
        )
    else:
        responses = generate_responses(
            golden_dataset=args.golden_dataset,
            allow_empty_retrieval=args.allow_empty_retrieval,
            generation_config=None if args.retrieval_only else generation_config,
            offset=args.offset,
            limit=args.limit,
        )

    write_json_list(args.responses, responses)

    logger.info(
        "Created %s with %d response entries.",
        args.responses,
        len(responses),
    )

if __name__ == "__main__":
    main()
