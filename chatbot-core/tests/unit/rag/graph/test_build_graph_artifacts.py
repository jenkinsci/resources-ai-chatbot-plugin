"""Unit tests for GraphRAG graph build entrypoint."""

import json
from unittest.mock import Mock

from rag.graph.build_graph_artifacts import load_plugin_chunks, run_graph_build
from rag.graph.graph_artifacts import GraphArtifactPaths
from rag.graph.graph_store import load_graph


def build_chunk(title: str, text: str) -> dict:
    """
    Build a plugin chunk for graph build tests.

    Args:
        title (str): Source plugin title.
        text (str): Chunk text.

    Returns:
        dict: Chunk payload matching chunks_plugin_docs.json.
    """
    return {
        "id": "chunk-1",
        "chunk_text": text,
        "metadata": {
            "title": title,
            "data_source": "jenkins_plugins_documentation",
        },
    }


def test_load_plugin_chunks_keeps_dict_records(tmp_path):
    """
    Verify plugin chunk loading skips malformed non-dict records.
    """
    chunks_path = tmp_path / "chunks_plugin_docs.json"
    chunks_path.write_text(
        json.dumps([{"id": "chunk-1"}, "bad-record", 123]),
        encoding="utf-8",
    )

    chunks = load_plugin_chunks(chunks_path)

    assert chunks == [{"id": "chunk-1"}]


def test_run_graph_build_writes_artifacts_from_fake_inputs(tmp_path):
    """
    Verify the build orchestration works with small fake input files.
    """
    mock_logger = Mock()
    plugin_names_path = tmp_path / "plugin_names.json"
    chunks_path = tmp_path / "chunks_plugin_docs.json"
    paths = GraphArtifactPaths(
        graph_path=tmp_path / "graph" / "plugin_graph.json",
        triples_path=tmp_path / "graph" / "triples.jsonl",
        report_path=tmp_path / "graph" / "extraction_report.json",
    )
    plugin_names_path.write_text(
        json.dumps(["source-plugin", "target-plugin"]),
        encoding="utf-8",
    )
    chunks_path.write_text(
        json.dumps(
            [
                build_chunk(
                    "source-plugin",
                    "This plugin depends on Target Plugin.",
                )
            ]
        ),
        encoding="utf-8",
    )

    report = run_graph_build(
        plugin_names_path=plugin_names_path,
        chunks_path=chunks_path,
        artifact_paths=paths,
        logger=mock_logger,
    )
    graph = load_graph(str(paths.graph_path), mock_logger)

    assert report["chunk_count"] == 1
    assert report["triple_count"] == 1
    assert report["node_count"] == 2
    assert report["edge_count"] == 1
    assert paths.triples_path.exists()
    assert paths.report_path.exists()
    assert graph.number_of_edges("source-plugin", "target-plugin") == 1
