"""Shared utilities for reading/writing JSON and standardizing chunk format."""

import json
import uuid
from langchain.text_splitter import RecursiveCharacterTextSplitter

def save_chunks(output_path, all_chunks, logger):
    """Save chunk list to JSON file and log the outcome."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        logger.info("Written %d chunks to %s.", len(all_chunks), output_path)
    except OSError as e:
        logger.error("File error while writing %s: %s", output_path, e)

def read_json_file(input_path, logger):
    """Load JSON file and return data, with proper error handling."""
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, OSError) as e:
        logger.error("File error while reading %s: %s", input_path, e)
    except json.JSONDecodeError as e:
        logger.error("JSON decode error in %s: %s", input_path, e)
    return []

def build_chunk_dict(chunk_text, metadata, code_blocks):
    """Create a standardized chunk dictionary."""
    return {
        "id": str(uuid.uuid4()),
        "chunk_text": chunk_text,
        "metadata": metadata,
        "code_blocks": code_blocks
    }

def get_text_splitter(chunk_size, chunk_overlap, separators=None):
    """
    Creates and returns a RecursiveCharacterTextSplitter with given parameters.

    Args:
        chunk_size (int): Maximum size of each text chunk.
        chunk_overlap (int): Number of overlapping characters between chunks.
        separators (list[str], optional): Custom list of separators for splitting.
                                          If None or empty, uses a default strategy.

    Returns:
        RecursiveCharacterTextSplitter: Configured text splitter instance.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators or ["\n\n", "\n", " ", ""]
    )
