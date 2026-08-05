"""Unit tests for GraphRAG deterministic triple extraction."""

from rag.graph.schema import GraphRelationType
from rag.graph.triple_extractor import (
    build_candidate_variants,
    build_plugin_lookup,
    extract_triples_from_chunk,
    extract_triples,
    is_changelog_span,
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
    plugin_lookup = build_plugin_lookup(plugin_ids)

    assert resolve_plugin_id("target-plugin", plugin_lookup) == "target-plugin"
    assert resolve_plugin_id("Target Plugin", plugin_lookup) == "target-plugin"
    assert resolve_plugin_id("Jenkins Credentials Plugin", plugin_lookup) == "credentials"
    assert resolve_plugin_id("not-a-plugin", plugin_lookup) is None


def test_bare_single_word_target_requires_plugin_wording():
    """
    Verify ambiguous single-word plugin names are not inferred as targets.
    """
    plugin_ids = build_plugin_ids()
    plugin_lookup = build_plugin_lookup(plugin_ids)

    assert not resolve_target_entities("Git", plugin_lookup)
    assert [
        target.entity_id
        for target in resolve_target_entities("Git Plugin", plugin_lookup)
    ] == ["git"]


def test_all_dependency_targets_require_plugin_wording():
    """
    Verify every dependency target uses explicit plugin wording.
    """
    plugin_ids = build_plugin_ids()
    plugin_lookup = build_plugin_lookup(plugin_ids)

    assert not resolve_target_entities("Job DSL", plugin_lookup)
    assert [
        target.entity_id
        for target in resolve_target_entities("Job DSL Plugin", plugin_lookup)
    ] == ["job-dsl"]


def test_hyphenated_plugin_names_accept_hyphen_and_space_forms():
    """
    Verify separator variants resolve to the same canonical plugin ID.
    """
    plugin_ids = build_plugin_ids()
    plugin_lookup = build_plugin_lookup(plugin_ids)

    assert [
        target.entity_id
        for target in resolve_target_entities("git-client plugin", plugin_lookup)
    ] == ["git-client"]
    assert [
        target.entity_id
        for target in resolve_target_entities("git client plugin", plugin_lookup)
    ] == ["git-client"]


def test_target_lookup_is_bounded_to_relation_local_context():
    """
    Verify target lookup does not scan an entire unrelated text span.
    """
    plugin_ids = build_plugin_ids()
    plugin_lookup = build_plugin_lookup(plugin_ids)
    distant_target = "noise " * 20 + "Git Client Plugin"

    assert not resolve_target_entities(distant_target, plugin_lookup)
    assert not resolve_target_entities(
        "Git Client Plugin " + "noise " * 20,
        plugin_lookup,
        scan_from_end=True,
    )


def test_underscore_plugin_names_accept_space_forms():
    """
    Verify underscore-separated IDs use the same readable-name matching.
    """
    targets = resolve_target_entities(
        "http request plugin",
        build_plugin_lookup(build_plugin_ids()),
    )

    assert [target.entity_id for target in targets] == ["http_request"]


def test_sentence_split_drops_empty_sentences():
    """
    Verify the sentence splitter returns useful text spans.
    """
    sentences = sentence_split("First sentence. Second sentence!  ")

    assert sentences == ["First sentence.", "Second sentence!"]


def test_sentence_split_preserves_soft_lines_and_structural_boundaries():
    """
    Verify soft plugin-name lines join while documentation sections split.
    """
    text = "\n".join(
        [
            "Requirements:",
            "This plugin depends on Git",
            "Client Plugin.",
            "",
            "[[CODE_BLOCK_0]]",
            "Changelog",
            "v1.2.0",
            "- Fixed a build issue.",
        ]
    )

    assert sentence_split(text) == [
        "Requirements:",
        "This plugin depends on Git Client Plugin.",
        "Changelog",
        "v1.2.0",
        "Fixed a build issue.",
    ]


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
        build_plugin_lookup(build_plugin_ids()),
        scan_from_end=True,
    )

    assert [target.entity_id for target in targets] == ["git", "credentials"]


