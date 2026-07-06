"""Unit tests for GraphRAG graph builder."""

import networkx as nx

from rag.graph.graph_builder import build_graph, build_graph_from_chunks
from rag.graph.models import GraphEntity, GraphEvidence, Triple
from rag.graph.schema import GraphEntityType, GraphRelationType


def build_entity(entity_id: str) -> GraphEntity:
    """
    Build a plugin entity for graph builder tests.

    Args:
        entity_id (str): Canonical plugin ID.

    Returns:
        GraphEntity: Test graph entity.
    """
    return GraphEntity(
        name=entity_id,
        entity_type=GraphEntityType.PLUGIN.value,
        entity_id=entity_id,
    )


def build_evidence(chunk_id: str, text: str) -> GraphEvidence:
    """
    Build source evidence for graph builder tests.

    Args:
        chunk_id (str): Source chunk ID.
        text (str): Evidence text.

    Returns:
        GraphEvidence: Test graph evidence.
    """
    return GraphEvidence(
        source_chunk_id=chunk_id,
        source_title="source-plugin",
        source_data_source="jenkins_plugins_documentation",
        evidence=text,
    )


def build_triple(chunk_id: str, evidence: str) -> Triple:
    """
    Build a dependency triple for graph builder tests.

    Args:
        chunk_id (str): Source chunk ID.
        evidence (str): Evidence text.

    Returns:
        Triple: Test dependency triple.
    """
    return Triple(
        source=build_entity("source-plugin"),
        relation=GraphRelationType.DEPENDS_ON.value,
        target=build_entity("target-plugin"),
        evidence=build_evidence(chunk_id, evidence),
        confidence=0.9,
    )


def test_build_graph_returns_multidigraph_with_node_attributes():
    """
    Verify triples are materialized as a NetworkX MultiDiGraph.
    """
    graph = build_graph([build_triple("chunk-1", "Source depends on target.")])

    assert isinstance(graph, nx.MultiDiGraph)
    assert graph.is_directed()
    assert graph.is_multigraph()
    assert graph.nodes["source-plugin"]["entity_type"] == GraphEntityType.PLUGIN.value
    assert graph.nodes["target-plugin"]["name"] == "target-plugin"


def test_build_graph_preserves_parallel_evidence_edges():
    """
    Verify repeated source-target pairs remain separate evidence edges.
    """
    graph = build_graph(
        [
            build_triple("chunk-1", "Source depends on target."),
            build_triple("chunk-2", "Source still depends on target."),
        ]
    )

    assert graph.number_of_edges("source-plugin", "target-plugin") == 2
    edge_data = graph.get_edge_data("source-plugin", "target-plugin")
    chunk_ids = sorted(edge["source_chunk_id"] for edge in edge_data.values())
    evidence_texts = sorted(edge["evidence"] for edge in edge_data.values())

    assert chunk_ids == ["chunk-1", "chunk-2"]
    assert evidence_texts == [
        "Source depends on target.",
        "Source still depends on target.",
    ]


def test_build_graph_from_chunks_extracts_and_materializes_graph():
    """
    Verify chunk extraction and graph materialization work together.
    """
    chunks = [
        {
            "id": "chunk-1",
            "chunk_text": "This plugin depends on Target Plugin.",
            "metadata": {
                "title": "source-plugin",
                "data_source": "jenkins_plugins_documentation",
            },
        }
    ]
    plugin_aliases = {
        "sourceplugin": "source-plugin",
        "targetplugin": "target-plugin",
        "target": "target-plugin",
    }

    graph, triples = build_graph_from_chunks(chunks, plugin_aliases)

    assert len(triples) == 1
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges("source-plugin", "target-plugin") == 1
