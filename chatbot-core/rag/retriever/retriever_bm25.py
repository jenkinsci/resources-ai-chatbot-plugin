"""
Query interface for retrieving the most relevant embedded text chunks using a Sparse Retriever.
"""

from rag.retriever.retriever_utils import load_vector_index
from rag.embedding.bm25_indexer import indexer


def perform_keyword_search_from_source(query, logger, source_name, keyword_threshold, top_k=5):
    """
    Convenience wrapper for performing a keyword-based search using a given source name.
    This function handles retrieving the index and metadata internally.

    Args:
        query (str): The input query string.
        logger (logging.Logger): Logger for warnings and updates.
        source_name (str): The source name that we want to consider.
        keyword_threshold (float): Minimum score required to keep a result.
        top_k (int, optional): Number of top results to retrieve. Defaults to 5.

    Returns:
        list[dict]: A list of dictionaries, each containing a retrieved chunk and its score.
    """
    index = indexer.get(source_name)
    _, metadata = load_vector_index(logger, source_name)
    if not index or not metadata:
        return []
    return perform_keyword_search(query, logger, index, metadata, keyword_threshold, top_k)

# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
def perform_keyword_search(query, logger, index, metadata, keyword_threshold, top_k=5):
    """
    Retrieve the top-k most relevant chunks for a given natural language query
    using a provided keyword-based index and metadata.

    Args:
        query (str): The input query string.
        logger (logging.Logger): Logger for warnings and updates.
        index (SparseRetriever): The built keyword-based index to search.
        metadata (list[dict]): Metadata entries associated with each stored vector.
        keyword_threshold (float): Minimum score required to keep a result.
        top_k (int, optional): Number of top results to retrieve. Defaults to 5.

    Returns:
        list[dict]: A list of dictionaries, each containing a retrieved chunk and its score.
    """
    if not query.strip():
        logger.warning("Empty query received.")
        return []
    data, scores = search_bm25_index(query, index, metadata, logger, top_k)
    return [
        {"chunk": d, "score": s}
        for d, s in zip(data, scores)
        if s >= keyword_threshold
    ]

def search_bm25_index(query, index, metadata, logger, top_k):
    """
    Perform the effective sparse research, using a sparse retriever.

    Args:
        query (str): The input query string.
        index (SparseRetriever): The built index on which we're searching.
        metadata (List[dict]): Metadata entries associated with each stored vector.
        logger (logging.Logger): Logger for warnings and file-level updates.
        top_k (int): Number of top results to retrieve.
    
    Returns:
        tuple[list[dict], list[float]]: Retrieved data and similarity scores.
    """
    search_results, scores = [], []
    metadata_by_id = {item["id"]: item for item in metadata}
    relevant_chunks = index.search(
        query=query,
        return_docs=True,
        cutoff=top_k,
    )

    for chunk in relevant_chunks:
        scores.append(chunk["score"])
        match = metadata_by_id.get(chunk["id"])
        if match:
            search_results.append(match)
        else:
            logger.warning("No metadata found for chunk ID: %s", chunk["id"])

    return search_results, scores
