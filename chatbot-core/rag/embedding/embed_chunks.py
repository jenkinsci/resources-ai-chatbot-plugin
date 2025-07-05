"""
Loads text chunks from preprocessed JSON files, embeds them using SentenceTransformers,
and returns both embeddings and associated metadata.
"""

import os
import json
from .embedding_utils import load_embedding_model, embed_documents

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DIR = os.path.join(SCRIPT_DIR, "..", "..", "data", "processed")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_FILES = [
    "chunks_docs.json",
    "chunks_plugin_docs.json",
    "chunks_discourse_docs.json",
    "chunks_stackoverflow_threads.json"
]

def load_chunks_from_file(path, logger):
    """Load JSON file and return data, with proper error handling."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, OSError) as e:
        logger.error("File error while reading %s: %s", path, e)
    except json.JSONDecodeError as e:
        logger.error("JSON decode error in %s: %s", path, e)
    return []

def collect_all_chunks(logger):
    """
    Load and aggregate chunks from all selected JSON files.

    Args:
        logger (logging.Logger): Logger for warnings and file-level updates.

    Returns:
        list[dict]: A combined list of all loaded chunks.
    """
    all_chunks = []
    for file_name in CHUNK_FILES:
        path = os.path.join(PROCESSED_DIR, file_name)
        chunks = load_chunks_from_file(path, logger)
        if not chunks:
            logger.warning("No chunks available from %s.", file_name)
            continue
        all_chunks.extend(chunks)
    return all_chunks

def embed_chunks(logger):
    """
    Embed all loaded text chunks and return vectors and associated metadata.

    Args:
        logger (logging.Logger): Logger for progress updates.
        model (SentenceTransformer, optional): Optionally pass a preloaded model.

    Returns:
        tuple: (list[np.ndarray], list[dict]) - embeddings and structured metadata.
    """
    chunks = collect_all_chunks(logger)
    logger.info("Collected %d chunks.", len(chunks))
    metadata = []
    for chunk in chunks:
        chunk_id = chunk.get("id")
        chunk_metadata = chunk.get("metadata", {})
        code_blocks = chunk.get("code_blocks", [])
        chunk_text = chunk.get("chunk_text", "")

        if not chunk_metadata or not chunk_text:
            logger.warning(
                "Chunk %s has empty metadata or text.",
                chunk_id
            )
            continue

        metadata.append({
            "id": chunk_id,
            "chunk_text": chunk_text,
            "metadata": chunk_metadata,
            "code_blocks": code_blocks
        })

    texts = [el["chunk_text"] for el in metadata]
    model = load_embedding_model(MODEL_NAME, logger)
    vectors = embed_documents(texts, model, logger)

    return vectors, metadata
