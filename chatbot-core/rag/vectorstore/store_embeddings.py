"""
Embeds document chunks, builds a FAISS IVF index,
and stores both the index and associated metadata to disk.
"""

import argparse
import os
import numpy as np
import faiss
from rag.embedding import embed_chunks
from rag.embedding.embed_chunks import SOURCE_CHUNK_FILES
from rag.vectorstore.vectorstore_utils import save_faiss_index, save_metadata
from utils import LoggerFactory

VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "embeddings")

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
    quantizer = faiss.IndexFlatL2(d)
    index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_L2)

    logger.info("FAISS index training started...")
    index.train(vectors)  # pylint: disable=no-value-for-parameter
    logger.info("FAISS index training completed.")
    index.nprobe = nprobe
    index.add(vectors)  # pylint: disable=no-value-for-parameter

    return index


def run_indexing(nlist, nprobe, logger, source_name):
    """
    Main pipeline: embed documents for one source, build FAISS index,
    and save index + metadata under {source_name}_index.idx / _metadata.pkl
    so the retriever (which keys files by source_name) can load them.

    Args:
        nlist (int): Number of clusters for FAISS IVF index.
        nprobe (int): Number of clusters to search during queries.
        source_name (str): Source key from SOURCE_CHUNK_FILES.
    """
    if source_name not in SOURCE_CHUNK_FILES:
        raise ValueError(
            f"Unknown source '{source_name}'. "
            f"Expected one of: {sorted(SOURCE_CHUNK_FILES)}"
        )

    chunk_file = SOURCE_CHUNK_FILES[source_name]
    index_path = os.path.join(VECTOR_STORE_DIR, f"{source_name}_index.idx")
    metadata_path = os.path.join(VECTOR_STORE_DIR, f"{source_name}_metadata.pkl")

    logger.info("Starting document embedding for source '%s'...", source_name)
    vectors, metadata = embed_chunks(logger, chunk_files=[chunk_file])

    if len(vectors) == 0:
        logger.warning(
            "No vectors produced for source '%s' (chunk file: %s). Skipping index build.",
            source_name, chunk_file
        )
        return

    vectors_np = np.array(vectors).astype("float32")

    index = build_faiss_ivf_index(vectors_np, nlist=nlist, nprobe=nprobe, logger=logger)

    save_faiss_index(index, index_path, logger)
    save_metadata(metadata, metadata_path, logger)

    logger.info("Stored %d vectors to FAISS (IVFFlat) at %s", len(vectors), index_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build a FAISS index for one source (plugins, docs, discourse) "
                    "or all of them if --source is omitted."
    )
    parser.add_argument(
        "--source",
        choices=sorted(SOURCE_CHUNK_FILES),
        help="Source to index. If omitted, indexes every source in SOURCE_CHUNK_FILES.",
    )
    args = parser.parse_args()

    logger_factory = LoggerFactory.instance()
    logger = logger_factory.get_logger("embedding-storage")

    sources = [args.source] if args.source else list(SOURCE_CHUNK_FILES)
    for source_name in sources:
        run_indexing(nlist=N_LIST, nprobe=N_PROBE, logger=logger, source_name=source_name)

if __name__ == "__main__":
    main()
