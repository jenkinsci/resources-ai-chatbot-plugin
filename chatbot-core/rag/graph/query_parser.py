"""Parse obvious GraphRAG questions from entity and relation positions."""

from dataclasses import dataclass
import re

from rag.graph.models import GraphEntity
from rag.graph.schema import GraphEntityType, GraphRelationType
from rag.graph.triple_extractor import (
    PluginLookup,
    build_candidate_variants,
    resolve_plugin_id,
)


QUERY_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9+._-]*")
QUERY_WHITESPACE_PATTERN = re.compile(r"\s+")
QUERY_PUNCTUATION_PATTERN = re.compile(r"[?!,:;]+")
MAX_QUERY_ENTITY_TOKENS = 8
MULTI_HOP_QUERY_PATTERNS = (
    re.compile(r"\bindirect(?:ly)?\b", re.IGNORECASE),
    re.compile(r"\btransitive(?:ly)?\b", re.IGNORECASE),
)

DEPENDENCY_RELATIONS = (
    ("depend on", "dependency"),
    ("depends on", "dependency"),
    ("require", "dependency"),
    ("requires", "dependency"),
    ("need", "dependency"),
    ("needs", "dependency"),
    ("rely on", "dependency"),
    ("relies on", "dependency"),
)
CONFLICT_RELATIONS = (
    ("conflict with", "conflict"),
    ("conflicts with", "conflict"),
    ("incompatible with", "conflict"),
)
NEGATION_WORDS = frozenset({"not", "never"})


@dataclass(frozen=True)
class QueryToken:
    """
    A lower-cased query token with offsets into the raw query.

    Attributes:
        text: Token text used for matching.
        start: Inclusive raw-query offset.
        end: Exclusive raw-query offset.
    """

    text: str
    start: int
    end: int


@dataclass(frozen=True)
class RelationMention:
    """
    A supported relation phrase and its raw-query span.

    Attributes:
        phrase: Matched relation phrase.
        family: ``dependency`` or ``conflict``.
        start: Inclusive raw-query offset.
        end: Exclusive raw-query offset.
    """

    phrase: str
    family: str
    start: int
    end: int


@dataclass(frozen=True)
class ResolvedQueryEntity:
    """
    A canonical Jenkins plugin and its raw-query span.

    Attributes:
        text: Original entity spelling.
        entity: Canonical graph entity.
        start: Inclusive raw-query offset.
        end: Exclusive raw-query offset.
    """

    text: str
    entity: GraphEntity
    start: int
    end: int


@dataclass(frozen=True)
class GraphQueryPlan:
    """
    The graph operation inferred from one supported query shape.

    Attributes:
        relation_types: Graph edge types to traverse.
        direction: ``outgoing``, ``incoming``, or ``pairwise``.
        source_entity: Known source entity, if any.
        target_entity: Known target entity, if any.
        traversal_depth: Number of graph hops.
        matched_rule: Diagnostic position-based rule label.
    """

    relation_types: tuple[str, ...]
    direction: str
    source_entity: GraphEntity | None
    target_entity: GraphEntity | None
    traversal_depth: int
    matched_rule: str


def normalize_graph_query(query: str) -> str:
    """
    Normalize formatting without interpreting relation or entity meaning.

    Args:
        query: Raw user query.

    Returns:
        Normalized text for simple keyword matching.
    """
    normalized = query.translate(
        str.maketrans(
            {
                "\u2018": "'",
                "\u2019": "'",
                "\u2010": "-",
                "\u2011": "-",
                "\u2013": "-",
                "\u2014": "-",
            }
        )
    ).lower()
    normalized = re.sub(r"\bplug[\s-]?ins\b", "plugins", normalized)
    normalized = re.sub(r"\bplug[\s-]?in\b", "plugin", normalized)
    normalized = QUERY_PUNCTUATION_PATTERN.sub(" ", normalized)
    return QUERY_WHITESPACE_PATTERN.sub(" ", normalized).strip()


def build_query_entity(plugin_id: str) -> GraphEntity:
    """
    Create a plugin graph entity from a canonical plugin ID.

    Args:
        plugin_id: Canonical Jenkins plugin ID.

    Returns:
        Plugin graph entity.
    """
    return GraphEntity(
        name=plugin_id,
        entity_type=GraphEntityType.PLUGIN.value,
        entity_id=plugin_id,
    )


def _tokens(query: str) -> tuple[QueryToken, ...]:
    """
    Tokenize raw text while preserving positions for role matching.

    Args:
        query: Raw user query.

    Returns:
        Ordered query tokens with raw-query spans.
    """
    return tuple(
        QueryToken(
            text=match.group().lower().rstrip(".?!,:;"),
            start=match.start(),
            end=match.end(),
        )
        for match in QUERY_TOKEN_PATTERN.finditer(query)
    )


def _find_relation(query: str) -> RelationMention | None:
    """
    Find a supported relation phrase without assigning direction.

    Args:
        query: Raw user query.

    Returns:
        Relation mention, or ``None`` when no supported phrase is found.
    """
    tokens = _tokens(query)
    for index, token in enumerate(tokens):
        for phrase, family in (*DEPENDENCY_RELATIONS, *CONFLICT_RELATIONS):
            words = phrase.split()
            if [token.text for token in tokens[index : index + len(words)]] != words:
                continue
            end_token = tokens[index + len(words) - 1]
            return RelationMention(
                phrase=phrase,
                family=family,
                start=token.start,
                end=end_token.end,
            )
    return None


