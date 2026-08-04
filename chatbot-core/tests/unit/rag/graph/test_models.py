"""Unit tests for GraphRAG models."""

import pytest

from rag.graph.models import (
    GraphEntity,
    GraphEvidence,
    GraphRelation,
    GraphRetrievalResult,
    Triple,
)
from rag.graph.schema import GraphEntityType, GraphRelationType


def build_entity(name="Git plugin", entity_id="git"):
    """
    Build a plugin entity for model tests.

    Args:
        name (str): Entity display name.
        entity_id (str): Canonical graph node ID.

    Returns:
        GraphEntity: Test graph entity.
    """
    return GraphEntity(
        name=name,
        entity_type=GraphEntityType.PLUGIN.value,
        entity_id=entity_id,
    )


def build_evidence():
    """
    Build source evidence for model tests.

    Returns:
        GraphEvidence: Test graph evidence.
    """
    return GraphEvidence(
        source_chunk_id="chunk-1",
        source_title="Git plugin",
        source_data_source="plugins",
        evidence="Git plugin is mentioned in this chunk.",
    )


def test_triple_accepts_valid_payload():
    """
    Verify a valid triple can be constructed.
    """
    triple = Triple(
        source=build_entity("Blue Ocean", ""),
        relation=GraphRelationType.DEPENDS_ON.value,
        target=build_entity("Git plugin", ""),
        evidence=build_evidence(),
        confidence=0.9,
    )

    assert triple.relation == GraphRelationType.DEPENDS_ON.value


def test_triple_rejects_invalid_relation():
    """
    Verify triple construction rejects unsupported relation values.
    """
    with pytest.raises(ValueError, match="invalid relation"):
        Triple(
            source=build_entity("Blue Ocean", ""),
            relation="USES",
            target=build_entity("Git plugin", ""),
            evidence=build_evidence(),
            confidence=0.9,
        )


def test_entity_rejects_empty_name():
    """
    Verify graph entities require a non-empty name.
    """
    with pytest.raises(ValueError, match="name must not be empty"):
        GraphEntity(name="", entity_type=GraphEntityType.PLUGIN.value)


def test_evidence_rejects_empty_text():
    """
    Verify graph evidence requires non-empty evidence text.
    """
    with pytest.raises(ValueError, match="evidence must not be empty"):
        GraphEvidence(
            source_chunk_id="chunk-1",
            source_title="Git plugin",
            source_data_source="plugins",
            evidence="",
        )


def test_graph_relation_requires_node_ids():
    """
    Verify graph relations require canonical source and target node IDs.
    """
    with pytest.raises(ValueError, match="source.entity_id must not be empty"):
        GraphRelation(
            source=build_entity("Blue Ocean", ""),
            relation=GraphRelationType.DEPENDS_ON.value,
            target=build_entity("Git plugin", "git"),
            evidence=build_evidence(),
            confidence=0.9,
        )


def test_retrieval_result_converts_relations_to_tuple():
    """
    Verify retrieval results normalize relation collections to tuples.
    """
    relation = GraphRelation(
        source=build_entity("Blue Ocean", "blueocean"),
        relation=GraphRelationType.DEPENDS_ON.value,
        target=build_entity("Git plugin", "git"),
        evidence=build_evidence(),
        confidence=0.9,
    )

    result = GraphRetrievalResult(
        query_entity="Blue Ocean",
        matched_entity_id="blueocean",
        relations=[relation],
    )

    assert result.relations == (relation,)
