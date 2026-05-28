"""Generate retrieval_context for responses.json"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

#Default dataset paths and RAG retrieval configuration for eval generation.
CORE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLDEN_DATASET = CORE_ROOT / "tests/eval/datasets/golden_dataset.json"
DEFAULT_RESPONSES = CORE_ROOT / "tests/eval/datasets/responses.json"
DEFAULT_RAG_SOURCES = ["plugins"]
DEFAULT_TOP_K = 3

if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0,str(CORE_ROOT))

try:
    from api.models.embedding_model import EMBEDDING_MODEL
    from rag.retriever.retrieve import get_relevant_documents
    from rag.retriever.retriever_utils import VECTOR_STORE_DIR
    from utils import LoggerFactory
except ImportError as exc:
    raise RuntimeError("Could not import chatbot-core RAG retriever modules") from exc

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

def normalize_context(value: Any) -> list[str]:
    """Normalize a dataset context field into a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]

def load_seed_records(golden_dataset: Path) -> list[dict[str, str]]:
    """Load eval question IDs and inputs from the golden dataset."""
    return[
        {
            "id": item["additional_metadata"]["id"],
            "input": item["input"],
        }
        for item in load_json_list(golden_dataset)
    ]

def parse_rag_sources(raw_sources: str) -> list[str]:
    """Convert comma-separated RAG source names into a list."""
    sources = [source.strip() for source in raw_sources.split(",") if source.strip()]
    if not sources:
        raise ValueError("--rag-sources must include at least one source name.")
    return sources

def _retrieve_from_source(
    question: str,
    source_name: str,
    top_k: int
) -> list[tuple[float, str, str]]:
    """Retrieve ranked chunks from a single RAG source."""
    index_path = os.path.join(VECTOR_STORE_DIR, f"{source_name}_index.idx")
    if not os.path.exists(index_path):
        logger.warning(
            "Skipping source '%s': FAISS index not found at %s. "
            "Build the embeddings for this source to include it in retrieval.",
            source_name,
            index_path,
        )
        return []
    data, scores = get_relevant_documents(
        question,
        EMBEDDING_MODEL,
        logger=logger,
        source_name=source_name,
        top_k=top_k,
    )
    return [
        (float(score), source_name, item.get("chunk_text", ""))
        for item, score in zip(data, scores)
        if item.get("chunk_text", "").strip()
    ]

def retrieve_context_from_rag(
    question: str,
    rag_sources: list[str],
    top_k: int,
) -> list[str]:
    """Retrieve relevant context chunks from configured RAG sources."""
    retrieved: list[tuple[float, str, str]] = []

    for source_name in rag_sources:
        retrieved.extend(_retrieve_from_source(question, source_name, top_k))

    retrieved.sort(key=lambda result: result[0])
    return [chunk_text for _, _source_name, chunk_text in retrieved]

def build_response_entry(
    seed: dict[str,str],
    rag_sources: list[str],
    top_k: int,
    allow_empty_retrieval: bool,
) -> dict[str, Any]:
    """Build a retrieval-only eval response entry."""
    question = seed["input"]
    retrieval_context = retrieve_context_from_rag(
        question = question,
        rag_sources= rag_sources,
        top_k = top_k
    )
    if not retrieval_context and not allow_empty_retrieval:
        raise RuntimeError(
            f"No RAG context retrieved for {seed['id']}. "
            "Check FAISS indexes/ runtime dependencies"
        )

    return {
        "id" : seed["id"],
        "input" : question,
        "actual_output": "",
        "retrieval_context": retrieval_context,
    }

def generate_responses(
    golden_dataset: Path,
    rag_sources: list[str],
    top_k: int,
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
                rag_sources=rag_sources,
                top_k=top_k,
                allow_empty_retrieval=allow_empty_retrieval,
            )
        )

    return responses

def main() -> None:
    """Generate and write the retrieval-only responses dataset."""
    responses = generate_responses(
        golden_dataset=DEFAULT_GOLDEN_DATASET,
        rag_sources=DEFAULT_RAG_SOURCES,
        top_k=DEFAULT_TOP_K,
        allow_empty_retrieval=False,
    )

    write_json_list(DEFAULT_RESPONSES, responses)

    logger.info(
        "Created %s with %d retrieval-only entries.",
        DEFAULT_RESPONSES,
        len(responses),
    )

if __name__ == "__main__":
    main()
