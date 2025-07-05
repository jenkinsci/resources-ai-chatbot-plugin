"""
Utilities for loading the FAISS vector index and performing similarity search
to retrieve relevant document chunks based on a query vector.
"""

import os
import numpy as np
from rag.vectorstore.vectorstore_utils import load_faiss_index, load_metadata

VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "embeddings")
INDEX_PATH = os.path.join(VECTOR_STORE_DIR, "faiss_index.idx")
METADATA_PATH = os.path.join(VECTOR_STORE_DIR, "faiss_metadata.pkl")

def load_vector_index(logger):
    """
    Load the FAISS index and associated metadata from disk.

    Args:
        logger (logging.Logger): Logger for status and error messages.

    Returns:
        Tuple[faiss.Index, list]: The FAISS index and corresponding metadata list.
    """
    index = load_faiss_index(INDEX_PATH, logger)
    metadata = load_metadata(METADATA_PATH, logger)

    return index, metadata

def search_index(query_vector, index, metadata, logger, top_k):
    """
    Search the FAISS index with a query vector and return the top-k closest metadata results.

    Args:
        query_vector (np.ndarray): A single embedding vector.
        index (faiss.Index): A trained and populated FAISS index.
        metadata (List[dict]): Metadata entries associated with each stored vector.
        top_k (int): Number of nearest neighbors to retrieve.

    Returns:
        List[dict]: A list of metadata entries with similarity scores.
    """
    if query_vector is None or not isinstance(query_vector, np.ndarray):
        logger.error("Invalid query vector received.")
        return [], []

    if index.ntotal == 0:
        logger.warning("FAISS index is empty. No search will be performed.")
        return [], []

    if index.ntotal != len(metadata):
        logger.warning(
            "Index contains %d vectors but metadata has %d entries." \
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
