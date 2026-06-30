"""Unit tests for GraphRAG schema."""

from rag.graph.schema import (
    GraphEntityType,
    GraphRelationType,
    has_required_edge_fields,
    has_required_evidence_fields,
    is_valid_confidence,
    is_valid_entity_type,
    is_valid_relation_type,
)


def test_valid_entity_type():
    """Test known entity type."""
    assert is_valid_entity_type(GraphEntityType.PLUGIN.value)


def test_invalid_entity_type():
    """Test unknown entity type."""
    assert not is_valid_entity_type("Unknown")


def test_valid_relation_type():
    """Test known relation type."""
    assert is_valid_relation_type(GraphRelationType.DEPENDS_ON.value)


def test_invalid_relation_type():
    """Test unknown relation type."""
    assert not is_valid_relation_type("USES")


def test_confidence_must_be_in_range_and_above_threshold():
    """Test confidence range checks."""
    assert is_valid_confidence(0.7)
    assert not is_valid_confidence(0.4)
    assert not is_valid_confidence(-0.1)
    assert not is_valid_confidence(1.1)


def test_required_evidence_fields():
    """Test evidence field check."""
    evidence = {
        "source_chunk_id": "chunk-1",
        "source_title": "Git plugin",
        "source_data_source": "plugins",
        "evidence": "Git plugin is mentioned.",
    }
    assert has_required_evidence_fields(evidence)


def test_required_edge_fields():
    """Test edge field check."""
    edge_data = {
        "source_chunk_id": "chunk-1",
        "source_title": "Git plugin",
        "source_data_source": "plugins",
        "evidence": "Git plugin is mentioned.",
        "relation": GraphRelationType.MENTIONS.value,
        "confidence": 0.8,
    }
    assert has_required_edge_fields(edge_data)
