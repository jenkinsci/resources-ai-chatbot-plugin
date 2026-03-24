"""
Embeds document chunks, builds a FAISS IVF index,
and stores both the index and associated metadata to disk.
"""

import os
import numpy as np
import faiss
from rag.embedding import embed_chunks
from rag.vectorstore.vectorstore_utils import save_faiss_index, save_metadata
from utils import LoggerFactory

VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "embeddings")
INDEX_PATH = os.path.join(VECTOR_STORE_DIR, "plugins_index.idx")
METADATA_PATH = os.path.join(VECTOR_STORE_DIR, "plugins_metadata.pkl")

N_LIST = 256
N_PROBE = 20


def build_faiss_ivf_index(vectors, nlist, nprobe, logger):

    """
    Build and return a FAISS IndexIVFFlat index from the given vectors.

    Args:
        vectors (np.ndarray): 2D array of shape (n_samples, dim) with float32 vectors.
        nlist (int): Number of clusters (centroids) to use in the index.
        nprobe (int): Number of clusters to probe during a search.
        logger (logging.Logger): Logger for status messages.

    Returns:
        faiss.IndexIVFFlat: A trained FAISS IVF index with added vectors.
    """

    if not isinstance(vectors, np.ndarray):
        raise TypeError("Vectors must be an instance of numpy.ndarray.")
    if vectors.ndim != 2:
        raise ValueError(f"Vectors must be 2D, got shape {vectors.shape}.")
    if vectors.dtype != np.float32:
        raise TypeError(f"Vectors must be float32, got dtype {vectors.dtype}.")

    d = vectors.shape[1]
    n_samples = vectors.shape[0]

    # --- ARCHITECTURAL FIX START ---
    # Determine the index type based on dataset size
    if n_samples < nlist:
        logger.warning(
        "Dataset size (%d) is smaller than nlist (%d). Falling back to IndexFlatL2.",
        n_samples, nlist
        )
        # Flat index doesn't need training
        index = faiss.IndexFlatL2(d)
    else:
        quantizer = faiss.IndexFlatL2(d)
        index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_L2)
        
        # Only train if the index requires it and isn't trained yet
        if not index.is_trained:
            logger.info("FAISS index training started...")
            index.train(vectors)
            logger.info("FAISS index training completed.")
        
        # Set nprobe only for IVF indices
        index.nprobe = nprobe
    # --- ARCHITECTURAL FIX END ---

    index.add(vectors) 
    return index


def run_indexing(nlist, nprobe, logger):
    """
    Main pipeline: embed documents, build FAISS index, and save index + metadata.

    Args:
        nlist (int): Number of clusters for FAISS IVF index.
        nprobe (int): Number of clusters to search during queries.
    """
    logger.info("Starting document embedding...")
    vectors, metadata = embed_chunks(logger)
    vectors_np = np.array(vectors).astype("float32")

    index = build_faiss_ivf_index(vectors_np, nlist=nlist, nprobe=nprobe, logger=logger)

    save_faiss_index(index, INDEX_PATH, logger)
    save_metadata(metadata, METADATA_PATH, logger)

    logger.info(f"Stored {len(vectors)} vectors to FAISS (IVFFlat) at {INDEX_PATH}")


def main():
    """Main entry point."""
    logger_factory = LoggerFactory.instance()
    logger = logger_factory.get_logger("embedding-storage")

    run_indexing(nlist=N_LIST, nprobe=N_PROBE, logger=logger)

if __name__ == "__main__":
    main()
