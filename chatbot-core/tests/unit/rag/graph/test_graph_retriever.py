"""Unit tests for GraphRAG retrieval and context formatting."""

import networkx as nx

from rag.graph.graph_retriever import retrieve_graph_relations
from rag.graph.hybrid_context import (
    MAX_GRAPH_CONTEXT_RELATIONS,
    build_chunk_lookup,
    format_graph_retrieval_result,
)
from rag.graph.models import GraphRetrievalResult
from rag.graph.query_parser import (
    detect_graph_relation_types,
    normalize_graph_query,
    parse_graph_query,
    resolve_query_entities,
)
from rag.graph.schema import GraphEntityType, GraphRelationType
from rag.graph.triple_extractor import build_plugin_lookup


PLUGIN_IDS = ("blueocean", "git", "workflow", "legacy-plugin")
PLUGIN_LOOKUP = build_plugin_lookup(PLUGIN_IDS)
TEST_EDGES = (
    (
        "blueocean",
        "git",
        GraphRelationType.DEPENDS_ON.value,
        "chunk-blue-git",
        "Blue Ocean depends on Git.",
    ),
    (
        "workflow",
        "git",
        GraphRelationType.OPTIONAL_DEPENDS_ON.value,
        "chunk-workflow-git",
        "Workflow optionally depends on Git.",
    ),
    (
        "blueocean",
        "legacy-plugin",
        GraphRelationType.CONFLICTS_WITH.value,
        "chunk-blue-legacy",
        "Blue Ocean conflicts with Legacy Plugin.",
    ),
)


def build_test_graph() -> nx.MultiDiGraph:
    """Build a small plugin relation graph for retriever tests."""
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(
        (
            plugin_id,
            {"name": plugin_id, "entity_type": GraphEntityType.PLUGIN.value},
        )
        for plugin_id in PLUGIN_IDS
    )

    for source, target, relation, chunk_id, evidence in TEST_EDGES:
        graph.add_edge(
            source,
            target,
            relation=relation,
            source_chunk_id=chunk_id,
            source_title=source,
            source_data_source="jenkins_plugins_documentation",
            evidence=evidence,
    )
    return graph


def test_detect_graph_relation_types_without_direction():
    """Verify relation-family detection remains independent of plan building."""
    dependency_query = "Which plugins depend on Git Plugin?"
    conflict_query = "Which plugins conflict with Legacy Plugin?"

    assert detect_graph_relation_types(dependency_query) == (
        "DEPENDS_ON",
        "OPTIONAL_DEPENDS_ON",
    )
    assert detect_graph_relation_types(conflict_query) == ("CONFLICTS_WITH",)


def test_normalize_graph_query_wording():
    """Verify graph-query formatting is normalized without changing meaning."""
    assert normalize_graph_query(
        "  Which  PLUG-INS are dependent upon Credentials?!  "
    ) == "which plugins are dependent upon credentials"
    assert normalize_graph_query(
        "What are Git\u2019s dependencies?"
    ) == "what are git's dependencies"
    assert normalize_graph_query(
        "Which plugins rely upon Credentials?"
    ) == "which plugins rely upon credentials"
    assert normalize_graph_query(
        "Does Git-Client depend upon Credentials?"
    ) == "does git-client depend upon credentials"


def test_parse_graph_query_resolves_alias_entity():
    """Verify human plugin names resolve to canonical graph node IDs."""
    plan = parse_graph_query(
        "What does Blue Ocean depend on?",
        PLUGIN_LOOKUP,
    )
    assert plan.source_entity.entity_id == "blueocean"
    assert plan.direction == "outgoing"
    assert plan.matched_rule == "dependency_by_position"


def test_parse_graph_query_keeps_multi_entity_roles_unassigned():
    """Verify pairwise entities are assigned directly by their positions."""
    plan = parse_graph_query(
        "Does Blue Ocean depend on Git?",
        PLUGIN_LOOKUP,
    )

    assert plan.direction == "pairwise"
    assert plan.source_entity.entity_id == "blueocean"
    assert plan.target_entity.entity_id == "git"


