"""Build a plugin relation graph from extracted triples."""

import networkx as nx

from rag.graph.models import Triple
from rag.graph.triple_extractor import extract_triples


def build_node_records(triples: list[Triple]) -> list[tuple[str, dict[str, str]]]:
    """
    Build node rows for graph insertion.

    Args:
        triples (list[Triple]): Validated triples ready for graph storage.

    Returns:
        list[tuple[str, dict[str, str]]]: Node rows for add_nodes_from().
    """
    node_records: dict[str, dict[str, str]] = {}

    for triple in triples:
        node_records[triple.source.entity_id] = {
            "name": triple.source.name,
            "entity_type": triple.source.entity_type,
        }
        node_records[triple.target.entity_id] = {
            "name": triple.target.name,
            "entity_type": triple.target.entity_type,
        }

    return list(node_records.items())


def build_edge_records(
    triples: list[Triple],
) -> list[tuple[str, str, dict[str, str | float]]]:
    """
    Build edge rows for graph insertion.

    Args:
        triples (list[Triple]): Validated triples ready for graph storage.

    Returns:
        list[tuple[str, str, dict[str, str | float]]]: Edge rows for add_edges_from().
    """
    return [
        (
            triple.source.entity_id,
            triple.target.entity_id,
            {
                "relation": triple.relation,
                "confidence": triple.confidence,
                "source_chunk_id": triple.evidence.source_chunk_id,
                "source_title": triple.evidence.source_title,
                "source_data_source": triple.evidence.source_data_source,
                "evidence": triple.evidence.evidence,
            },
        )
        for triple in triples
    ]


def build_graph(triples: list[Triple]) -> nx.MultiDiGraph:
    """
    Build a MultiDiGraph from validated triples.

    Args:
        triples (list[Triple]): Validated triples ready for graph storage.

    Returns:
        nx.MultiDiGraph: Graph artifact with node and edge attributes.
    """
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(build_node_records(triples))
    graph.add_edges_from(build_edge_records(triples))

    return graph


def build_graph_from_chunks(
    chunks: list[dict],
    plugin_aliases: dict[str, str],
) -> tuple[nx.MultiDiGraph, list[Triple]]:
    """
    Extract triples from chunks and build the graph artifact.

    Args:
        chunks (list[dict]): Plugin documentation chunks.
        plugin_aliases (dict[str, str]): Alias map built from plugin IDs.

    Returns:
        tuple[nx.MultiDiGraph, list[Triple]]: Built graph and extracted triples.
    """
    triples = extract_triples(chunks, plugin_aliases)
    return build_graph(triples), triples
