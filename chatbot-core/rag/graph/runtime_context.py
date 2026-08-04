"""Runtime helpers for optional GraphRAG context retrieval."""

from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from rag.graph.entity_normalizer import DEFAULT_PLUGIN_NAMES_PATH
from rag.graph.graph_retriever import (
    load_plugin_relation_graph,
    load_query_plugin_aliases,
    retrieve_graph_relations,
)
from rag.graph.graph_store import DEFAULT_PLUGIN_GRAPH_PATH
from rag.graph.hybrid_context import (
    DEFAULT_PLUGIN_CHUNKS_PATH,
    build_chunk_lookup,
    format_graph_retrieval_result,
    load_graph_context_chunks,
)


@dataclass(frozen=True)
class GraphRuntimeContext:
    """
    Loaded graph resources used by runtime retrieval.

    Args:
        graph (nx.MultiDiGraph): Plugin relation graph artifact.
        plugin_aliases (dict[str, str]): Query-time plugin alias map.
        chunk_lookup (dict[str, dict]): Source chunk lookup by chunk ID.
    """

    graph: nx.MultiDiGraph
    plugin_aliases: dict[str, str]
    chunk_lookup: dict[str, dict]


_GRAPH_CONTEXT_CACHE: dict[tuple[str, str, str], GraphRuntimeContext] = {}


def build_graph_context_cache_key(
    graph_path: Path,
    plugin_names_path: Path,
    chunks_path: Path,
) -> tuple[str, str, str]:
    """
    Build a cache key for graph runtime artifacts.

    Args:
        graph_path (Path): Path to plugin_graph.json.
        plugin_names_path (Path): Path to plugin_names.json.
        chunks_path (Path): Path to chunks_plugin_docs.json.

    Returns:
        tuple[str, str, str]: String path cache key.
    """
    return (
        str(graph_path.resolve()),
        str(plugin_names_path.resolve()),
        str(chunks_path.resolve()),
    )


def load_graph_runtime_context(
    logger,
    graph_path: Path = DEFAULT_PLUGIN_GRAPH_PATH,
    plugin_names_path: Path = DEFAULT_PLUGIN_NAMES_PATH,
    chunks_path: Path = DEFAULT_PLUGIN_CHUNKS_PATH,
) -> GraphRuntimeContext | None:
    """
    Load graph resources used for runtime GraphRAG context.

    Args:
        logger (logging.Logger): Logger for fallback details.
        graph_path (Path): Path to plugin graph artifact.
        plugin_names_path (Path): Path to plugin names artifact.
        chunks_path (Path): Path to processed plugin chunks artifact.

    Returns:
        GraphRuntimeContext | None: Loaded context when artifacts are available.
    """
    cache_key = build_graph_context_cache_key(
        graph_path,
        plugin_names_path,
        chunks_path,
    )
    if cache_key in _GRAPH_CONTEXT_CACHE:
        return _GRAPH_CONTEXT_CACHE[cache_key]

    try:
        graph = load_plugin_relation_graph(graph_path, logger)
        if graph is None:
            return None

        plugin_aliases = load_query_plugin_aliases(plugin_names_path)
        chunks = load_graph_context_chunks(chunks_path)
        runtime_context = GraphRuntimeContext(
            graph=graph,
            plugin_aliases=plugin_aliases,
            chunk_lookup=build_chunk_lookup(chunks),
        )
        _GRAPH_CONTEXT_CACHE[cache_key] = runtime_context
        return runtime_context
    except (OSError, TypeError, ValueError) as error:
        logger.warning("GraphRAG runtime context unavailable: %s", error)
        return None


def build_graph_runtime_context(
    query: str,
    logger,
    runtime_context: GraphRuntimeContext | None = None,
) -> str:
    """
    Build optional graph retrieval context for a user query.

    Args:
        query (str): User query text.
        logger (logging.Logger): Logger for fallback details.
        runtime_context (GraphRuntimeContext | None): Preloaded graph resources.

    Returns:
        str: Formatted graph context, or an empty string when graph retrieval does not apply.
    """
    graph_context = runtime_context or load_graph_runtime_context(logger)
    if graph_context is None:
        return ""

    result = retrieve_graph_relations(
        query,
        graph_context.plugin_aliases,
        graph_context.graph,
    )
    if result is None:
        return ""

    return format_graph_retrieval_result(
        result,
        chunk_lookup=graph_context.chunk_lookup,
    )