def _relation_types(query: str, relation: RelationMention) -> tuple[str, ...]:
    """
    Map a relation mention and modifiers to graph edge types.

    Args:
        query: Raw user query containing modifiers.
        relation: Detected relation mention.

    Returns:
        Graph relation types requested by the query.
    """
    if relation.family == "conflict":
        return (GraphRelationType.CONFLICTS_WITH.value,)
    words = {token.text for token in _tokens(query)}
    if words & {"optional", "optionally"}:
        return (GraphRelationType.OPTIONAL_DEPENDS_ON.value,)
    if relation.phrase in {"require", "requires"} or "required" in words:
        return (GraphRelationType.DEPENDS_ON.value,)
    return (
        GraphRelationType.DEPENDS_ON.value,
        GraphRelationType.OPTIONAL_DEPENDS_ON.value,
    )


def detect_graph_relation_types(query: str) -> tuple[str, ...] | None:
    """
    Detect a relation family without assigning entity roles.

    Args:
        query: Raw user query.

    Returns:
        Relation types, or ``None`` when no phrase is recognized.
    """
    relation = _find_relation(query)
    return _relation_types(query, relation) if relation else None


def _build_plan(
    query: str,
    relation: RelationMention,
    entities: tuple[ResolvedQueryEntity, ...],
) -> GraphQueryPlan | None:
    """
    Build a plan from entity positions or abstain.

    Args:
        query: Raw user query.
        relation: Detected relation mention.
        entities: Resolved plugin entities in query order.

    Returns:
        Position-based graph plan, or ``None`` for an unsupported layout.
    """
    if len(entities) not in {1, 2}:
        return None
    before = [entity for entity in entities if entity.end <= relation.start]
    after = [entity for entity in entities if entity.start >= relation.end]
    if len(entities) == 2:
        if len(before) != 1 or len(after) != 1:
            return None
        direction = "pairwise"
        source, target = before[0].entity, after[0].entity
    elif before:
        if relation.family == "conflict":
            return None
        direction = "outgoing"
        source, target = before[0].entity, None
    elif after:
        if relation.family == "conflict":
            return None
        direction = "incoming"
        source, target = (None, after[0].entity)
    else:
        return None

    normalized = normalize_graph_query(query)
    depth = 2 if any(pattern.search(normalized) for pattern in MULTI_HOP_QUERY_PATTERNS) else 1
    return GraphQueryPlan(
        relation_types=_relation_types(query, relation),
        direction=direction,
        source_entity=source,
        target_entity=target,
        traversal_depth=depth,
        matched_rule=f"{relation.family}_by_position",
    )


def build_graph_query_plan(
    query: str,
    entities: tuple[ResolvedQueryEntity, ...],
) -> GraphQueryPlan | None:
    """
    Resolve the relation and build a position-based graph plan.

    Args:
        query: Raw user query.
        entities: Resolved plugin entities in query order.

    Returns:
        Graph query plan, or ``None`` when parsing abstains.
    """
    relation = _find_relation(query)
    return _build_plan(query, relation, entities) if relation else None


def resolve_query_entities(
    text: str,
    plugin_lookup: PluginLookup,
) -> tuple[ResolvedQueryEntity, ...]:
    """
    Resolve all non-overlapping Jenkins plugin mentions with raw spans.

    Args:
        text: Raw query text.
        plugin_lookup: Existing Jenkins plugin lookup.

    Returns:
        Ordered resolved entities, possibly empty.
    """
    tokens = list(QUERY_TOKEN_PATTERN.finditer(text))
    resolved: list[ResolvedQueryEntity] = []
    occupied: set[int] = set()
    for start_index, token in enumerate(tokens):
        if start_index in occupied:
            continue
        for token_count in range(
            min(MAX_QUERY_ENTITY_TOKENS, len(tokens) - start_index), 0, -1
        ):
            indexes = range(start_index, start_index + token_count)
            if any(index in occupied for index in indexes):
                continue
            phrase = " ".join(tokens[index].group() for index in indexes)
            plugin_id = next(
                (
                    resolved_id
                    for variant in build_candidate_variants(phrase)
                    if (resolved_id := resolve_plugin_id(variant, plugin_lookup))
                ),
                None,
            )
            if not plugin_id:
                continue
            end_token = tokens[start_index + token_count - 1]
            resolved.append(
                ResolvedQueryEntity(
                    text=text[token.start() : end_token.end()],
                    entity=build_query_entity(plugin_id),
                    start=token.start(),
                    end=end_token.end(),
                )
            )
            occupied.update(indexes)
            break
    return tuple(resolved)


def parse_graph_query(
    query: str,
    plugin_lookup: PluginLookup,
) -> GraphQueryPlan | None:
    """
    Parse an obvious graph-shaped query or abstain.

    Args:
        query: Raw user query.
        plugin_lookup: Existing Jenkins plugin lookup.

    Returns:
        Position-based graph plan, or ``None`` for negated or unsupported
        wording.
    """
    if any(token.text in NEGATION_WORDS for token in _tokens(query)):
        return None
    entities = resolve_query_entities(query, plugin_lookup)
    plan = build_graph_query_plan(query, entities)
    return plan
