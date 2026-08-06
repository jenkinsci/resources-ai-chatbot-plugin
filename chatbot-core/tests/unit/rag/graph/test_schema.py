"""Unit tests for GraphRAG schema."""

from rag.graph.schema import (
    GraphEntityType,
    GraphRelationType,
    has_required_evidence_fields,
    is_valid_entity_type,
    is_valid_relation_type,
)


def test_valid_entity_type():
    """
    Verify that a schema-defined entity type is accepted.
    """
    assert is_valid_entity_type(GraphEntityType.PLUGIN.value)


def test_invalid_entity_type():
    """
    Verify that an unknown entity type is rejected.
    """
    assert not is_valid_entity_type("Unknown")


def test_valid_relation_type():
    """
    Verify that a schema-defined relation type is accepted.
    """
    assert is_valid_relation_type(GraphRelationType.DEPENDS_ON.value)


def test_invalid_relation_type():
    """
    Verify that an unknown relation type is rejected.
    """
    assert not is_valid_relation_type("USES")


def test_required_evidence_fields():
    """
    Verify evidence payloads with all required fields are accepted.
    """
    evidence = {
        "source_chunk_id": "chunk-1",
        "source_title": "Git plugin",
        "source_data_source": "plugins",
        "evidence": "Git plugin is mentioned.",
    }
    assert has_required_evidence_fields(evidence)
