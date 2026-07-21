"""Unit tests for GraphRAG artifact writing."""

import json
from unittest.mock import Mock

from rag.graph.graph_artifacts import (
    GraphArtifactPaths,
    build_extraction_report,
    triple_to_record,
    write_graph_artifacts,
)
from rag.graph.graph_builder import build_graph
from rag.graph.graph_store import load_graph
from rag.graph.models import GraphEntity, GraphEvidence, Triple
from rag.graph.schema import GraphEntityType, GraphRelationType


def build_test_triple() -> Triple:
    """
    Build a graph triple for artifact tests.

    Returns:
        Triple: Test dependency triple.
    """
    return Triple(
        source=GraphEntity(
            name="source-plugin",
            entity_type=GraphEntityType.PLUGIN.value,
            entity_id="source-plugin",
        ),
        relation=GraphRelationType.DEPENDS_ON.value,
        target=GraphEntity(
            name="target-plugin",
            entity_type=GraphEntityType.PLUGIN.value,
            entity_id="target-plugin",
        ),
        evidence=GraphEvidence(
            source_chunk_id="chunk-1",
            source_title="source-plugin",
            source_data_source="jenkins_plugins_documentation",
            evidence="Source depends on target.",
        ),
        confidence=0.9,
    )


def test_triple_to_record_preserves_nested_shape():
    """
    Verify triple serialization keeps source, target, and evidence payloads.
    """
    record = triple_to_record(build_test_triple())

    assert record["source"]["entity_id"] == "source-plugin"
    assert record["relation"] == GraphRelationType.DEPENDS_ON.value
    assert record["target"]["entity_id"] == "target-plugin"
    assert record["evidence"]["source_chunk_id"] == "chunk-1"


def test_build_extraction_report_counts_graph_and_relations():
    """
    Verify extraction reports include source, graph, and relation counts.
    """
    triples = [build_test_triple()]
    graph = build_graph(triples)
    chunks = [{"id": "chunk-1"}]

    report = build_extraction_report(chunks, triples, graph)

    assert report == {
        "chunk_count": 1,
        "triple_count": 1,
        "node_count": 2,
        "edge_count": 1,
        "relation_counts": {
            GraphRelationType.DEPENDS_ON.value: 1,
        },
    }


def test_write_graph_artifacts_writes_loadable_outputs(tmp_path):
    """
    Verify graph, triples, and report artifacts are written together.
    """
    mock_logger = Mock()
    triples = [build_test_triple()]
    graph = build_graph(triples)
    chunks = [{"id": "chunk-1"}]
    paths = GraphArtifactPaths(
        graph_path=tmp_path / "plugin_graph.json",
        triples_path=tmp_path / "triples.jsonl",
        report_path=tmp_path / "extraction_report.json",
    )

    report = write_graph_artifacts(
        graph,
        triples,
        chunks,
        mock_logger,
        paths=paths,
    )
    loaded_graph = load_graph(str(paths.graph_path), mock_logger)
    triple_lines = paths.triples_path.read_text(encoding="utf-8").splitlines()
    report_payload = json.loads(paths.report_path.read_text(encoding="utf-8"))

    assert report["triple_count"] == 1
    assert loaded_graph.number_of_edges("source-plugin", "target-plugin") == 1
    assert len(triple_lines) == 1
    assert json.loads(triple_lines[0])["evidence"]["evidence"] == (
        "Source depends on target."
    )
    assert report_payload == report
