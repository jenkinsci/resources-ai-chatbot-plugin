"""Write GraphRAG graph extraction artifacts."""

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

from rag.graph.graph_store import DEFAULT_PLUGIN_GRAPH_PATH, GRAPH_STORE_DIR, save_graph
from rag.graph.models import Triple


DEFAULT_TRIPLES_PATH = GRAPH_STORE_DIR / "triples.jsonl"
DEFAULT_EXTRACTION_REPORT_PATH = GRAPH_STORE_DIR / "extraction_report.json"
GRAPH_SOURCE = "plugin_documentation"
COMBINED_GRAPH_SOURCE = "plugin_documentation_and_jenkins_update_center"
DEPENDENCY_METADATA_SOURCE = "not_used"


@dataclass(frozen=True)
class GraphArtifactPaths:
    """
    Hold output paths for graph extraction artifacts.

    Args:
        graph_path (Path): Destination graph JSON path.
        triples_path (Path): Destination triples JSONL path.
        report_path (Path): Destination extraction report JSON path.
    """

    graph_path: Path = DEFAULT_PLUGIN_GRAPH_PATH
    triples_path: Path = DEFAULT_TRIPLES_PATH
    report_path: Path = DEFAULT_EXTRACTION_REPORT_PATH


@dataclass(frozen=True)
class GraphArtifactConfig:
    """
    Configure graph artifact destinations and report metadata.

    Args:
        paths (GraphArtifactPaths): Destination artifact paths.
        graph_source (str): Graph relationship sources used for the build.
        dependency_metadata_source (str): Dependency metadata source.
    """

    paths: GraphArtifactPaths = field(default_factory=GraphArtifactPaths)
    graph_source: str = GRAPH_SOURCE
    dependency_metadata_source: str = DEPENDENCY_METADATA_SOURCE


def triple_to_record(triple: Triple) -> dict[str, Any]:
    """
    Convert a Triple model to a JSON-ready record.

    Args:
        triple (Triple): Extracted graph relation triple.

    Returns:
        dict[str, Any]: JSON-serializable triple record.
    """
    return asdict(triple)


def write_jsonl(
    path: Path,
    records: list[dict[str, Any]],
    logger,
) -> None:
    """
    Write records to a JSONL artifact file.

    Args:
        path (Path): Destination JSONL path.
        records (list[dict[str, Any]]): Records to write.
        logger (logging.Logger): Logger for write status or errors.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as output_file:
            for record in records:
                output_file.write(json.dumps(record, ensure_ascii=False))
                output_file.write("\n")
        logger.info("Wrote %d records to %s", len(records), path)
    except (OSError, TypeError, ValueError) as error:
        logger.error("Failed to write JSONL artifact to %s: %s", path, error)


def write_json(
    path: Path,
    data: dict[str, Any],
    logger,
) -> None:
    """
    Write a JSON artifact file.

    Args:
        path (Path): Destination JSON path.
        data (dict[str, Any]): JSON-serializable payload to write.
        logger (logging.Logger): Logger for write status or errors.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("Wrote JSON artifact to %s", path)
    except (OSError, TypeError, ValueError) as error:
        logger.error("Failed to write JSON artifact to %s: %s", path, error)


def build_extraction_report(
    chunks: list[dict],
    triples: list[Triple],
    graph: nx.MultiDiGraph,
    graph_source: str = GRAPH_SOURCE,
    dependency_metadata_source: str = DEPENDENCY_METADATA_SOURCE,
) -> dict[str, Any]:
    """
    Build summary counters for graph extraction artifacts.

    Args:
        chunks (list[dict]): Source plugin chunks used for extraction.
        triples (list[Triple]): Extracted triples.
        graph (nx.MultiDiGraph): Built graph artifact.
        graph_source (str): Graph relationship sources used for the build.
        dependency_metadata_source (str): Dependency metadata source used for the build.

    Returns:
        dict[str, Any]: Extraction summary counters.
    """
    relation_counts = Counter(triple.relation for triple in triples)

    return {
        "graph_source": graph_source,
        "dependency_metadata": dependency_metadata_source,
        "chunk_count": len(chunks),
        "triple_count": len(triples),
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "relation_counts": dict(sorted(relation_counts.items())),
    }


def write_triples(
    triples: list[Triple],
    path: Path,
    logger,
) -> None:
    """
    Write extracted triples to a JSONL artifact.

    Args:
        triples (list[Triple]): Extracted triples to serialize.
        path (Path): Destination JSONL path.
        logger (logging.Logger): Logger for write status or errors.
    """
    records = [triple_to_record(triple) for triple in triples]
    write_jsonl(path, records, logger)


def write_graph_artifacts(
    graph: nx.MultiDiGraph,
    triples: list[Triple],
    chunks: list[dict],
    logger,
    config: GraphArtifactConfig = GraphArtifactConfig(),
) -> dict[str, Any]:
    """
    Write graph, triples, and extraction report artifacts.

    Args:
        graph (nx.MultiDiGraph): Built plugin relation graph.
        triples (list[Triple]): Extracted triples used to build the graph.
        chunks (list[dict]): Source chunks used for extraction.
        logger (logging.Logger): Logger for artifact status or errors.
        config (GraphArtifactConfig): Artifact paths and report metadata.

    Returns:
        dict[str, Any]: Extraction report payload.
    """
    report = build_extraction_report(
        chunks,
        triples,
        graph,
        graph_source=config.graph_source,
        dependency_metadata_source=config.dependency_metadata_source,
    )

    save_graph(graph, str(config.paths.graph_path), logger)
    write_triples(triples, config.paths.triples_path, logger)
    write_json(config.paths.report_path, report, logger)

    return report
