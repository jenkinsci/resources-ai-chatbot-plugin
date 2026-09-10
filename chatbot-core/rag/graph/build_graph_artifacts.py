"""Build GraphRAG plugin graph artifacts from plugin chunks."""

import argparse
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import networkx as nx

from rag.graph.graph_artifacts import GraphArtifactPaths, write_graph_artifacts
from rag.graph.graph_builder import build_graph, build_graph_from_chunks
from rag.graph.json_loader import load_json_list
from rag.graph.models import GraphEntity, GraphEvidence, Triple
from rag.graph.schema import GraphEntityType, GraphRelationType
from rag.graph.triple_extractor import deduplicate_triples
from utils import LoggerFactory


GRAPH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLUGIN_NAMES_PATH = GRAPH_ROOT / "data" / "raw" / "plugin_names.json"
DEFAULT_PLUGIN_CHUNKS_PATH = GRAPH_ROOT / "data" / "processed" / "chunks_plugin_docs.json"
DEFAULT_UPDATE_CENTER_PATH = GRAPH_ROOT / "data" / "raw" / "update-center.actual.json"
DEFAULT_UPDATE_CENTER_URL = "https://updates.jenkins.io/update-center.actual.json"
UPDATE_CENTER_DATA_SOURCE = "jenkins_update_center"
DEFAULT_GRAPH_REFRESH_INTERVAL_SECONDS = 24 * 60 * 60


def load_plugin_ids(path: Path) -> list[str]:
    """
    Load canonical plugin IDs from plugin_names.json.

    Args:
        path (Path): Path to the JSON array of plugin IDs.

    Returns:
        list[str]: Canonical plugin IDs in file order.

    Raises:
        ValueError: If the JSON root or an ID is invalid.
    """
    records = load_json_list(path)
    if any(not isinstance(record, str) or not record.strip() for record in records):
        raise ValueError(f"Plugin names JSON contains an invalid plugin ID: {path}")
    return [record for record in records if isinstance(record, str)]


def is_valid_plugin_chunk(chunk: object) -> bool:
    """
    Check the required shape of one plugin documentation chunk.

    Args:
        chunk (object): JSON value to validate.

    Returns:
        bool: True when the chunk contains required string fields.
    """
    if not isinstance(chunk, dict):
        return False

    metadata = chunk.get("metadata")
    return (
        isinstance(chunk.get("id"), str)
        and bool(chunk["id"].strip())
        and isinstance(chunk.get("chunk_text"), str)
        and bool(chunk["chunk_text"].strip())
        and isinstance(metadata, dict)
        and isinstance(metadata.get("title"), str)
        and bool(metadata["title"].strip())
        and isinstance(metadata.get("data_source"), str)
        and bool(metadata["data_source"].strip())
    )


def load_plugin_chunks(path: Path) -> list[dict]:
    """
    Load plugin chunks from a JSON artifact file.

    Args:
        path (Path): Path to chunks_plugin_docs.json.

    Returns:
        list[dict]: Plugin chunk records.
    """
    chunks = load_json_list(path)
    return [chunk for chunk in chunks if is_valid_plugin_chunk(chunk)]


def _validate_update_center_plugins(snapshot: object) -> dict[str, Any]:
    """Validate and return the plugin map from an Update Center snapshot."""
    plugins = snapshot.get("plugins") if isinstance(snapshot, dict) else None
    if not isinstance(plugins, dict):
        raise ValueError("Update Center snapshot must contain a plugins map")

    for source_id, plugin in plugins.items():
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("Update Center plugin IDs must be non-empty strings")
        if not isinstance(plugin, dict):
            raise ValueError(f"Invalid plugin record: {source_id}")

        dependencies = plugin.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise ValueError(f"Invalid dependencies for plugin: {source_id}")

        for dependency in dependencies:
            if not isinstance(dependency, dict):
                raise ValueError(f"Invalid dependency for plugin: {source_id}")
            target_id = dependency.get("name")
            if not isinstance(target_id, str) or not target_id.strip():
                raise ValueError(f"Dependency has no plugin name: {source_id}")
            optional = dependency.get("optional", False)
            if not isinstance(optional, bool):
                raise ValueError(f"Dependency optionality is invalid: {source_id}")
            version = dependency.get("version")
            if version is not None and not isinstance(version, str):
                raise ValueError(f"Dependency version is invalid: {source_id}")

    return plugins


