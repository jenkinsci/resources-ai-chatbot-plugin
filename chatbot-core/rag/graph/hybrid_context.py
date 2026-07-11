"""Format graph retrieval results as prompt-ready retrieval context."""

import re
from pathlib import Path

from rag.graph.build_graph_artifacts import load_plugin_chunks
from rag.graph.models import GraphRelation, GraphRetrievalResult


GRAPH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLUGIN_CHUNKS_PATH = GRAPH_ROOT / "data" / "processed" / "chunks_plugin_docs.json"
CODE_BLOCK_PLACEHOLDER_PATTERN = r"\[\[(?:CODE_BLOCK|CODE_SNIPPET)_(\d+)\]\]"


def load_graph_context_chunks(
    path: Path = DEFAULT_PLUGIN_CHUNKS_PATH,
) -> list[dict]:
    """
    Load processed plugin chunks for graph context formatting.

    Args:
        path (Path): Path to the processed plugin chunk artifact.

    Returns:
        list[dict]: Plugin chunk records in corpus order.
    """
    return load_plugin_chunks(path)


def build_chunk_lookup(chunks: list[dict]) -> dict[str, dict]:
    """
    Build a chunk lookup map by chunk ID.

    Args:
        chunks (list[dict]): Plugin chunk records.

    Returns:
        dict[str, dict]: Mapping from chunk ID to chunk payload.
    """
    return {
        chunk["id"]: chunk
        for chunk in chunks
        if isinstance(chunk.get("id"), str)
    }


def reconstruct_chunk_text(chunk: dict) -> str:
    """
    Reconstruct stored chunk text with inline code blocks.

    Args:
        chunk (dict): Stored chunk payload.

    Returns:
        str: Reconstructed chunk text.
    """
    code_blocks = iter(chunk.get("code_blocks", []))

    def replace(_match):
        return next(code_blocks, "")

    return re.sub(
        CODE_BLOCK_PLACEHOLDER_PATTERN,
        replace,
        chunk.get("chunk_text", ""),
    ).strip()


def format_graph_relation(
    relation: GraphRelation,
    chunk_lookup: dict[str, dict] | None = None,
) -> str:
    """
    Format one graph relation as compact retrieval context.

    Args:
        relation (GraphRelation): Graph relation returned by traversal.
        chunk_lookup (dict[str, dict] | None): Optional chunk lookup by source chunk ID.

    Returns:
        str: Prompt-ready graph relation block.
    """
    relation_block = (
        "[Source: plugin_relation_graph]\n"
        f"{relation.source.name} {relation.relation} {relation.target.name}.\n"
        f"Evidence: {relation.evidence.evidence}"
    )

    source_chunk = None
    if chunk_lookup is not None:
        source_chunk = chunk_lookup.get(relation.evidence.source_chunk_id)

    if source_chunk is not None:
        chunk_text = reconstruct_chunk_text(source_chunk)
        if chunk_text:
            relation_block += f"\nContext:\n{chunk_text}"

    return relation_block + f"\nSource Chunk ID: {relation.evidence.source_chunk_id}"


def format_graph_retrieval_result(
    result: GraphRetrievalResult,
    chunk_lookup: dict[str, dict] | None = None,
) -> str:
    """
    Format a graph retrieval result as compact retrieval context.

    Args:
        result (GraphRetrievalResult): Graph retrieval output to format.
        chunk_lookup (dict[str, dict] | None): Optional chunk lookup by source chunk ID.

    Returns:
        str: Prompt-ready context built from graph relations.
    """
    if not result.relations:
        return ""

    relation_blocks = [
        format_graph_relation(relation, chunk_lookup=chunk_lookup)
        for relation in result.relations
    ]
    return "\n\n".join(relation_blocks)
