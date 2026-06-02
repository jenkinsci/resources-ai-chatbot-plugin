"""Generate retrieval_context for responses.json"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Default dataset paths for eval generation.
CORE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLDEN_DATASET = CORE_ROOT / "tests/eval/datasets/golden_dataset.json"
DEFAULT_RESPONSES = CORE_ROOT / "tests/eval/datasets/responses.json"

if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

try:
    from api.services import chat_service
    from utils import LoggerFactory
except ImportError as exc:
    raise RuntimeError("Could not import chatbot-core retrieval modules") from exc

logger = LoggerFactory.instance().get_logger("eval-generate-responses")
get_agent_tool_calls = getattr(chat_service, "_get_agent_tool_calls")
execute_search_tools = getattr(chat_service, "_execute_search_tools")


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


def retrieve_context_from_tools(question: str) -> list[str]:
    """Retrieve context through the production search tools."""
    tool_calls = get_agent_tool_calls(question)
    retrieved_context = execute_search_tools(tool_calls)
    return [retrieved_context] if retrieved_context.strip() else []


def build_response_entry(
    seed: dict[str, str],
    allow_empty_retrieval: bool,
) -> dict[str, Any]:
    """Build a retrieval-only eval response entry."""
    question = seed["input"]
    retrieval_context = retrieve_context_from_tools(question)
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
    allow_empty_retrieval: bool,
    max_items: int | None = None,
) -> list[dict[str, Any]]:
    """Generate retrieval-only eval responses from the golden dataset."""
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
    return parser.parse_args()


def main() -> None:
    """Generate and write the retrieval-only responses dataset."""
    args = parse_args()
    responses = generate_responses(
        golden_dataset=args.golden_dataset,
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
