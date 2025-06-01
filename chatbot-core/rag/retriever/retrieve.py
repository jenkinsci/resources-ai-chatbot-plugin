"""
Query interface for retrieving the most relevant embedded text chunks using a FAISS vector index.
"""

from rag.embedding.embedding_utils import load_embedding_model, embed_documents
from rag.retriever.retriever_utils import load_vector_index, search_index
from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("retrieve")

def get_relevant_documents(query, top_k=5):
    """
    Retrieve the top-k most relevant chunks for a given natural language query.

    Args:
        query (str): The input query string.
        top_k (int): Number of top results to retrieve. Defaults to 5.

    Returns:
        list[dict]: A list of metadata entries corresponding to the most relevant chunks.
    """
    model = load_embedding_model()
    index, metadata = load_vector_index(logger)

    if not index or not metadata:
        return []

    query_vector = embed_documents([query], model)[0]
    results = search_index(query_vector, index, metadata, top_k=top_k)

    return results
