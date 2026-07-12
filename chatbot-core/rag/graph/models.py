"""Typed model objects for GraphRAG triples and retrieval results."""

from dataclasses import dataclass, field

from rag.graph.schema import (
    DEFAULT_MIN_CONFIDENCE,
    is_valid_confidence,
    is_valid_entity_type,
    is_valid_relation_type,
)


def _require_non_empty(value: str, field_name: str) -> None:
    """
    Require a string field to contain a non-whitespace value.

    Args:
        value (str): String value to validate.
        field_name (str): Field name used in the error message.

    Raises:
        ValueError: If the value is empty or only whitespace.
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _validate_relation_payload(relation: str, confidence: float) -> None:
    """
    Validate relation type and confidence fields shared by graph models.

    Args:
        relation (str): Relation type value.
        confidence (float): Relation confidence score.

    Raises:
        ValueError: If relation or confidence is invalid.
    """
    if not is_valid_relation_type(relation):
        raise ValueError(f"invalid relation: {relation}")
    if not is_valid_confidence(confidence, DEFAULT_MIN_CONFIDENCE):
        raise ValueError(f"invalid confidence: {confidence}")


@dataclass(frozen=True)
class GraphEntity:
    """
    Entity reference used by triples and graph relations.

    Args:
        name (str): Human-readable entity name.
        entity_type (str): Entity type from the graph schema.
        entity_id (str): Optional canonical graph node identifier.
    """

    name: str
    entity_type: str
    entity_id: str = ""

    def __post_init__(self) -> None:
        """
        Validate entity fields after dataclass construction.

        Raises:
            ValueError: If the name is empty or the entity type is unsupported.
        """
        _require_non_empty(self.name, "name")
        if not is_valid_entity_type(self.entity_type):
            raise ValueError(f"invalid entity_type: {self.entity_type}")
        if self.entity_id:
            _require_non_empty(self.entity_id, "entity_id")


@dataclass(frozen=True)
class GraphEvidence:
    """
    Source evidence attached to a graph relation.

    Args:
        source_chunk_id (str): Identifier of the source chunk.
        source_title (str): Title attached to the source chunk.
        source_data_source (str): Source collection name for the chunk.
        evidence (str): Text evidence supporting the relation.
    """

    source_chunk_id: str
    source_title: str
    source_data_source: str
    evidence: str

    def __post_init__(self) -> None:
        """
        Validate source evidence fields after dataclass construction.

        Raises:
            ValueError: If any required evidence value is missing or empty.
        """
        _require_non_empty(self.source_chunk_id, "source_chunk_id")
        _require_non_empty(self.source_title, "source_title")
        _require_non_empty(self.source_data_source, "source_data_source")
        _require_non_empty(self.evidence, "evidence")


@dataclass(frozen=True)
class Triple:
    """
    Accepted source-grounded relation before graph storage.

    Args:
        source (GraphEntity): Source entity in the directed relation.
        relation (str): Relation type from the graph schema.
        target (GraphEntity): Target entity in the directed relation.
        evidence (GraphEvidence): Source chunk evidence for the relation.
        confidence (float): Confidence score for the relation.
    """

    source: GraphEntity
    relation: str
    target: GraphEntity
    evidence: GraphEvidence
    confidence: float

    def __post_init__(self) -> None:
        """
        Validate relation fields after dataclass construction.

        Raises:
            ValueError: If relation or confidence is invalid.
        """
        _validate_relation_payload(self.relation, self.confidence)


@dataclass(frozen=True)
class GraphRelation:
    """
    Relation returned from a graph traversal.

    Args:
        source (GraphEntity): Source graph node with a canonical entity ID.
        relation (str): Relation type from the graph schema.
        target (GraphEntity): Target graph node with a canonical entity ID.
        evidence (GraphEvidence): Source chunk evidence for the relation.
        confidence (float): Confidence score for the relation.
    """

    source: GraphEntity
    relation: str
    target: GraphEntity
    evidence: GraphEvidence
    confidence: float

    def __post_init__(self) -> None:
        """
        Validate graph relation fields after dataclass construction.

        Raises:
            ValueError: If node IDs, relation, or confidence are invalid.
        """
        _require_non_empty(self.source.entity_id, "source.entity_id")
        _require_non_empty(self.target.entity_id, "target.entity_id")
        _validate_relation_payload(self.relation, self.confidence)


@dataclass(frozen=True)
class GraphRetrievalResult:
    """
    Result object returned by graph retrieval code.

    Args:
        query_entity (str): Entity text detected in the user query.
        matched_entity_id (str): Canonical graph node matched for the query.
        relations (tuple[GraphRelation, ...]): Relations found by traversal.
        traversal_depth (int): Traversal depth used to collect relations.
    """

    query_entity: str
    matched_entity_id: str
    relations: tuple[GraphRelation, ...] = field(default_factory=tuple)
    traversal_depth: int = 1

    def __post_init__(self) -> None:
        """
        Validate retrieval result fields after dataclass construction.

        Raises:
            ValueError: If entity fields are empty or traversal depth is invalid.
        """
        _require_non_empty(self.query_entity, "query_entity")
        _require_non_empty(self.matched_entity_id, "matched_entity_id")
        if self.traversal_depth < 1:
            raise ValueError("traversal_depth must be positive")
        if not isinstance(self.relations, tuple):
            object.__setattr__(self, "relations", tuple(self.relations))
