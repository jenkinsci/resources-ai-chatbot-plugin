"""Unit tests for runtime GraphRAG context assembly."""

from unittest.mock import Mock

import networkx as nx

from rag.graph.runtime_context import GraphRuntimeContext, build_graph_runtime_context
from rag.graph.schema import GraphEntityType, GraphRelationType
from rag.graph.triple_extractor import build_plugin_lookup


def build_runtime_context() -> GraphRuntimeContext:
    """Build a minimal loaded runtime context for integration tests."""
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(
        (
            ("blueocean", {"name": "Blue Ocean", "entity_type": GraphEntityType.PLUGIN.value}),
            ("git", {"name": "Git", "entity_type": GraphEntityType.PLUGIN.value}),
        )
    )
    graph.add_edge(
        "blueocean",
        "git",
        relation=GraphRelationType.DEPENDS_ON.value,
        source_chunk_id="chunk-blue-git",
        source_title="Blue Ocean",
        source_data_source="jenkins_plugins_documentation",
        evidence="Blue Ocean depends on Git.",
    )
    return GraphRuntimeContext(
        graph=graph,
        plugin_lookup=build_plugin_lookup(("blueocean", "git")),
        chunk_lookup={
            "chunk-blue-git": {
                "id": "chunk-blue-git",
                "chunk_text": "Blue Ocean depends on Git. Extra setup detail.",
            }
        },
    )


def test_build_graph_runtime_context_formats_retrieved_relations():
    """Append graph relation, evidence, and source chunk to prompt context."""
    result = build_graph_runtime_context(
        "What does Blue Ocean depend on?",
        Mock(),
        runtime_context=build_runtime_context(),
    )

    assert "Blue Ocean DEPENDS_ON Git." in result
    assert "Evidence: Blue Ocean depends on Git." in result
    assert "Context:\nBlue Ocean depends on Git. Extra setup detail." in result


def test_build_graph_runtime_context_falls_back_for_non_graph_query():
    """Return empty context when the parser abstains from a normal query."""
    result = build_graph_runtime_context(
        "How do I configure Blue Ocean?",
        Mock(),
        runtime_context=build_runtime_context(),
    )

    assert result == ""


def test_build_graph_runtime_context_falls_back_for_negated_query():
    """Return empty context when negation makes graph traversal unsafe."""
    result = build_graph_runtime_context(
        "Does Blue Ocean not depend on Git?",
        Mock(),
        runtime_context=build_runtime_context(),
    )

    assert result == ""
