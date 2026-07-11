"""Format graph retrieval results as prompt-ready retrieval context."""

from rag.graph.models import GraphRelation, GraphRetrievalResult


def format_graph_relation(relation: GraphRelation) -> str:
    """
    Format one graph relation as compact retrieval context.

    Args:
        relation (GraphRelation): Graph relation returned by traversal.

    Returns:
        str: Prompt-ready graph relation block.
    """
    return (
        "[Source: plugin_relation_graph]\n"
        f"{relation.source.name} {relation.relation} {relation.target.name}.\n"
        f"Evidence: {relation.evidence.evidence}\n"
        f"Context: source_chunk_id={relation.evidence.source_chunk_id}"
    )


def format_graph_retrieval_result(result: GraphRetrievalResult) -> str:
    """
    Format a graph retrieval result as compact retrieval context.

    Args:
        result (GraphRetrievalResult): Graph retrieval output to format.

    Returns:
        str: Prompt-ready context built from graph relations.
    """
    if not result.relations:
        return ""

    relation_blocks = [
        format_graph_relation(relation)
        for relation in result.relations
    ]
    return "\n\n".join(relation_blocks)
