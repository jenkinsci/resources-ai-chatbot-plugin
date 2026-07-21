"""GraphRAG query intent and entity parsing helpers."""

from dataclasses import dataclass
import re

from rag.graph.entity_normalizer import resolve_plugin_name
from rag.graph.models import GraphEntity
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
    Parsed graph query state used by graph traversal.

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

    entity_match = resolve_query_entity_text(query, plugin_aliases)
    if not entity_match:
        return None

    query_entity, matched_entity = entity_match
    return GraphQueryMatch(
        query=query,
        query_entity=query_entity,
        matched_entity=matched_entity,
        intent=intent,
    )
