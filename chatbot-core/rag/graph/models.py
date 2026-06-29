"""GraphRAG model objects."""

from dataclasses import dataclass, field

from rag.graph.schema import (
    DEFAULT_MIN_CONFIDENCE,
    has_required_evidence_fields,
    is_valid_confidence,
    is_valid_entity_type,
    is_valid_relation_type,
)


def _require_non_empty(value: str, field_name: str) -> None:
    """Check a string field is not empty."""
    if not value or not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _validate_relation_payload(relation: str, confidence: float) -> None:
    """Check common relation fields."""
    if not is_valid_relation_type(relation):
        raise ValueError(f"invalid relation: {relation}")
    if not is_valid_confidence(confidence, DEFAULT_MIN_CONFIDENCE):
        raise ValueError(f"invalid confidence: {confidence}")


@dataclass(frozen=True)
class GraphEntity:
    """Entity used in graph data."""

    name: str
    entity_type: str
    entity_id: str = ""

    def __post_init__(self) -> None:
        """Check entity fields."""
        _require_non_empty(self.name, "name")
        if not is_valid_entity_type(self.entity_type):
            raise ValueError(f"invalid entity_type: {self.entity_type}")
        if self.entity_id:
            _require_non_empty(self.entity_id, "entity_id")


@dataclass(frozen=True)
class GraphEvidence:
    """Evidence from the source chunk."""

    source_chunk_id: str
    source_title: str
    source_data_source: str
    evidence: str

    def __post_init__(self) -> None:
        """Check evidence fields."""
        evidence_payload = {
            "source_chunk_id": self.source_chunk_id,
            "source_title": self.source_title,
            "source_data_source": self.source_data_source,
            "evidence": self.evidence,
        }
        if not has_required_evidence_fields(evidence_payload):
            raise ValueError("missing evidence fields")

        _require_non_empty(self.source_chunk_id, "source_chunk_id")
        _require_non_empty(self.source_title, "source_title")
        _require_non_empty(self.source_data_source, "source_data_source")
        _require_non_empty(self.evidence, "evidence")


@dataclass(frozen=True)
class Triple:
    """Raw graph triple found from a source chunk."""

    source: GraphEntity
    relation: str
    target: GraphEntity
    evidence: GraphEvidence
    confidence: float

    def __post_init__(self) -> None:
        """Check triple fields."""
        _validate_relation_payload(self.relation, self.confidence)


@dataclass(frozen=True)
class GraphRelation:
    """Relation returned from the graph."""

    source: GraphEntity
    relation: str
    target: GraphEntity
    evidence: GraphEvidence
    confidence: float

    def __post_init__(self) -> None:
        """Check relation fields."""
        _require_non_empty(self.source.entity_id, "source.entity_id")
        _require_non_empty(self.target.entity_id, "target.entity_id")
        _validate_relation_payload(self.relation, self.confidence)


@dataclass(frozen=True)
class GraphRetrievalResult:
    """Graph retrieval output."""

    query_entity: str
    matched_entity_id: str
    relations: tuple[GraphRelation, ...] = field(default_factory=tuple)
    traversal_depth: int = 1

    def __post_init__(self) -> None:
        """Check retrieval result fields."""
        _require_non_empty(self.query_entity, "query_entity")
        _require_non_empty(self.matched_entity_id, "matched_entity_id")
        if self.traversal_depth < 1:
            raise ValueError("traversal_depth must be positive")
        if not isinstance(self.relations, tuple):
            object.__setattr__(self, "relations", tuple(self.relations))
