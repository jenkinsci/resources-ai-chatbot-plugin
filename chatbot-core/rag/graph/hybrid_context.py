"""Format graph retrieval results as prompt-ready retrieval context."""

import json
import re
from pathlib import Path

from rag.graph.models import GraphRelation, GraphRetrievalResult


GRAPH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLUGIN_CHUNKS_PATH = GRAPH_ROOT / "data" / "processed" / "chunks_plugin_docs.json"
CODE_BLOCK_PLACEHOLDER_PATTERN = r"\[\[(?:CODE_BLOCK|CODE_SNIPPET)_(\d+)\]\]"


def load_graph_context_chunks(
    path: Path = DEFAULT_PLUGIN_CHUNKS_PATH,
) -> list[dict]:
    """
    Load processed plugin chunks used for graph context expansion.

    Args:
        path (Path): Path to the processed plugin chunk artifact.

    Returns:
        list[dict]: Plugin chunk records in corpus order.
    """
    with path.open(encoding="utf-8") as chunks_file:
        chunks = json.load(chunks_file)
    return [chunk for chunk in chunks if isinstance(chunk, dict)]


def build_chunk_position_map(chunks: list[dict]) -> dict[str, int]:
    """
    Build a chunk ID to corpus-position map.

    Args:
        chunks (list[dict]): Plugin chunk records in corpus order.

    Returns:
        dict[str, int]: Mapping from chunk ID to list position.
    """
    return {
        chunk["id"]: index
        for index, chunk in enumerate(chunks)
        if isinstance(chunk.get("id"), str)
    }


def reconstruct_chunk_text(chunk: dict) -> str:
    """
    Reconstruct chunk text by replacing code block placeholders.

    Args:
        chunk (dict): Stored chunk payload.

    Returns:
        str: Chunk text with inline code block substitutions when present.
    """
    code_blocks = iter(chunk.get("code_blocks", []))

    def replace(_match):
        return next(code_blocks, "")

    return re.sub(
        CODE_BLOCK_PLACEHOLDER_PATTERN,
        replace,
        chunk.get("chunk_text", ""),
    ).strip()


def expand_relation_context_chunks(
    relation: GraphRelation,
    chunks: list[dict],
    chunk_positions: dict[str, int],
    window_size: int = 1,
) -> list[dict]:
    """
    Expand a relation's source chunk into a small local chunk window.

    Args:
        relation (GraphRelation): Graph relation anchored to a source chunk.
        chunks (list[dict]): Plugin chunk records in corpus order.
        chunk_positions (dict[str, int]): Mapping from chunk ID to corpus position.
        window_size (int): Number of neighboring chunks to inspect on each side.

    Returns:
        list[dict]: Neighboring chunks from the same plugin document.
    """
    chunk_index = chunk_positions.get(relation.evidence.source_chunk_id)
    if chunk_index is None:
        return []

    anchor_chunk = chunks[chunk_index]
    anchor_metadata = anchor_chunk.get("metadata", {})
    anchor_title = anchor_metadata.get("title")
    anchor_source = anchor_metadata.get("data_source")
    context_chunks = []

    start_index = max(0, chunk_index - window_size)
    end_index = min(len(chunks), chunk_index + window_size + 1)

    for neighbor_chunk in chunks[start_index:end_index]:
        neighbor_metadata = neighbor_chunk.get("metadata", {})
        if neighbor_metadata.get("title") != anchor_title:
            continue
        if neighbor_metadata.get("data_source") != anchor_source:
            continue
        context_chunks.append(neighbor_chunk)

    return context_chunks


def format_relation_context_window(context_chunks: list[dict]) -> str:
    """
    Format a local chunk window as compact supporting context.

    Args:
        context_chunks (list[dict]): Neighboring chunks around the evidence anchor.

    Returns:
        str: Combined local chunk context.
    """
    context_texts = [
        reconstruct_chunk_text(chunk)
        for chunk in context_chunks
    ]
    context_texts = [text for text in context_texts if text]
    return "\n\n".join(context_texts)


def format_graph_relation(
    relation: GraphRelation,
    context_chunks: list[dict] | None = None,
) -> str:
    """
    Format one graph relation as a compact retrieval context block.

    Args:
        relation (GraphRelation): Graph relation returned by traversal.
        context_chunks (list[dict] | None): Neighboring chunks around the evidence anchor.

    Returns:
        str: Prompt-ready graph relation block.
    """
    relation_block = (
        "[Source: plugin_relation_graph]\n"
        f"{relation.source.name} {relation.relation} {relation.target.name}.\n"
        f"Evidence: {relation.evidence.evidence}"
    )
    if not context_chunks:
        return relation_block

    expanded_context = format_relation_context_window(context_chunks)
    if not expanded_context:
        return relation_block

    return relation_block + "\nContext:\n" + expanded_context


def format_graph_retrieval_result(
    result: GraphRetrievalResult,
    chunks: list[dict] | None = None,
    chunk_positions: dict[str, int] | None = None,
    window_size: int = 1,
) -> str:
    """
    Format a graph retrieval result as compact retrieval context.

    Args:
        result (GraphRetrievalResult): Graph retrieval output to format.
        chunks (list[dict] | None): Plugin chunk corpus for local context expansion.
        chunk_positions (dict[str, int] | None): Mapping from chunk ID to corpus position.
        window_size (int): Number of neighboring chunks to inspect on each side.

    Returns:
        str: Prompt-ready context built from graph relations.
    """
    if not result.relations:
        return ""

    relation_blocks = [
        format_graph_relation(
            relation,
            context_chunks=(
                expand_relation_context_chunks(
                    relation,
                    chunks,
                    chunk_positions,
                    window_size=window_size,
                )
                if chunks is not None and chunk_positions is not None
                else None
            ),
        )
        for relation in result.relations
    ]

    return "\n\n".join(relation_blocks)
