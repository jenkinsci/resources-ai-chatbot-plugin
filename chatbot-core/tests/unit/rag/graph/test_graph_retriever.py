"""Unit tests for GraphRAG retrieval and context formatting."""

import networkx as nx

from rag.graph.entity_normalizer import build_plugin_aliases
from rag.graph.graph_retriever import retrieve_graph_relations
from rag.graph.hybrid_context import build_chunk_lookup, format_graph_retrieval_result
from rag.graph.query_parser import detect_graph_query_intent, parse_graph_query
from rag.graph.schema import GraphEntityType, GraphRelationType


PLUGIN_IDS = ("blueocean", "git", "workflow", "legacy-plugin")
PLUGIN_ALIASES = build_plugin_aliases(PLUGIN_IDS)
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
            confidence=0.9,
    )
    return graph


def test_detect_graph_query_intents():
    """Verify dependency, reverse dependency, conflict, and multi-hop intents."""
    dependency = detect_graph_query_intent("What does Blue Ocean depend on?")
    reverse = detect_graph_query_intent("Which plugins depend on Git Plugin?")
    conflict = detect_graph_query_intent("Which plugins conflict with Legacy Plugin?")
    multi_hop = detect_graph_query_intent("Show indirect dependencies of Blue Ocean")

    assert dependency.direction == "outgoing"
    assert reverse.direction == "incoming"
    assert conflict.direction == "both"
    assert multi_hop.traversal_depth == 2


def test_parse_graph_query_resolves_alias_entity():
    """Verify human plugin names resolve to canonical graph node IDs."""
    query_match = parse_graph_query(
        "What does Blue Ocean depend on?",
        PLUGIN_ALIASES,
    )
    assert query_match.query_entity == "Blue Ocean"
    assert query_match.matched_entity.entity_id == "blueocean"
    assert query_match.intent.direction == "outgoing"


def test_retrieve_graph_relations_handles_dependency_directions():
    """Verify outgoing and incoming dependency traversal."""
    graph = build_test_graph()
    outgoing = retrieve_graph_relations(
        "What does Blue Ocean depend on?",
        PLUGIN_ALIASES,
        graph,
    )
    incoming = retrieve_graph_relations(
        "Which plugins depend on Git Plugin?",
        PLUGIN_ALIASES,
        graph,
    )
    assert [relation.target.entity_id for relation in outgoing.relations] == ["git"]
    assert sorted(relation.source.entity_id for relation in incoming.relations) == [
        "blueocean",
        "workflow",
    ]


def test_retrieve_graph_relations_handles_conflicts_and_fallback():
    """Verify conflict traversal works and normal how-to queries do not activate."""
    graph = build_test_graph()
    conflict = retrieve_graph_relations(
        "Which plugins conflict with Legacy Plugin?",
        PLUGIN_ALIASES,
        graph,
    )
    assert conflict.relations[0].source.entity_id == "blueocean"
    assert conflict.relations[0].target.entity_id == "legacy-plugin"
    assert retrieve_graph_relations(
        "How do I configure Blue Ocean?",
        PLUGIN_ALIASES,
        graph,
    ) is None


def test_format_graph_retrieval_result_includes_source_chunk_context():
    """Verify graph context includes relation evidence and source chunk text."""
    result = retrieve_graph_relations(
        "What does Blue Ocean depend on?",
        PLUGIN_ALIASES,
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
