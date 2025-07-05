"""
Query interface for retrieving the most relevant embedded text chunks using a FAISS vector index.
"""

from rag.embedding.embedding_utils import embed_documents
from rag.retriever.retriever_utils import load_vector_index, search_index

def get_relevant_documents(query, model, logger, top_k=5):
    """
    Retrieve the top-k most relevant chunks for a given natural language query.

    Args:
        query (str): The input query string.
        model (SentenceTransformer): A loaded SentenceTransformer model.
        logger (logging.Logger): Logger for warnings and file-level updates.
        top_k (int): Number of top results to retrieve. Defaults to 5.

    Returns:
        tuple[list[dict], list[float]]: Retrieved metadata and similarity scores.
    """
    if not query.strip():
        logger.warning("Empty query received.")
        return [], []

    index, metadata = load_vector_index(logger)

    if not index or not metadata:
        return [], []

    query_vector = embed_documents([query], model, logger)[0]
    data, scores = search_index(query_vector, index, metadata, logger, top_k)

    return data, scores
