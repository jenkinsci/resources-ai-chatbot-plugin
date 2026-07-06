"""Unit tests for GraphRAG deterministic triple extraction."""

from rag.graph.entity_normalizer import build_plugin_aliases
from rag.graph.schema import GraphRelationType
from rag.graph.triple_extractor import (
    build_candidate_variants,
    extract_triples_from_chunk,
    sentence_split,
)


def build_chunk(title: str, text: str, chunk_id: str = "chunk-1") -> dict:
    """
    Build a plugin chunk for extractor tests.

    Args:
        title (str): Source plugin title.
        text (str): Chunk text.
        chunk_id (str): Source chunk ID.

    Returns:
        dict: Chunk payload matching chunks_plugin_docs.json.
    """
    return {
        "id": chunk_id,
        "chunk_text": text,
        "metadata": {
            "title": title,
            "data_source": "jenkins_plugins_documentation",
        },
    }


def build_aliases() -> dict[str, str]:
    """
    Build plugin aliases used by extractor tests.

    Returns:
        dict[str, str]: Plugin alias map.
    """
    return build_plugin_aliases(
        [
            "android-signing",
            "blueocean",
            "credentials",
            "git",
            "junit",
            "legacy-plugin",
            "port-allocator",
            "source-plugin",
            "target-plugin",
            "jenkins",
        ]
    )


def test_sentence_split_drops_empty_sentences():
    """
    Verify the sentence splitter returns useful text spans.
    """
    sentences = sentence_split("First sentence. Second sentence!  ")

    assert sentences == ["First sentence.", "Second sentence!"]


def test_build_candidate_variants_handles_jenkins_plugin_names():
    """
    Verify candidate variants strip Jenkins prefixes and plugin suffixes.
    """
    variants = build_candidate_variants("Jenkins Credentials Plugin")

    assert variants == [
        "Jenkins Credentials Plugin",
        "Credentials Plugin",
        "Jenkins Credentials",
        "Credentials",
    ]


def test_extracts_depends_on_triple_from_chunk():
    """
    Verify explicit depends-on text becomes a hard dependency triple.
    """
    chunk = build_chunk(
        "android-signing",
        "This plugin depends on the Jenkins Credentials Plugin for signing APKs.",
    )

    triples = extract_triples_from_chunk(chunk, build_aliases())

    assert len(triples) == 1
    assert triples[0].source.entity_id == "android-signing"
    assert triples[0].relation == GraphRelationType.DEPENDS_ON.value
    assert triples[0].target.entity_id == "credentials"
    assert triples[0].confidence == 0.9
    assert triples[0].evidence.source_chunk_id == "chunk-1"


def test_extracts_requires_triple_with_lower_confidence():
    """
    Verify requires text becomes a dependency triple with rule confidence.
    """
    chunk = build_chunk(
        "source-plugin",
        "This plugin requires the Port Allocator Plugin.",
    )

    triples = extract_triples_from_chunk(chunk, build_aliases())

    assert len(triples) == 1
    assert triples[0].relation == GraphRelationType.DEPENDS_ON.value
    assert triples[0].target.entity_id == "port-allocator"
    assert triples[0].confidence == 0.85


def test_extracts_optional_dependency_without_hard_dependency_duplicate():
    """
    Verify optional dependency text does not also emit a hard dependency.
    """
    chunk = build_chunk(
        "source-plugin",
        "This plugin optionally depends on the Git Plugin.",
    )

    triples = extract_triples_from_chunk(chunk, build_aliases())

    assert len(triples) == 1
    assert triples[0].relation == GraphRelationType.OPTIONAL_DEPENDS_ON.value
    assert triples[0].target.entity_id == "git"
    assert triples[0].confidence == 0.75


def test_extracts_conflict_triple_from_chunk():
    """
    Verify incompatibility text becomes a conflict triple.
    """
    chunk = build_chunk(
        "source-plugin",
        "This version is incompatible with Legacy Plugin.",
    )

    triples = extract_triples_from_chunk(chunk, build_aliases())

    assert len(triples) == 1
    assert triples[0].relation == GraphRelationType.CONFLICTS_WITH.value
    assert triples[0].target.entity_id == "legacy-plugin"
    assert triples[0].confidence == 0.8


def test_skips_unknown_source_plugin():
    """
    Verify chunks with unknown source titles do not emit triples.
    """
    chunk = build_chunk(
        "unknown-plugin",
        "This plugin depends on Git Plugin.",
    )

    assert not extract_triples_from_chunk(chunk, build_aliases())


def test_skips_self_relations():
    """
    Verify source-to-source relations are ignored.
    """
    chunk = build_chunk(
        "git",
        "The Git Plugin depends on Git Plugin.",
    )

    assert not extract_triples_from_chunk(chunk, build_aliases())


def test_skips_jenkins_as_target_plugin():
    """
    Verify Jenkins core requirements are not stored as plugin relations.
    """
    chunk = build_chunk(
        "source-plugin",
        "This plugin requires Jenkins.",
    )

    assert not extract_triples_from_chunk(chunk, build_aliases())


def test_deduplicates_identical_triples_inside_one_chunk():
    """
    Verify repeated identical evidence in one chunk is emitted once.
    """
    chunk = build_chunk(
        "source-plugin",
        "This plugin depends on Git Plugin. This plugin depends on Git Plugin.",
    )

    triples = extract_triples_from_chunk(chunk, build_aliases())

    assert len(triples) == 1
    assert triples[0].target.entity_id == "git"
