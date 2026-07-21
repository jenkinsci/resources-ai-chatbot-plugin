"""Unit tests for GraphRAG graph store."""

from unittest.mock import Mock

import networkx as nx

from rag.graph.graph_store import load_graph, save_graph
from rag.graph.schema import GraphRelationType


def build_test_graph():
    """
    Build a MultiDiGraph with two parallel plugin relation edges.

    Returns:
        nx.MultiDiGraph: Test graph with node attributes and edge evidence.
    """
    graph = nx.MultiDiGraph()
    graph.add_node("blueocean", name="Blue Ocean", entity_type="Plugin")
    graph.add_node("git", name="Git plugin", entity_type="Plugin")
    graph.add_edge(
        "blueocean",
        "git",
        relation=GraphRelationType.DEPENDS_ON.value,
        source_chunk_id="chunk-1",
        source_title="Blue Ocean",
        source_data_source="plugins",
        evidence="Blue Ocean depends on Git.",
        confidence=0.9,
    )
    graph.add_edge(
        "blueocean",
        "git",
        relation=GraphRelationType.OPTIONAL_DEPENDS_ON.value,
        source_chunk_id="chunk-2",
        source_title="Blue Ocean",
        source_data_source="plugins",
        evidence="Git is optional in this setup.",
        confidence=0.7,
    )
    return graph


def test_save_and_load_graph_preserves_multidigraph(tmp_path):
    """
    Verify saved graph JSON loads back as a MultiDiGraph with node metadata.
    """
    mock_logger = Mock()
    path = tmp_path / "plugin_graph.json"

    save_graph(build_test_graph(), str(path), mock_logger)
    result = load_graph(str(path), mock_logger)

    assert isinstance(result, nx.MultiDiGraph)
    assert result.number_of_nodes() == 2
    assert result.nodes["blueocean"]["name"] == "Blue Ocean"


def test_save_and_load_graph_preserves_parallel_edges(tmp_path):
    """
    Verify parallel relation edges survive the node-link JSON round trip.
    """
    mock_logger = Mock()
    path = tmp_path / "plugin_graph.json"

    save_graph(build_test_graph(), str(path), mock_logger)
    result = load_graph(str(path), mock_logger)

    assert result.number_of_edges("blueocean", "git") == 2
    edge_data = result.get_edge_data("blueocean", "git")
    relations = sorted(edge["relation"] for edge in edge_data.values())
    assert relations == [
        GraphRelationType.DEPENDS_ON.value,
        GraphRelationType.OPTIONAL_DEPENDS_ON.value,
    ]
    assert edge_data[0]["source_chunk_id"] == "chunk-1"
    assert edge_data[1]["source_chunk_id"] == "chunk-2"


def test_save_graph_rejects_plain_digraph(tmp_path):
    """
    Verify the store rejects plain DiGraph instances.
    """
    mock_logger = Mock()
    path = tmp_path / "plugin_graph.json"

    save_graph(nx.DiGraph(), str(path), mock_logger)

    assert not path.exists()
    mock_logger.error.assert_called_once_with("Graph must be a NetworkX MultiDiGraph")


def test_load_graph_missing_file_returns_none(tmp_path):
    """
    Verify loading a missing graph file returns None and logs an error.
    """
    mock_logger = Mock()
    path = tmp_path / "missing_graph.json"

    result = load_graph(str(path), mock_logger)

    assert result is None
    mock_logger.error.assert_called_once()
    assert "Graph file not found" in mock_logger.error.call_args[0][0]


def test_load_graph_corrupt_json_returns_none(tmp_path):
    """
    Verify loading malformed graph JSON returns None and logs an error.
    """
    mock_logger = Mock()
    path = tmp_path / "plugin_graph.json"
    path.write_text("not json", encoding="utf-8")

    result = load_graph(str(path), mock_logger)

    assert result is None
    mock_logger.error.assert_called_once()
    assert "Failed to load graph" in mock_logger.error.call_args[0][0]
