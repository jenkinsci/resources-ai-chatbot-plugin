"""GraphRAG schema definitions for plugin ecosystem relation artifacts."""

from enum import Enum


class GraphEntityType(str, Enum):
    """
    Entity types allowed in plugin ecosystem graph artifacts.
    """

    PLUGIN = "Plugin"
    PLUGIN_VERSION = "PluginVersion"
    CVE = "CVE"
    CONFIGURATION = "Configuration"
    ERROR = "Error"


class GraphRelationType(str, Enum):
    """
    Directed relation types allowed between graph entities.
    """

    DEPENDS_ON = "DEPENDS_ON"
    OPTIONAL_DEPENDS_ON = "OPTIONAL_DEPENDS_ON"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    FIXED_IN = "FIXED_IN"
    CAUSES = "CAUSES"
    RESOLVES = "RESOLVES"
    MENTIONS = "MENTIONS"


REQUIRED_EVIDENCE_FIELDS = frozenset(
    {
        "source_chunk_id",
        "source_title",
        "source_data_source",
        "evidence",
    }
)

ALLOWED_ENTITY_TYPES = frozenset(entity.value for entity in GraphEntityType)
ALLOWED_RELATION_TYPES = frozenset(relation.value for relation in GraphRelationType)


def is_valid_entity_type(entity_type: str) -> bool:
    """
    Check whether a string is an allowed graph entity type.

    Args:
        entity_type (str): Entity type value to validate.

    Returns:
        bool: True when the entity type is supported, False otherwise.
    """
    return entity_type in ALLOWED_ENTITY_TYPES


def is_valid_relation_type(relation_type: str) -> bool:
    """
    Check whether a string is an allowed graph relation type.

    Args:
        relation_type (str): Relation type value to validate.

    Returns:
        bool: True when the relation type is supported, False otherwise.
    """
    return relation_type in ALLOWED_RELATION_TYPES


def has_required_evidence_fields(evidence: dict) -> bool:
    """
    Check whether graph evidence contains the required source fields.

    Args:
        evidence (dict): Evidence payload to validate.

    Returns:
        bool: True when all required evidence fields are present.
    """
    return REQUIRED_EVIDENCE_FIELDS.issubset(evidence)
