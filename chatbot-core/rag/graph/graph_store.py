"""GraphRAG graph store helpers."""

import json
import os

import networkx as nx
from networkx.readwrite import json_graph


GRAPH_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "graph")
DEFAULT_PLUGIN_GRAPH_PATH = os.path.join(GRAPH_STORE_DIR, "plugin_graph.json")


def save_graph(graph: nx.MultiDiGraph, path: str, logger) -> None:
    """
    Save a MultiDiGraph to JSON.

    Args:
        graph (nx.MultiDiGraph): Graph to save.
        path (str): File path to save the graph.
        logger (logging.Logger): Logger for status or error messages.
    """
    if not isinstance(graph, nx.MultiDiGraph):
        logger.error("Graph must be a NetworkX MultiDiGraph")
        return

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        graph_data = json_graph.node_link_data(graph, edges="edges")
        with open(path, "w", encoding="utf-8") as graph_file:
            json.dump(graph_data, graph_file, indent=2)
            graph_file.write("\n")
        logger.info("Graph saved to %s", path)
    except (OSError, TypeError, ValueError) as error:
        logger.error("Failed to save graph to %s: %s", path, error)


def load_graph(path: str, logger) -> nx.MultiDiGraph | None:
    """
    Load a MultiDiGraph from JSON.

    Args:
        path (str): File path to load the graph from.
        logger (logging.Logger): Logger for status or error messages.

    Returns:
        nx.MultiDiGraph | None: Loaded graph, or None if loading fails.
    """
    try:
        logger.info("Loading graph from %s...", path)
        with open(path, encoding="utf-8") as graph_file:
            graph_data = json.load(graph_file)
        graph = json_graph.node_link_graph(graph_data, edges="edges")

        if not isinstance(graph, nx.MultiDiGraph):
            logger.error("Loaded graph is not a NetworkX MultiDiGraph: %s", path)
            return None

        logger.info("Graph loaded successfully.")
        return graph
    except FileNotFoundError as error:
        logger.error("Graph file not found: %s - %s", path, error)
    except (OSError, json.JSONDecodeError, TypeError, KeyError, ValueError) as error:
        logger.error("Failed to load graph from %s - %s", path, error)
    return None