def _load_update_center_plugins(path: Path) -> dict[str, Any]:
    """Load and validate the plugin map from a local snapshot."""
    with path.open(encoding="utf-8") as json_file:
        snapshot = json.load(json_file)

    return _validate_update_center_plugins(snapshot)


def fetch_update_center_snapshot(
    destination: Path,
    url: str = DEFAULT_UPDATE_CENTER_URL,
    timeout: int = 30,
) -> str:
    """
    Fetch, validate, and atomically replace a local Update Center snapshot.

    Args:
        destination (Path): Local path to replace with the validated snapshot.
        url (str): Update Center endpoint to fetch.
        timeout (int): Network timeout in seconds.

    Returns:
        str: SHA-256 checksum of the downloaded snapshot.

    Raises:
        ValueError: If the downloaded JSON is not a valid snapshot.
    """
    with urlopen(url, timeout=timeout) as response:
        snapshot_bytes = response.read()

    snapshot = json.loads(snapshot_bytes)
    _validate_update_center_plugins(snapshot)

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as temporary_file:
            temporary_file.write(snapshot_bytes)
            temporary_path = temporary_file.name
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None and os.path.exists(temporary_path):
            os.unlink(temporary_path)

    return hashlib.sha256(snapshot_bytes).hexdigest()


def _build_update_center_triple(
    source_id: str,
    dependency: dict[str, Any],
) -> Triple:
    """Convert one validated Update Center dependency into a triple."""
    target_id = dependency["name"]
    optional = dependency.get("optional", False)
    relation = (
        GraphRelationType.OPTIONAL_DEPENDS_ON.value
        if optional
        else GraphRelationType.DEPENDS_ON.value
    )
    version = dependency.get("version")
    version_text = f" Minimum version: {version}." if version else ""
    source = GraphEntity(
        name=source_id,
        entity_type=GraphEntityType.PLUGIN.value,
        entity_id=source_id,
    )
    target = GraphEntity(
        name=target_id,
        entity_type=GraphEntityType.PLUGIN.value,
        entity_id=target_id,
    )

    return Triple(
        source=source,
        relation=relation,
        target=target,
        evidence=GraphEvidence(
            source_chunk_id=f"update-center:{source_id}",
            source_title=source_id,
            source_data_source=UPDATE_CENTER_DATA_SOURCE,
            evidence=(
                f"Update Center declares {target_id} as a "
                f"{'optional' if optional else 'required'} dependency "
                f"of {source_id}.{version_text}"
            ),
        ),
    )


def load_update_center_triples(path: Path) -> list[Triple]:
    """
    Load direct dependency triples from a local Update Center snapshot.

    Args:
        path (Path): Local update-center.actual.json path.

    Returns:
        list[Triple]: Required and optional dependency triples.
    """
    plugins = _load_update_center_plugins(path)
    return [
        _build_update_center_triple(source_id, dependency)
        for source_id, plugin in plugins.items()
        for dependency in plugin.get("dependencies", [])
    ]


def get_update_center_dependencies(
    path: Path,
    plugin_id: str,
) -> list[Triple]:
    """
    Return direct Update Center dependencies for one canonical plugin ID.

    Args:
        path (Path): Local update-center.actual.json path.
        plugin_id (str): Canonical plugin ID to look up.

    Returns:
        list[Triple]: Matching required and optional dependency triples.

    Raises:
        ValueError: If the plugin ID is empty.
    """
    if not plugin_id.strip():
        raise ValueError("Plugin ID must not be empty")

    return [
        triple
        for triple in load_update_center_triples(path)
        if triple.source.entity_id == plugin_id
    ]


def _add_plugin_nodes(graph: nx.MultiDiGraph, plugin_ids: list[str]) -> None:
    """Add known plugin IDs that may not participate in a relation."""
    graph.add_nodes_from(
        (
            plugin_id,
            {
                "name": plugin_id,
                "entity_type": GraphEntityType.PLUGIN.value,
            },
        )
        for plugin_id in plugin_ids
    )