def test_target_scan_keeps_targets_after_boundary_words():
    """
    Verify explanatory words do not hide a valid target plugin.
    """
    targets = resolve_target_entities(
        "support for the Kubernetes Plugin",
        build_plugin_lookup(build_plugin_ids()),
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
    assert triples[0].evidence.source_chunk_id == "chunk-1"


def test_rejects_unresolved_pronoun_relation_subject():
    """
    Verify unresolved pronouns do not create dependency relationships.
    """
    chunk = build_chunk(
        "source-plugin",
        "It depends on the Git Plugin.",
    )

    assert not extract_triples_from_chunk(chunk, build_plugin_ids())


def test_accepts_explicit_plugin_relation_subject():
    """
    Verify explicitly named source plugins create relationships.
    """
    chunk = build_chunk(
        "source-plugin",
        "Source Plugin depends on the Git Plugin.",
    )

    triples = extract_triples_from_chunk(chunk, build_plugin_ids())

    assert len(triples) == 1
    assert triples[0].target.entity_id == "git"


def test_filters_historical_changelog_dependency_spans():
    """
    Verify release-note dependency mentions are not extracted.
    """
    chunk = build_chunk(
        "source-plugin",
        "Fix: depends on the Git Plugin.",
    )

    assert is_changelog_span("Fix: depends on the Git Plugin.")
    assert not extract_triples_from_chunk(chunk, build_plugin_ids())


def test_preserves_direct_dependency_and_conflict_statements():
    """
    Verify current relationship statements remain extractable.
    """
    dependency = build_chunk("source-plugin", "Depends on the Job DSL Plugin.")
    conflict = build_chunk(
        "source-plugin",
        "This plugin is incompatible with the Git Plugin.",
    )

    assert not is_changelog_span("Depends on the Job DSL Plugin.")
    assert len(extract_triples_from_chunk(dependency, build_plugin_ids())) == 1
    assert len(extract_triples_from_chunk(conflict, build_plugin_ids())) == 1


def test_filters_spans_with_multiple_jenkins_issues():
    """
    Verify multiple issue references are treated as changelog noise.
    """
    text = "JENKINS-123 JENKINS-456 depends on the Git Plugin."

    assert is_changelog_span(text)


def test_deduplicates_relationships_across_chunks():
    """
    Verify one preferred triple is emitted for repeated chunk relationships.
    """
    chunks = [
        build_chunk(
            "source-plugin",
            "This plugin depends on the Git Plugin.",
            chunk_id="chunk-long",
        ),
        build_chunk(
            "source-plugin",
            "Depends on Git Plugin.",
            chunk_id="chunk-short",
        ),
    ]

    triples = extract_triples(chunks, build_plugin_ids())

    assert len(triples) == 1
    assert triples[0].evidence.source_chunk_id == "chunk-short"


def test_extracts_requires_triple():
    """
    Verify requires text becomes a dependency triple.
    """
    chunk = build_chunk(
        "source-plugin",
        "This plugin requires the Port Allocator Plugin.",
    )

    triples = extract_triples_from_chunk(chunk, build_plugin_ids())

    assert len(triples) == 1
    assert triples[0].relation == GraphRelationType.DEPENDS_ON.value
    assert triples[0].target.entity_id == "port-allocator"


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


def test_preceding_target_is_included_in_dependency_evidence():
    """
    Verify preceding-span target resolution keeps complete evidence.
    """
    chunk = build_chunk(
        "source-plugin",
        "Git Client Plugin. This plugin optionally depends on it.",
    )

    triples = extract_triples_from_chunk(chunk, build_plugin_ids())

    assert len(triples) == 1
    assert triples[0].target.entity_id == "git-client"
    assert triples[0].evidence.evidence == (
        "Git Client Plugin. This plugin optionally depends on it."
    )


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
