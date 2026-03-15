"""
Utilities for loading the FAISS vector index and performing similarity search
to retrieve relevant document chunks based on a query vector.
"""

import os
import numpy as np
from rag.vectorstore.vectorstore_utils import load_faiss_index, load_metadata

VECTOR_STORE_DIR = os.path.join(os.path.dirname(
    __file__), "..", "..", "data", "embeddings")


def load_vector_index(logger, source_name):
    """
    Load the FAISS index and associated metadata from disk.
    """
    if not source_name.strip():
        logger.warning("No source name provided. Returning empty results.")
        return None, None

    index_path = os.path.join(VECTOR_STORE_DIR, f"{source_name}_index.idx")
    metadata_path = os.path.join(
        VECTOR_STORE_DIR, f"{source_name}_metadata.pkl")

    # This triggers our @lru_cache perfectly!
    index = load_faiss_index(index_path)
    metadata = load_metadata(metadata_path)

    return index, metadata


def search_index(query_vector, index, metadata, logger, top_k):
    """
    Search the FAISS index with a query vector and return the top-k closest metadata results.
    """
    if query_vector is None or not isinstance(query_vector, np.ndarray):
        logger.error("Invalid query vector received.")
        return [], []

    if index.ntotal == 0:
        logger.warning("FAISS index is empty. No search will be performed.")
        return [], []

    if index.ntotal != len(metadata):
        logger.warning(
            "Index contains %d vectors but metadata has %d entries."
            " Some results may be missing or inconsistent.",
            index.ntotal,
            len(metadata)
        )

    query_vector = np.array(query_vector).astype("float32").reshape(1, -1)
    distances, indices = index.search(query_vector, top_k)
    results = []

    for i in range(len(indices[0])):
        idx = indices[0][i]
        if idx < len(metadata):
            results.append({
                "metadata": metadata[idx],
                "score": float(distances[0][i])
            })
        else:
            logger.error("FAISS returned index %d out of range (metadata size: %d)",
                         idx,
                         len(metadata)
                         )

    data = []
    scores = []
    for result in results:
        data.append(result["metadata"])
        scores.append(result["score"])

    return data, scores
