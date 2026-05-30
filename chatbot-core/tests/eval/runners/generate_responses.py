"""Generate retrieval_context for responses.json"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path
from typing import Any

# Default dataset paths and retrieval tools for eval generation.
CORE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLDEN_DATASET = CORE_ROOT / "tests/eval/datasets/golden_dataset.json"
DEFAULT_RESPONSES = CORE_ROOT / "tests/eval/datasets/responses.json"
DEFAULT_SEARCH_TOOLS = [
    "search_jenkins_docs",
    "search_plugin_docs",
    "search_community_threads",
]
DEFAULT_TOP_K = 3

if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

try:
    from api.tools import tools as search_tools_module
    from utils import LoggerFactory
except ImportError as exc:
    raise RuntimeError("Could not import chatbot-core retrieval modules") from exc

TOOL_REGISTRY = search_tools_module.TOOL_REGISTRY
logger = LoggerFactory.instance().get_logger("eval-generate-responses")

def load_json_list(path: Path) -> list[dict[str, Any]]:
    """Load a JSON file containing a list of objects."""
    with path.open(encoding="utf-8") as f:
        return json.load(f)

def write_json_list(path: Path, data: list[dict[str, Any]]) -> None:
    """Write a list of objects to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

def load_seed_records(golden_dataset: Path) -> list[dict[str, str]]:
    """Load eval question IDs and inputs from the golden dataset."""
    return [
        {
            "id": item["additional_metadata"]["id"],
            "input": item["input"],
        }
        for item in load_json_list(golden_dataset)
    ]


def parse_csv(raw_value: str) -> list[str]:
    """Convert comma-separated values into a non-empty list."""
    values = [value.strip() for value in raw_value.split(",") if value.strip()]
    if not values:
        raise ValueError("Comma-separated arguments must include at least one value.")
    return values


def configure_top_k(top_k: int) -> None:
    """Set final per-tool chunk count for this eval generation run."""
    if top_k < 1:
        raise ValueError("--top-k must be at least 1.")

    for config_key in ("top_k_docs", "top_k_plugins", "top_k_discourse"):
        search_tools_module.retrieval_config[config_key] = top_k


def build_tool_calls(question: str, search_tools: list[str]) -> list[dict[str, Any]]:
    """Build production search-tool calls for an eval question."""
    tool_calls = []

    for tool_name in search_tools:
        params: dict[str, Any] = {"query": question}
        if tool_name != "search_stackoverflow_threads":
            params["keywords"] = question
        if tool_name == "search_plugin_docs":
            params["plugin_name"] = None
        tool_calls.append({"tool": tool_name, "params": params})

    return tool_calls


def execute_search_tools(tool_calls: list[dict[str, Any]]) -> str:
    """Run production search tools and format their retrieved context."""
    retrieved_results = []

    for call in tool_calls:
        tool_name = call.get("tool")
        params = dict(call.get("params") or {})
        tool_fn = TOOL_REGISTRY.get(tool_name)

        if tool_fn is None:
            logger.warning("Unknown tool '%s'; skipping.", tool_name)
            continue

        if "logger" in inspect.signature(tool_fn).parameters:
            params.setdefault("logger", logger)

        retrieved_results.append({
            "tool": tool_name,
            "output": tool_fn(**params),
        })

    return "\n\n".join(
        f"[Result of the search tool {result['tool']}]:\n{result.get('output', '')}".strip()
        for result in retrieved_results
    )


def retrieve_context_from_tools(question: str, search_tools: list[str]) -> list[str]:
    """Retrieve context through the production search tools."""
    retrieved_context = execute_search_tools(build_tool_calls(question, search_tools))
    return [retrieved_context] if retrieved_context.strip() else []

def build_response_entry(
    seed: dict[str, str],
    search_tools: list[str],
    allow_empty_retrieval: bool,
) -> dict[str, Any]:
    """Build a retrieval-only eval response entry."""
    question = seed["input"]
    retrieval_context = retrieve_context_from_tools(question, search_tools)
    if not retrieval_context and not allow_empty_retrieval:
        raise RuntimeError(
            f"No RAG context retrieved for {seed['id']}. "
            "Check retrieval indexes and runtime dependencies."
        )

    return {
        "id": seed["id"],
        "input": question,
        "actual_output": "",
        "retrieval_context": retrieval_context,
    }

def generate_responses(
    golden_dataset: Path,
    search_tools: list[str],
    top_k: int,
    allow_empty_retrieval: bool,
    max_items: int | None = None,
) -> list[dict[str, Any]]:
    """Generate retrieval-only eval responses from the golden dataset."""
    configure_top_k(top_k)
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
                search_tools=search_tools,
                allow_empty_retrieval=allow_empty_retrieval,
            )
        )

    return responses


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for response generation."""
    parser = argparse.ArgumentParser(
        description="Generate retrieval_context entries for responses.json."
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
        "--search-tools",
        default=",".join(DEFAULT_SEARCH_TOOLS),
        help="Comma-separated production search tools to run for each question.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Optional maximum number of golden records to process.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Number of final chunks each production search tool returns.",
    )
    parser.add_argument(
        "--allow-empty-retrieval",
        action="store_true",
        help="Allow response entries when no retrieval context is returned.",
    )
    return parser.parse_args()


def main() -> None:
    """Generate and write the retrieval-only responses dataset."""
    args = parse_args()
    search_tools = parse_csv(args.search_tools)
    responses = generate_responses(
        golden_dataset=args.golden_dataset,
        search_tools=search_tools,
        top_k=args.top_k,
        allow_empty_retrieval=args.allow_empty_retrieval,
        max_items=args.max_items,
    )

    write_json_list(args.responses, responses)

    logger.info(
        "Created %s with %d retrieval-only entries.",
        args.responses,
        len(responses),
    )

if __name__ == "__main__":
    main()