def test_resolve_query_entities_preserves_multiple_plugin_spans():
    """Verify all known plugins are resolved with positions in the raw query."""
    query = "Can CloverPHP be installed with Clover?"
    plugin_lookup = build_plugin_lookup(("cloverphp", "clover"))

    entities = resolve_query_entities(query, plugin_lookup)

    assert [entity.entity.entity_id for entity in entities] == [
        "cloverphp",
        "clover",
    ]
    assert [query[entity.start : entity.end] for entity in entities] == [
        "CloverPHP",
        "Clover",
    ]
    assert all(entity.start < entity.end for entity in entities)


def test_retrieve_graph_relations_handles_dependency_directions():
    """Verify outgoing and incoming dependency traversal."""
    graph = build_test_graph()
    outgoing = retrieve_graph_relations(
        "What does Blue Ocean depend on?",
        PLUGIN_LOOKUP,
        graph,
    )
    incoming = retrieve_graph_relations(
        "Which plugins depend on Git Plugin?",
        PLUGIN_LOOKUP,
        graph,
    )
    assert [relation.target.entity_id for relation in outgoing.relations] == ["git"]
    assert sorted(relation.source.entity_id for relation in incoming.relations) == [
        "blueocean",
        "workflow",
    ]


def test_retrieve_graph_relations_always_returns_list_context():
    """Return graph relations regardless of wording that implies an answer shape."""
    graph = build_test_graph()

    list_result = retrieve_graph_relations(
        "Which plugins depend on Git Plugin?",
        PLUGIN_LOOKUP,
        graph,
    )
    boolean_result = retrieve_graph_relations(
        "Does Blue Ocean depend on Git?",
        PLUGIN_LOOKUP,
        graph,
    )
    count_result = retrieve_graph_relations(
        "How many plugins depend on Git Plugin?",
        PLUGIN_LOOKUP,
        graph,
    )

    assert sorted(relation.source.entity_id for relation in list_result.relations) == [
        "blueocean",
        "workflow",
    ]
    assert [
        (relation.source.entity_id, relation.target.entity_id)
        for relation in boolean_result.relations
    ] == [("blueocean", "git")]
    assert sorted(relation.source.entity_id for relation in count_result.relations) == [
        "blueocean",
        "workflow",
    ]


def test_retrieve_graph_relations_handles_conflicts_and_fallback():
    """Verify conflict traversal works and normal how-to queries do not activate."""
    graph = build_test_graph()
    conflict = retrieve_graph_relations(
        "Does Blue Ocean conflict with Legacy Plugin?",
        PLUGIN_LOOKUP,
        graph,
    )
    assert conflict.relations[0].source.entity_id == "blueocean"
    assert conflict.relations[0].target.entity_id == "legacy-plugin"
    assert retrieve_graph_relations(
        "How do I configure Blue Ocean?",
        PLUGIN_LOOKUP,
        graph,
    ) is None


def test_retrieve_graph_relations_honors_pairwise_order():
    """Return only the ordered dependency edge requested by a pairwise plan."""
    graph = build_test_graph()
    graph.add_edge(
        "git",
        "blueocean",
        relation=GraphRelationType.DEPENDS_ON.value,
        source_chunk_id="chunk-git-blue",
        source_title="Git",
        source_data_source="jenkins_plugins_documentation",
        evidence="Git depends on Blue Ocean.",
    )

    result = retrieve_graph_relations(
        "Does Blue Ocean depend on Git?",
        PLUGIN_LOOKUP,
        graph,
    )

    assert [(item.source.entity_id, item.target.entity_id) for item in result.relations] == [
        ("blueocean", "git")
    ]


