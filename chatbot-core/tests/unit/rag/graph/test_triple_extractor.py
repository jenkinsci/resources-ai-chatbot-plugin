"""Unit tests for GraphRAG deterministic triple extraction."""

from rag.graph.schema import GraphRelationType
from rag.graph.triple_extractor import (
    build_candidate_variants,
    extract_triples_from_chunk,
    resolve_plugin_id,
    resolve_target_entities,
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


def build_plugin_ids() -> set[str]:
    """
    Build canonical plugin IDs used by extractor tests.

    Returns:
        set[str]: Canonical plugin IDs.
    """
    return {
        "android-signing",
        "blueocean",
        "credentials",
        "git",
        "git-client",
        "http_request",
        "job-dsl",
        "junit",
        "legacy-plugin",
        "port-allocator",
        "kubernetes",
        "source-plugin",
        "target-plugin",
        "jenkins",
    }


def test_resolve_plugin_id_matches_canonical_documentation_forms():
    """
    Verify matching is derived from canonical IDs rather than alias metadata.
    """
    plugin_ids = build_plugin_ids()

    assert resolve_plugin_id("target-plugin", plugin_ids) == "target-plugin"
    assert resolve_plugin_id("Target Plugin", plugin_ids) == "target-plugin"
    assert resolve_plugin_id("Jenkins Credentials Plugin", plugin_ids) == "credentials"
    assert resolve_plugin_id("not-a-plugin", plugin_ids) is None


def test_bare_single_word_target_requires_plugin_wording():
    """
    Verify ambiguous single-word plugin names are not inferred as targets.
    """
    plugin_ids = build_plugin_ids()

    assert not resolve_target_entities("Git", plugin_ids)
    assert [
        target.entity_id
        for target in resolve_target_entities("Git Plugin", plugin_ids)
    ] == ["git"]


def test_all_dependency_targets_require_plugin_wording():
    """
    Verify every dependency target uses explicit plugin wording.
    """
    plugin_ids = build_plugin_ids()

    assert not resolve_target_entities("Job DSL", plugin_ids)
    assert [
        target.entity_id
        for target in resolve_target_entities("Job DSL Plugin", plugin_ids)
    ] == ["job-dsl"]


def test_hyphenated_plugin_names_accept_hyphen_and_space_forms():
    """
    Verify separator variants resolve to the same canonical plugin ID.
    """
    plugin_ids = build_plugin_ids()

    assert [
        target.entity_id
        for target in resolve_target_entities("git-client plugin", plugin_ids)
    ] == ["git-client"]


def test_underscore_plugin_names_accept_space_forms():
    """
    Verify underscore-separated IDs use the same readable-name matching.
    """
    targets = resolve_target_entities("http request plugin", build_plugin_ids())

    assert [target.entity_id for target in targets] == ["http_request"]
    assert [
        target.entity_id
        for target in resolve_target_entities("git client plugin", plugin_ids)
    ] == ["git-client"]


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


def test_reverse_target_scan_returns_targets_in_text_order():
    """
    Verify reverse scans return all targets in normal text order.
    """
    targets = resolve_target_entities(
        "Git Plugin and Credentials Plugin",
        build_plugin_ids(),
        scan_from_end=True,
    )

    assert [target.entity_id for target in targets] == ["git", "credentials"]


def test_target_scan_keeps_targets_after_boundary_words():
    """
    Verify explanatory words do not hide a valid target plugin.
    """
    targets = resolve_target_entities(
        "support for the Kubernetes Plugin",
        build_plugin_ids(),
    )

    assert [target.entity_id for target in targets] == ["kubernetes"]


def test_extracts_depends_on_triple_from_chunk():
    """
    Verify explicit depends-on text becomes a hard dependency triple.
    """
    chunk = build_chunk(
        "android-signing",
        "This plugin depends on the Jenkins Credentials Plugin for signing APKs.",
    )

    triples = extract_triples_from_chunk(chunk, build_plugin_ids())

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

    triples = extract_triples_from_chunk(chunk, build_plugin_ids())

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

    triples = extract_triples_from_chunk(chunk, build_plugin_ids())

    assert len(triples) == 1
    assert triples[0].relation == GraphRelationType.OPTIONAL_DEPENDS_ON.value
    assert triples[0].target.entity_id == "git"
    assert triples[0].confidence == 0.75


def test_extracts_optional_target_before_relation_phrase():
    """
    Verify optional dependencies can resolve a target before the relation.
    """
    chunk = build_chunk(
        "source-plugin",
        "The Git Plugin is an optional dependency for this plugin.",
    )

    triples = extract_triples_from_chunk(chunk, build_plugin_ids())

    assert len(triples) == 1
    assert triples[0].relation == GraphRelationType.OPTIONAL_DEPENDS_ON.value
    assert triples[0].target.entity_id == "git"


def test_extracts_conflict_triple_from_chunk():
    """
    Verify incompatibility text becomes a conflict triple.
    """
    chunk = build_chunk(
        "source-plugin",
        "This version is incompatible with Legacy Plugin.",
    )

    triples = extract_triples_from_chunk(chunk, build_plugin_ids())

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

    assert not extract_triples_from_chunk(chunk, build_plugin_ids())


def test_skips_self_relations():
    """
    Verify source-to-source relations are ignored.
    """
    chunk = build_chunk(
        "git",
        "The Git Plugin depends on Git Plugin.",
    )

    assert not extract_triples_from_chunk(chunk, build_plugin_ids())


def test_skips_jenkins_as_target_plugin():
    """
    Verify Jenkins core requirements are not stored as plugin relations.
    """
    chunk = build_chunk(
        "source-plugin",
        "This plugin requires Jenkins.",
    )

    assert not extract_triples_from_chunk(chunk, build_plugin_ids())


def test_deduplicates_identical_triples_inside_one_chunk():
    """
    Verify repeated identical evidence in one chunk is emitted once.
    """
    chunk = build_chunk(
        "source-plugin",
        "This plugin depends on Git Plugin. This plugin depends on Git Plugin.",
    )

    triples = extract_triples_from_chunk(chunk, build_plugin_ids())

    assert len(triples) == 1
    assert triples[0].target.entity_id == "git"