def run_graph_build(
    plugin_names_path: Path,
    chunks_path: Path,
    artifact_paths: GraphArtifactPaths,
    logger,
    update_center_path: Path | None = None,
) -> dict[str, Any]:
    """
    Build graph artifacts from plugin chunks.

    Args:
        plugin_names_path (Path): Path to plugin_names.json.
        chunks_path (Path): Path to chunks_plugin_docs.json.
        artifact_paths (GraphArtifactPaths): Output artifact paths.
        logger (logging.Logger): Logger for build progress and errors.
        update_center_path (Path | None): Optional local Update Center snapshot.

    Returns:
        dict[str, Any]: Extraction report payload.
    """
    plugin_ids = load_plugin_ids(plugin_names_path)
    chunks = load_plugin_chunks(chunks_path)

    logger.info("Loaded %d plugin IDs from %s.", len(plugin_ids), plugin_names_path)
    logger.info("Loaded %d plugin chunks from %s.", len(chunks), chunks_path)

    _, documentation_triples = build_graph_from_chunks(chunks, plugin_ids)
    known_plugin_ids = set(plugin_ids)
    update_center_triples: list[Triple] = []
    if update_center_path is not None:
        update_center_plugins = _load_update_center_plugins(update_center_path)
        known_plugin_ids.update(update_center_plugins)
        update_center_triples = [
            _build_update_center_triple(source_id, dependency)
            for source_id, plugin in update_center_plugins.items()
            for dependency in plugin.get("dependencies", [])
        ]

    update_center_keys = {
        (
            triple.source.entity_id,
            triple.relation,
            triple.target.entity_id,
        )
        for triple in update_center_triples
    }
    triples = [
        triple
        for triple in documentation_triples
        if (
            triple.source.entity_id,
            triple.relation,
            triple.target.entity_id,
        )
        not in update_center_keys
    ]
    triples.extend(update_center_triples)
    triples = deduplicate_triples(triples)
    graph = build_graph(triples)
    _add_plugin_nodes(graph, sorted(known_plugin_ids))

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


def refresh_graph_if_stale(
    logger,
    artifact_paths: GraphArtifactPaths = GraphArtifactPaths(),
    max_age_seconds: int = DEFAULT_GRAPH_REFRESH_INTERVAL_SECONDS,
) -> None:
    """
    Fetch Update Center data and rebuild graph artifacts when the graph is stale.

    Args:
        logger: Logger for refresh status and failures.
        artifact_paths: Destination paths for graph artifacts.
        max_age_seconds: Maximum allowed age of the graph artifact.

    """
    graph_path = artifact_paths.graph_path
    if (
        graph_path.exists()
        and time.time() - graph_path.stat().st_mtime < max_age_seconds
    ):
        logger.info("Graph is up to date, no need to refresh.")
        return

    started_at = time.perf_counter()
    try:
        logger.info("Graph outdated, refreshing.")
        fetch_update_center_snapshot(DEFAULT_UPDATE_CENTER_PATH)
        run_graph_build(
            plugin_names_path=DEFAULT_PLUGIN_NAMES_PATH,
            chunks_path=DEFAULT_PLUGIN_CHUNKS_PATH,
            artifact_paths=artifact_paths,
            logger=logger,
            update_center_path=DEFAULT_UPDATE_CENTER_PATH,
        )
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        logger.warning("Graph refresh failed; keeping existing artifacts: %s", error)
        return

    logger.info("Graph refresh completed in %.2fs.", time.perf_counter() - started_at)


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
        "--update-center-path",
        type=Path,
        help="Optional local update-center.actual.json to merge into the graph.",
    )
    parser.add_argument(
        "--refresh-update-center",
        action="store_true",
        help="Fetch and validate a fresh Update Center snapshot before building.",
    )
    parser.add_argument(
        "--update-center-url",
        default=DEFAULT_UPDATE_CENTER_URL,
        help="Update Center URL used with --refresh-update-center.",
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

    update_center_path = args.update_center_path
    if args.refresh_update_center:
        update_center_path = update_center_path or DEFAULT_UPDATE_CENTER_PATH
        checksum = fetch_update_center_snapshot(
            update_center_path,
            url=args.update_center_url,
        )
        logger.info(
            "Fetched Update Center snapshot to %s (sha256=%s).",
            update_center_path,
            checksum,
        )

    run_graph_build(
        plugin_names_path=args.plugin_names_path,
        chunks_path=args.chunks_path,
        artifact_paths=artifact_paths,
        logger=logger,
        update_center_path=update_center_path,
    )


if __name__ == "__main__":
    main()
