"""Save and load GraphRAG NetworkX graph artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import logging
from typing import Optional, Union

import networkx as nx
from networkx.readwrite import json_graph


GRAPH_STORE_DIR = Path(__file__).resolve().parents[2] / "data" / "graph"
DEFAULT_PLUGIN_GRAPH_PATH = GRAPH_STORE_DIR / "plugin_graph.json"


def save_graph(graph: nx.MultiDiGraph, path: Union[str, Path], logger: logging.Logger) -> None:
    """
    Save a NetworkX MultiDiGraph to node-link JSON.

    Args:
        graph (nx.MultiDiGraph): Graph artifact to serialize.
        path (str | Path): Destination JSON file path.
        logger (logging.Logger): Logger for save status or error messages.
    """
    if not isinstance(graph, nx.MultiDiGraph):
        logger.error("Graph must be a NetworkX MultiDiGraph")
        return

    graph_path = Path(path)

    try:
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_data = json_graph.node_link_data(graph, edges="edges")
        with graph_path.open("w", encoding="utf-8") as graph_file:
            json.dump(graph_data, graph_file, indent=2)
            graph_file.write("\n")
        logger.info("Graph saved to %s", graph_path)
    except (OSError, TypeError, ValueError) as error:
        logger.error("Failed to save graph to %s: %s", graph_path, error)


def load_graph(path: Union[str, Path], logger: logging.Logger) -> Optional[nx.MultiDiGraph]:
    """
    Load a NetworkX MultiDiGraph from node-link JSON.

    Args:
        path (str | Path): Source JSON file path.
        logger (logging.Logger): Logger for load status or error messages.

    Returns:
        Optional[nx.MultiDiGraph]: Loaded graph when parsing succeeds, otherwise
        None.
    """
    graph_path = Path(path)

    try:
        logger.info("Loading graph from %s...", graph_path)
        with graph_path.open(encoding="utf-8") as graph_file:
            graph_data = json.load(graph_file)
        graph = json_graph.node_link_graph(graph_data, edges="edges")

        if not isinstance(graph, nx.MultiDiGraph):
            logger.error("Loaded graph is not a NetworkX MultiDiGraph: %s", graph_path)
            return None

        logger.info("Graph loaded successfully.")
        return graph
    except FileNotFoundError as error:
        logger.error("Graph file not found: %s - %s", graph_path, error)
    except (OSError, json.JSONDecodeError, TypeError, KeyError, ValueError) as error:
        logger.error("Failed to load graph from %s - %s", graph_path, error)
    return None
