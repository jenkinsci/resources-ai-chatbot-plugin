"""Query intent and entity resolution helpers for GraphRAG retrieval."""

from dataclasses import dataclass
import re
from pathlib import Path

import networkx as nx

from rag.graph.entity_normalizer import (
    DEFAULT_PLUGIN_NAMES_PATH,
    build_plugin_aliases,
    load_canonical_plugin_ids,
    resolve_plugin_name,
)
from rag.graph.graph_store import DEFAULT_PLUGIN_GRAPH_PATH, load_graph
from rag.graph.models import GraphEntity, GraphEvidence, GraphRelation, GraphRetrievalResult
from rag.graph.schema import GraphEntityType, GraphRelationType
from rag.graph.triple_extractor import build_candidate_variants


QUERY_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9+._-]*")
MAX_QUERY_ENTITY_TOKENS = 8

DEPENDENCY_QUERY_PATTERNS = (
    re.compile(r"\bwhat does .+ depend on\b", re.IGNORECASE),
    re.compile(r"\bdoes .+ depend on\b", re.IGNORECASE),
    re.compile(r"\bdepends on\b", re.IGNORECASE),
    re.compile(r"\bdependencies of\b", re.IGNORECASE),
    re.compile(r"\brequires?\b", re.IGNORECASE),
)
REVERSE_DEPENDENCY_QUERY_PATTERNS = (
    re.compile(r"\bwhat depends on\b", re.IGNORECASE),
    re.compile(r"\bwhich plugins depend on\b", re.IGNORECASE),
    re.compile(r"\bdepended on by\b", re.IGNORECASE),
    re.compile(r"\brequired by\b", re.IGNORECASE),
    re.compile(r"\bdepending on\b", re.IGNORECASE),
)
CONFLICT_QUERY_PATTERNS = (
    re.compile(r"\bconflicts? with\b", re.IGNORECASE),
    re.compile(r"\bincompatible with\b", re.IGNORECASE),
    re.compile(r"\bconflicts?\b", re.IGNORECASE),
    re.compile(r"\bincompatible\b", re.IGNORECASE),
)
MULTI_HOP_QUERY_PATTERNS = (
    re.compile(r"\bindirect(?:ly)?\b", re.IGNORECASE),
    re.compile(r"\btransitive(?:ly)?\b", re.IGNORECASE),
    re.compile(r"\bthrough\b", re.IGNORECASE),
    re.compile(r"\bchain\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class GraphQueryIntent:
    """
    Parsed graph intent from a user query.

    Args:
        relation_types (tuple[str, ...]): Relation types requested by the query.
        direction (str): Traversal direction needed for the relation query.
        traversal_depth (int): Traversal depth requested by the query.
    """

    relation_types: tuple[str, ...]
    direction: str
    traversal_depth: int = 1


@dataclass(frozen=True)
class GraphQueryMatch:
    """
    Parsed graph query state used by later retrieval code.

    Args:
        query (str): Original user query.
        query_entity (str): Raw entity text found in the query.
        matched_entity (GraphEntity): Canonical plugin entity matched from the query.
        intent (GraphQueryIntent): Parsed relation intent.
    """

    query: str
    query_entity: str
    matched_entity: GraphEntity
    intent: GraphQueryIntent


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


def build_query_entity(plugin_id: str) -> GraphEntity:
    """
    Build a plugin graph entity from a canonical plugin ID.

    Args:
        plugin_id (str): Canonical plugin ID.

    Returns:
        GraphEntity: Plugin entity used by query parsing.
    """
    return GraphEntity(
        name=plugin_id,
        entity_type=GraphEntityType.PLUGIN.value,
        entity_id=plugin_id,
    )


def detect_graph_query_intent(query: str) -> GraphQueryIntent | None:
    """
    Detect relation intent from a user query.

    Args:
        query (str): User query text.

    Returns:
        GraphQueryIntent | None: Parsed graph intent, if the query is relational.
    """
    query_lower = query.lower()
    traversal_depth = (
        2
        if any(pattern.search(query_lower) for pattern in MULTI_HOP_QUERY_PATTERNS)
        else 1
    )

    if any(pattern.search(query_lower) for pattern in CONFLICT_QUERY_PATTERNS):
        return GraphQueryIntent(
            relation_types=(GraphRelationType.CONFLICTS_WITH.value,),
            direction="both",
            traversal_depth=traversal_depth,
        )

    if any(pattern.search(query_lower) for pattern in REVERSE_DEPENDENCY_QUERY_PATTERNS):
        return GraphQueryIntent(
            relation_types=(
                GraphRelationType.DEPENDS_ON.value,
                GraphRelationType.OPTIONAL_DEPENDS_ON.value,
            ),
            direction="incoming",
            traversal_depth=traversal_depth,
        )

    if any(pattern.search(query_lower) for pattern in DEPENDENCY_QUERY_PATTERNS):
        return GraphQueryIntent(
            relation_types=(
                GraphRelationType.DEPENDS_ON.value,
                GraphRelationType.OPTIONAL_DEPENDS_ON.value,
            ),
            direction="outgoing",
            traversal_depth=traversal_depth,
        )

    return None


def resolve_query_entity(
    query: str,
    plugin_aliases: dict[str, str],
    intent: GraphQueryIntent | None = None,
) -> tuple[str, GraphEntity] | None:
    """
    Resolve a plugin entity from query text.

    Args:
        query (str): User query text.
        plugin_aliases (dict[str, str]): Alias map built from canonical plugin IDs.
        intent (GraphQueryIntent | None): Parsed graph intent when available.

    Returns:
        tuple[str, GraphEntity] | None: Matched query text and canonical plugin entity.
    """
    for lookup_span in build_query_lookup_spans(query, intent):
        entity_match = resolve_query_entity_text(lookup_span, plugin_aliases)
        if entity_match:
            return entity_match

    return resolve_query_entity_text(query, plugin_aliases)


def build_query_lookup_spans(
    query: str,
    intent: GraphQueryIntent | None,
) -> list[str]:
    """
    Build focused query spans for entity resolution.

    Args:
        query (str): User query text.
        intent (GraphQueryIntent | None): Parsed graph intent when available.

    Returns:
        list[str]: Query text spans to scan for plugin entity lookup.
    """
    lookup_spans = [query]
    query_lower = query.lower()

    if intent and intent.direction == "outgoing":
        if "what does " in query_lower and " depend on" in query_lower:
            start_index = query_lower.index("what does ") + len("what does ")
            end_index = query_lower.index(" depend on")
            lookup_spans.insert(0, query[start_index:end_index])
        if "dependencies of " in query_lower:
            start_index = query_lower.index("dependencies of ") + len("dependencies of ")
            lookup_spans.insert(0, query[start_index:])

    if intent and intent.direction == "incoming":
        if "what depends on " in query_lower:
            start_index = query_lower.index("what depends on ") + len("what depends on ")
            lookup_spans.insert(0, query[start_index:])
        if "which plugins depend on " in query_lower:
            start_index = query_lower.index("which plugins depend on ") + len(
                "which plugins depend on "
            )
            lookup_spans.insert(0, query[start_index:])
        if "required by " in query_lower:
            start_index = query_lower.index("required by ") + len("required by ")
            lookup_spans.insert(0, query[start_index:])

    if " through " in query_lower:
        lookup_spans = [text.split(" through ", 1)[0] for text in lookup_spans]

    return list(dict.fromkeys(text.strip(" ?") for text in lookup_spans if text.strip()))


def resolve_query_entity_text(
    text: str,
    plugin_aliases: dict[str, str],
) -> tuple[str, GraphEntity] | None:
    """
    Resolve a plugin entity from one text span.

    Args:
        text (str): Candidate query text span.
        plugin_aliases (dict[str, str]): Alias map built from canonical plugin IDs.

    Returns:
        tuple[str, GraphEntity] | None: Matched text and canonical plugin entity.
    """
    tokens = QUERY_TOKEN_PATTERN.findall(text)
    max_length = min(len(tokens), MAX_QUERY_ENTITY_TOKENS)

    for token_count in range(max_length, 0, -1):
        for start_index in range(len(tokens) - token_count + 1):
            lookup_phrase = " ".join(tokens[start_index : start_index + token_count])
            for variant in build_candidate_variants(lookup_phrase):
                target_id = resolve_plugin_name(variant, plugin_aliases)
                if target_id:
                    return lookup_phrase, build_query_entity(target_id)

    return None


def parse_graph_query(
    query: str,
    plugin_aliases: dict[str, str],
) -> GraphQueryMatch | None:
    """
    Parse a user query into graph intent and a canonical entity.

    Args:
        query (str): User query text.
        plugin_aliases (dict[str, str]): Alias map built from canonical plugin IDs.

    Returns:
        GraphQueryMatch | None: Parsed graph query state when graph retrieval applies.
    """
    intent = detect_graph_query_intent(query)
    if not intent:
        return None

    entity_match = resolve_query_entity(query, plugin_aliases, intent)
    if not entity_match:
        return None

    query_entity, matched_entity = entity_match
    return GraphQueryMatch(
        query=query,
        query_entity=query_entity,
        matched_entity=matched_entity,
        intent=intent,
    )


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
