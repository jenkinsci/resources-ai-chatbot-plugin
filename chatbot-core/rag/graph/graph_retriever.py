"""GraphRAG graph loading and traversal helpers."""

from pathlib import Path

import networkx as nx

from rag.graph.entity_normalizer import (
    DEFAULT_PLUGIN_NAMES_PATH,
    build_plugin_aliases,
    load_canonical_plugin_ids,
)
from rag.graph.graph_store import DEFAULT_PLUGIN_GRAPH_PATH, load_graph
from rag.graph.models import GraphEntity, GraphEvidence, GraphRelation, GraphRetrievalResult
from rag.graph.query_parser import (
    GraphQueryIntent,
    GraphQueryMatch,
    parse_graph_query,
)
from rag.graph.schema import GraphEntityType


def load_plugin_relation_graph(
    path: Path = DEFAULT_PLUGIN_GRAPH_PATH,
    logger=None,
) -> nx.MultiDiGraph | None:
    """
    Load the plugin relation graph used for query-time traversal.

    Args:
        path (Path): Path to the stored plugin graph artifact.
        logger (logging.Logger): Logger for load status or errors.

    Returns:
        nx.MultiDiGraph | None: Loaded graph artifact when available.
    """
    if logger is None:
        return None
    return load_graph(str(path), logger)


def load_query_plugin_aliases(
    path: Path = DEFAULT_PLUGIN_NAMES_PATH,
) -> dict[str, str]:
    """
    Load plugin aliases used for query-time entity matching.

    Args:
        path (Path): Path to the canonical plugin names JSON file.

    Returns:
        dict[str, str]: Alias map for query entity resolution.
    """
    plugin_ids = load_canonical_plugin_ids(path)
    return build_plugin_aliases(plugin_ids)


def build_graph_relation(
    graph: nx.MultiDiGraph,
    source_id: str,
    target_id: str,
    edge_data: dict,
) -> GraphRelation:
    """
    Build a graph relation model from a graph edge payload.

    Args:
        graph (nx.MultiDiGraph): Loaded plugin relation graph.
        source_id (str): Source node ID.
        target_id (str): Target node ID.
        edge_data (dict): Edge attribute payload from the graph.

    Returns:
        GraphRelation: Structured graph relation model.
    """
    source_node = graph.nodes[source_id]
    target_node = graph.nodes[target_id]

    return GraphRelation(
        source=GraphEntity(
            name=source_node.get("name", source_id),
            entity_type=source_node.get("entity_type", GraphEntityType.PLUGIN.value),
            entity_id=source_id,
        ),
        relation=edge_data["relation"],
        target=GraphEntity(
            name=target_node.get("name", target_id),
            entity_type=target_node.get("entity_type", GraphEntityType.PLUGIN.value),
            entity_id=target_id,
        ),
        evidence=GraphEvidence(
            source_chunk_id=edge_data["source_chunk_id"],
            source_title=edge_data["source_title"],
            source_data_source=edge_data["source_data_source"],
            evidence=edge_data["evidence"],
        ),
        confidence=edge_data["confidence"],
    )


def iter_relation_edges(
    graph: nx.MultiDiGraph,
    node_id: str,
    intent: GraphQueryIntent,
) -> list[tuple[str, str, dict]]:
    """
    Collect matching graph edges for one node and relation intent.

    Args:
        graph (nx.MultiDiGraph): Loaded plugin relation graph.
        node_id (str): Canonical plugin node ID.
        intent (GraphQueryIntent): Parsed relation intent.

    Returns:
        list[tuple[str, str, dict]]: Matching source, target, and edge payload rows.
    """
    matching_edges = []
    edge_iterators = []

    if intent.direction == "outgoing":
        edge_iterators.append(graph.out_edges(node_id, keys=True, data=True))
    elif intent.direction == "incoming":
        edge_iterators.append(graph.in_edges(node_id, keys=True, data=True))
    else:
        edge_iterators.append(graph.out_edges(node_id, keys=True, data=True))
        edge_iterators.append(graph.in_edges(node_id, keys=True, data=True))

    for edge_iterator in edge_iterators:
        for source_id, target_id, _edge_key, edge_data in edge_iterator:
            if edge_data.get("relation") not in intent.relation_types:
                continue
            matching_edges.append((source_id, target_id, edge_data))

    return matching_edges


def collect_graph_relations(
    graph: nx.MultiDiGraph,
    query_match: GraphQueryMatch,
) -> tuple[GraphRelation, ...]:
    """
    Traverse the graph for a parsed query and collect matching relations.

    Args:
        graph (nx.MultiDiGraph): Loaded plugin relation graph.
        query_match (GraphQueryMatch): Parsed graph query state.

    Returns:
        tuple[GraphRelation, ...]: Matching graph relations with evidence.
    """
    frontier = {query_match.matched_entity.entity_id}
    visited_nodes = set(frontier)
    relation_keys = set()
    relations = []

    for _depth in range(query_match.intent.traversal_depth):
        next_frontier = set()

        for node_id in frontier:
            for source_id, target_id, edge_data in iter_relation_edges(
                graph,
                node_id,
                query_match.intent,
            ):
                relation_key = (
                    source_id,
                    target_id,
                    edge_data["relation"],
                    edge_data["source_chunk_id"],
                    edge_data["evidence"],
                )
                if relation_key in relation_keys:
                    continue

                relation_keys.add(relation_key)
                relations.append(
                    build_graph_relation(
                        graph,
                        source_id,
                        target_id,
                        edge_data,
                    )
                )

                if query_match.intent.direction == "incoming":
                    neighbor_id = source_id
                elif query_match.intent.direction == "outgoing":
                    neighbor_id = target_id
                else:
                    neighbor_id = (
                        target_id if source_id == node_id else source_id
                    )

                if neighbor_id not in visited_nodes:
                    visited_nodes.add(neighbor_id)
                    next_frontier.add(neighbor_id)

        frontier = next_frontier
        if not frontier:
            break

    return tuple(relations)


def retrieve_graph_relations(
    query: str,
    plugin_aliases: dict[str, str],
    graph: nx.MultiDiGraph,
) -> GraphRetrievalResult | None:
    """
    Retrieve graph relations for a relational plugin query.

    Args:
        query (str): User query text.
        plugin_aliases (dict[str, str]): Alias map built from canonical plugin IDs.
        graph (nx.MultiDiGraph): Loaded plugin relation graph.

    Returns:
        GraphRetrievalResult | None: Structured graph retrieval output when matched.
    """
    query_match = parse_graph_query(query, plugin_aliases)
    if not query_match:
        return None

    if query_match.matched_entity.entity_id not in graph:
        return None

    return GraphRetrievalResult(
        query_entity=query_match.query_entity,
        matched_entity_id=query_match.matched_entity.entity_id,
        relations=collect_graph_relations(graph, query_match),
        traversal_depth=query_match.intent.traversal_depth,
    )
