"""GraphRAG schema definitions."""

from enum import Enum


class GraphEntityType(str, Enum):
    """Entity types we support in the graph."""

    PLUGIN = "Plugin"
    PLUGIN_VERSION = "PluginVersion"
    CVE = "CVE"
    CONFIGURATION = "Configuration"
    ERROR = "Error"


class GraphRelationType(str, Enum):
    """Relation types we support in the graph."""

    DEPENDS_ON = "DEPENDS_ON"
    OPTIONAL_DEPENDS_ON = "OPTIONAL_DEPENDS_ON"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    FIXED_IN = "FIXED_IN"
    CAUSES = "CAUSES"
    RESOLVES = "RESOLVES"
    MENTIONS = "MENTIONS"


MIN_RELATION_CONFIDENCE = 0.0
MAX_RELATION_CONFIDENCE = 1.0
DEFAULT_MIN_CONFIDENCE = 0.5

REQUIRED_EVIDENCE_FIELDS = frozenset(
    {
        "source_chunk_id",
        "source_title",
        "source_data_source",
        "evidence",
    }
)

REQUIRED_EDGE_FIELDS = frozenset(
    {
        *REQUIRED_EVIDENCE_FIELDS,
        "relation",
        "confidence",
    }
)

ALLOWED_ENTITY_TYPES = frozenset(entity.value for entity in GraphEntityType)
ALLOWED_RELATION_TYPES = frozenset(relation.value for relation in GraphRelationType)


def is_valid_entity_type(entity_type: str) -> bool:
    """Check if this is a known entity type."""
    return entity_type in ALLOWED_ENTITY_TYPES


def is_valid_relation_type(relation_type: str) -> bool:
    """Check if this is a known relation type."""
    return relation_type in ALLOWED_RELATION_TYPES


def is_valid_confidence(
    confidence: float,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> bool:
    """Check if confidence is good enough."""
    return (
        MIN_RELATION_CONFIDENCE
        <= confidence
        <= MAX_RELATION_CONFIDENCE
        and confidence >= min_confidence
    )


def has_required_evidence_fields(evidence: dict) -> bool:
    """Check if evidence has the fields we need."""
    return REQUIRED_EVIDENCE_FIELDS.issubset(evidence)


def has_required_edge_fields(edge_data: dict) -> bool:
    """Check if edge data has the fields we need."""
    return REQUIRED_EDGE_FIELDS.issubset(edge_data)
