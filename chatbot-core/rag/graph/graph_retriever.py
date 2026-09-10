"""GraphRAG graph loading and traversal helpers."""

from pathlib import Path

import networkx as nx

from rag.graph.build_graph_artifacts import (
    DEFAULT_PLUGIN_NAMES_PATH,
    load_plugin_ids,
)
from rag.graph.graph_store import DEFAULT_PLUGIN_GRAPH_PATH, load_graph
from rag.graph.models import GraphEntity, GraphEvidence, GraphRelation, GraphRetrievalResult
from rag.graph.query_parser import (
    GraphQueryPlan,
    parse_graph_query,
)
from rag.graph.schema import (
    REQUIRED_EVIDENCE_FIELDS,
    GraphEntityType,
    GraphRelationType,
    has_required_evidence_fields,
)
from rag.graph.triple_extractor import PluginLookup, build_plugin_lookup


def _has_valid_graph_edge_payload(edge_data: dict) -> bool:
    """
    Check whether an edge contains documentation evidence fields.

    Args:
        edge_data (dict): Edge attributes loaded from the graph artifact.

    Returns:
        bool: True when all required fields contain non-empty strings.
    """
    return has_required_evidence_fields(edge_data) and all(
        isinstance(edge_data.get(field_name), str)
        and bool(edge_data[field_name].strip())
        for field_name in REQUIRED_EVIDENCE_FIELDS
    )


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

    graph = load_graph(str(path), logger)
    if graph is None:
        return None

    invalid_edge_count = sum(
        not _has_valid_graph_edge_payload(edge_data)
        for _source_id, _target_id, edge_data in graph.edges(data=True)
    )
    if invalid_edge_count:
        logger.warning(
            "Plugin graph contains %d edge(s) without documentation evidence. "
            "Ignoring the graph artifact.",
            invalid_edge_count,
        )
        return None

    return graph


def load_query_plugin_lookup(
    path: Path = DEFAULT_PLUGIN_NAMES_PATH,
) -> PluginLookup:
    """
    Load the canonical plugin lookup used for query-time entity matching.

    Args:
        path (Path): Path to the canonical plugin names JSON file.

    Returns:
        PluginLookup: Canonical forms mapped to plugin IDs.
    """
    return build_plugin_lookup(load_plugin_ids(path))


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
    )


def iter_relation_edges(
    graph: nx.MultiDiGraph,
    node_id: str,
    plan: GraphQueryPlan,
) -> list[tuple[str, str, dict]]:
    """
    Collect matching graph edges for one node and query plan.

    Args:
        graph (nx.MultiDiGraph): Loaded plugin relation graph.
        node_id (str): Canonical plugin node ID.
        plan (GraphQueryPlan): Position-based graph query plan.

    Returns:
        list[tuple[str, str, dict]]: Matching source, target, and edge payload rows.
    """
    matching_edges = []
    edge_iterators = []

    if plan.direction == "outgoing":
        edge_iterators.append(graph.out_edges(node_id, keys=True, data=True))
    elif plan.direction == "incoming":
        edge_iterators.append(graph.in_edges(node_id, keys=True, data=True))
    elif GraphRelationType.CONFLICTS_WITH.value in plan.relation_types:
        edge_iterators.append(graph.out_edges(node_id, keys=True, data=True))
        edge_iterators.append(graph.in_edges(node_id, keys=True, data=True))
    else:
        edge_iterators.append(graph.out_edges(node_id, keys=True, data=True))

    for edge_iterator in edge_iterators:
        for source_id, target_id, _edge_key, edge_data in edge_iterator:
            if edge_data.get("relation") not in plan.relation_types:
                continue
            if plan.direction == "pairwise":
                if plan.source_entity is None or plan.target_entity is None:
                    continue
                source_entity_id = plan.source_entity.entity_id
                target_entity_id = plan.target_entity.entity_id
                if GraphRelationType.CONFLICTS_WITH.value in plan.relation_types:
                    if {source_id, target_id} != {
                        source_entity_id,
                        target_entity_id,
                    }:
                        continue
                elif (source_id, target_id) != (
                    source_entity_id,
                    target_entity_id,
                ):
                    continue
            matching_edges.append((source_id, target_id, edge_data))

    return matching_edges


def collect_graph_relations(
    graph: nx.MultiDiGraph,
    plan: GraphQueryPlan,
) -> tuple[GraphRelation, ...]:
    """
    Traverse the graph for a parsed query and collect matching relations.

    Args:
        graph (nx.MultiDiGraph): Loaded plugin relation graph.
        plan (GraphQueryPlan): Position-based graph query plan.

    Returns:
        tuple[GraphRelation, ...]: Matching graph relations with evidence.
    """
    anchor = plan.source_entity or plan.target_entity
    if anchor is None:
        return ()
    frontier = {anchor.entity_id}
    visited_nodes = set(frontier)
    relation_keys = set()
    relations = []

    for _depth in range(plan.traversal_depth):
        next_frontier = set()

        for node_id in frontier:
            for source_id, target_id, edge_data in iter_relation_edges(
                graph,
                node_id,
                plan,
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

                neighbor_id = source_id if plan.direction == "incoming" else target_id

                if neighbor_id not in visited_nodes:
                    visited_nodes.add(neighbor_id)
                    next_frontier.add(neighbor_id)

        frontier = next_frontier
        if not frontier:
            break

    return tuple(relations)


def retrieve_graph_relations(
    query: str,
    plugin_lookup: PluginLookup,
    graph: nx.MultiDiGraph,
    logger=None,
) -> GraphRetrievalResult | None:
    """
    Retrieve graph relations for a relational plugin query.

    Args:
        query (str): User query text.
        plugin_lookup (PluginLookup): Canonical plugin lookup built from IDs.
        graph (nx.MultiDiGraph): Loaded plugin relation graph.
        logger (logging.Logger | None): Optional logger for retrieval decisions.

    Returns:
        GraphRetrievalResult | None: Structured graph retrieval output when matched.
    """
    plan = parse_graph_query(query, plugin_lookup)
    if not plan:
        if logger:
            logger.debug("Graph query not recognized; using semantic retrieval fallback.")
        return None

    plan_entities = (plan.source_entity, plan.target_entity)
    if any(entity is not None and entity.entity_id not in graph for entity in plan_entities):
        if logger:
            logger.debug("Graph query entity not found; using semantic retrieval fallback.")
        return None

    anchor = plan.source_entity or plan.target_entity
    if anchor is None:
        if logger:
            logger.debug("Graph query has no anchor entity; using semantic retrieval fallback.")
        return None

    relations = collect_graph_relations(graph, plan)
    if logger:
        logger.info(
            "Graph query matched: direction=%s source=%s target=%s depth=%d relations=%d",
            plan.direction,
            plan.source_entity.entity_id if plan.source_entity else "unknown",
            plan.target_entity.entity_id if plan.target_entity else "unknown",
            plan.traversal_depth,
            len(relations),
        )

    return GraphRetrievalResult(
        query_entity=anchor.name,
        matched_entity_id=anchor.entity_id,
        relations=relations,
        traversal_depth=plan.traversal_depth,
    )
