"""Build GraphRAG plugin graph artifacts from plugin chunks."""

import argparse
import json
from pathlib import Path
from typing import Any

from rag.graph.entity_normalizer import (
    DEFAULT_PLUGIN_NAMES_PATH,
    build_plugin_aliases,
    load_canonical_plugin_ids,
)
from rag.graph.graph_artifacts import GraphArtifactPaths, write_graph_artifacts
from rag.graph.graph_builder import build_graph_from_chunks
from utils import LoggerFactory


GRAPH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLUGIN_CHUNKS_PATH = GRAPH_ROOT / "data" / "processed" / "chunks_plugin_docs.json"


def load_plugin_chunks(path: Path) -> list[dict]:
    """
    Load plugin chunks from a JSON artifact file.

    Args:
        path (Path): Path to chunks_plugin_docs.json.

    Returns:
        list[dict]: Plugin chunk records.
    """
    with path.open(encoding="utf-8") as chunks_file:
        chunks = json.load(chunks_file)
    return [chunk for chunk in chunks if isinstance(chunk, dict)]


def run_graph_build(
    plugin_names_path: Path,
    chunks_path: Path,
    artifact_paths: GraphArtifactPaths,
    logger,
) -> dict[str, Any]:
    """
    Build graph artifacts from plugin chunks.

    Args:
        plugin_names_path (Path): Path to plugin_names.json.
        chunks_path (Path): Path to chunks_plugin_docs.json.
        artifact_paths (GraphArtifactPaths): Output artifact paths.
        logger (logging.Logger): Logger for build progress and errors.

    Returns:
        dict[str, Any]: Extraction report payload.
    """
    plugin_ids = load_canonical_plugin_ids(plugin_names_path)
    plugin_aliases = build_plugin_aliases(plugin_ids)
    chunks = load_plugin_chunks(chunks_path)

    logger.info("Loaded %d plugin IDs from %s.", len(plugin_ids), plugin_names_path)
    logger.info("Loaded %d plugin chunks from %s.", len(chunks), chunks_path)

    graph, triples = build_graph_from_chunks(chunks, plugin_aliases)
    report = write_graph_artifacts(
        graph,
        triples,
        chunks,
        logger,
        paths=artifact_paths,
    )

    logger.info(
        "Built graph artifacts with %d triples, %d nodes, and %d edges.",
        report["triple_count"],
        report["node_count"],
        report["edge_count"],
    )
    return report


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for graph artifact generation.

    Returns:
        argparse.Namespace: Parsed graph build arguments.
    """
    parser = argparse.ArgumentParser(
        description="Build GraphRAG plugin graph artifacts from plugin chunks."
    )
    parser.add_argument(
        "--plugin-names-path",
        type=Path,
        default=DEFAULT_PLUGIN_NAMES_PATH,
        help="Path to plugin_names.json.",
    )
    parser.add_argument(
        "--chunks-path",
        type=Path,
        default=DEFAULT_PLUGIN_CHUNKS_PATH,
        help="Path to chunks_plugin_docs.json.",
    )
    parser.add_argument(
        "--graph-path",
        type=Path,
        default=GraphArtifactPaths().graph_path,
        help="Destination path for plugin_graph.json.",
    )
    parser.add_argument(
        "--triples-path",
        type=Path,
        default=GraphArtifactPaths().triples_path,
        help="Destination path for triples.jsonl.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=GraphArtifactPaths().report_path,
        help="Destination path for extraction_report.json.",
    )
    return parser.parse_args()


def main() -> None:
    """
    Run the graph artifact build entrypoint.
    """
    args = parse_args()
    logger = LoggerFactory.instance().get_logger("graph-artifacts")

    artifact_paths = GraphArtifactPaths(
        graph_path=args.graph_path,
        triples_path=args.triples_path,
        report_path=args.report_path,
    )

    run_graph_build(
        plugin_names_path=args.plugin_names_path,
        chunks_path=args.chunks_path,
        artifact_paths=artifact_paths,
        logger=logger,
    )


if __name__ == "__main__":
    main()
