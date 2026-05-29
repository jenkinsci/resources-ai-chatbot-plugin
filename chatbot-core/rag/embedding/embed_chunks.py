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

# Maps a source_name (matching CONFIG["tool_names"] values and the
# {source_name}_index.idx files the retriever expects) to its chunk JSON file.
SOURCE_CHUNK_FILES = {
    "plugins": "chunks_plugin_docs.json",
    "docs": "chunks_docs.json",
    "discourse": "chunks_discourse_docs.json",
}

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

def collect_all_chunks(logger, chunk_files):
    """
    Load and aggregate chunks from the given JSON files.

    Args:
        logger (logging.Logger): Logger for warnings and file-level updates.
        chunk_files (list[str]): Chunk JSON filenames inside PROCESSED_DIR.

    Returns:
        list[dict]: A combined list of all loaded chunks.
    """
    all_chunks = []
    for file_name in chunk_files:
        path = os.path.join(PROCESSED_DIR, file_name)
        chunks = load_chunks_from_file(path, logger)
        if not chunks:
            logger.warning("No chunks available from %s.", file_name)
            continue
        all_chunks.extend(chunks)
    return all_chunks

def embed_chunks(logger, chunk_files=None):
    """
    Embed all loaded text chunks and return vectors and associated metadata.

    Args:
        logger (logging.Logger): Logger for progress updates.
        chunk_files (list[str] | None): Chunk JSON filenames to embed. Defaults to
            every file in SOURCE_CHUNK_FILES when not provided.

    Returns:
        tuple: (list[np.ndarray], list[dict]) - embeddings and structured metadata.
    """
    if chunk_files is None:
        chunk_files = list(SOURCE_CHUNK_FILES.values())
    chunks = collect_all_chunks(logger, chunk_files)
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
