"""
Query interface for retrieving the most relevant embedded text chunks using a FAISS vector index.
"""

from rag.embedding.embedding_utils import embed_documents
from rag.retriever.retriever_utils import load_vector_index, search_index
from api.config.loader import CONFIG


def get_relevant_documents(query, model, logger, source_name, top_k=5):
    if not query.strip():
        logger.warning("Empty query received.")
        return [], []

    # Python's @lru_cache handles all the caching silently behind the scenes!
    index, metadata = load_vector_index(logger, source_name)

    if not index or not metadata:
        logger.error("Database is missing. Retrieval disabled.")
        return [], []

    query_vector = embed_documents([query], model, logger)[0]
    data, scores = search_index(query_vector, index, metadata, logger, top_k)

    filtered = [(d, s) for d, s in zip(data, scores)
                if s <= CONFIG["retrieval"]["semantic_threshold"]]
    filtered_data, filtered_scores = zip(*filtered) if filtered else ([], [])

    return list(filtered_data), list(filtered_scores)
