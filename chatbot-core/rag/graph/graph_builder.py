"""Build a plugin relation graph from extracted triples."""

import networkx as nx

from rag.graph.models import Triple
from rag.graph.triple_extractor import extract_triples


def add_triple_to_graph(graph: nx.MultiDiGraph, triple: Triple) -> None:
    """
    Add one validated triple to the graph.

    Args:
        graph (nx.MultiDiGraph): Graph artifact being built.
        triple (Triple): Validated relation to add.
    """
    graph.add_node(
        triple.source.entity_id,
        name=triple.source.name,
        entity_type=triple.source.entity_type,
    )
    graph.add_node(
        triple.target.entity_id,
        name=triple.target.name,
        entity_type=triple.target.entity_type,
    )
    graph.add_edge(
        triple.source.entity_id,
        triple.target.entity_id,
        relation=triple.relation,
        confidence=triple.confidence,
        source_chunk_id=triple.evidence.source_chunk_id,
        source_title=triple.evidence.source_title,
        source_data_source=triple.evidence.source_data_source,
        evidence=triple.evidence.evidence,
    )


def build_graph(triples: list[Triple]) -> nx.MultiDiGraph:
    """
    Build a MultiDiGraph from validated triples.

    Args:
        triples (list[Triple]): Validated triples ready for graph storage.

    Returns:
        nx.MultiDiGraph: Graph artifact with node and edge attributes.
    """
    graph = nx.MultiDiGraph()

    for triple in triples:
        add_triple_to_graph(graph, triple)

    return graph


def build_graph_from_chunks(
    chunks: list[dict],
    plugin_aliases: dict[str, str],
) -> tuple[nx.MultiDiGraph, list[Triple]]:
    """
    Extract triples from chunks and build a graph artifact.

    Args:
        chunks (list[dict]): Plugin documentation chunks.
        plugin_aliases (dict[str, str]): Alias map built from plugin IDs.

    Returns:
        tuple[nx.MultiDiGraph, list[Triple]]: Built graph and extracted triples.
    """
    triples = extract_triples(chunks, plugin_aliases)
    return build_graph(triples), triples