def test_retrieve_graph_relations_honors_depth_and_relation_filter():
    """Apply multi-hop depth and required-versus-optional edge filters."""
    indirect_graph = build_test_graph()
    indirect_graph.add_edge(
        "git",
        "workflow",
        relation=GraphRelationType.DEPENDS_ON.value,
        source_chunk_id="chunk-git-workflow",
        source_title="Git",
        source_data_source="jenkins_plugins_documentation",
        evidence="Git depends on Workflow.",
    )
    required_graph = build_test_graph()
    required_graph.add_edge(
        "blueocean",
        "workflow",
        relation=GraphRelationType.OPTIONAL_DEPENDS_ON.value,
        source_chunk_id="chunk-blue-workflow",
        source_title="Blue Ocean",
        source_data_source="jenkins_plugins_documentation",
        evidence="Blue Ocean optionally depends on Workflow.",
    )

    indirect = retrieve_graph_relations(
        "What does Blue Ocean indirectly depend on?",
        PLUGIN_LOOKUP,
        indirect_graph,
    )
    required = retrieve_graph_relations(
        "What does Blue Ocean require?",
        PLUGIN_LOOKUP,
        required_graph,
    )

    assert indirect.traversal_depth == 2
    assert [
        (item.source.entity_id, item.target.entity_id)
        for item in indirect.relations
    ] == [("blueocean", "git"), ("git", "workflow")]
    assert [item.relation for item in required.relations] == [
        GraphRelationType.DEPENDS_ON.value
    ]


def test_retrieve_graph_relations_treats_conflicts_as_symmetric():
    """Match a conflict when the stored edge is reversed from the query."""
    graph = build_test_graph()
    graph.remove_edge("blueocean", "legacy-plugin", key=0)
    graph.add_edge(
        "legacy-plugin",
        "blueocean",
        relation=GraphRelationType.CONFLICTS_WITH.value,
        source_chunk_id="chunk-legacy-blue",
        source_title="Legacy Plugin",
        source_data_source="jenkins_plugins_documentation",
        evidence="Legacy Plugin conflicts with Blue Ocean.",
    )

    result = retrieve_graph_relations(
        "Does Blue Ocean conflict with Legacy Plugin?",
        PLUGIN_LOOKUP,
        graph,
    )

    assert len(result.relations) == 1
    assert {
        result.relations[0].source.entity_id,
        result.relations[0].target.entity_id,
    } == {"blueocean", "legacy-plugin"}


def test_format_graph_retrieval_result_includes_source_chunk_context():
    """Verify graph context includes relation evidence and source chunk text."""
    result = retrieve_graph_relations(
        "What does Blue Ocean depend on?",
        PLUGIN_LOOKUP,
        build_test_graph(),
    )
    chunk_lookup = build_chunk_lookup(
        [
            {
                "id": "chunk-blue-git",
                "chunk_text": "Blue Ocean depends on Git. Extra setup detail.",
            }
        ]
    )
    context = format_graph_retrieval_result(result, chunk_lookup=chunk_lookup)

    assert "blueocean DEPENDS_ON git." in context
    assert "Evidence: Blue Ocean depends on Git." in context
    assert "Context:\nBlue Ocean depends on Git. Extra setup detail." in context
    assert "Source Chunk ID: chunk-blue-git" in context


def test_format_graph_retrieval_result_limits_prompt_relations():
    """Limit prompt context while retaining the complete retrieval result."""
    relation = retrieve_graph_relations(
        "What does Blue Ocean depend on?",
        PLUGIN_LOOKUP,
        build_test_graph(),
    ).relations[0]
    result = GraphRetrievalResult(
        query_entity="blueocean",
        matched_entity_id="blueocean",
        relations=(relation,) * (MAX_GRAPH_CONTEXT_RELATIONS + 1),
    )

    context = format_graph_retrieval_result(result)

    assert (
        f"Graph results are limited to the first {MAX_GRAPH_CONTEXT_RELATIONS} "
        f"of {MAX_GRAPH_CONTEXT_RELATIONS + 1} relations."
    ) in context
    assert context.count("[Source: plugin_relation_graph]") == MAX_GRAPH_CONTEXT_RELATIONS
