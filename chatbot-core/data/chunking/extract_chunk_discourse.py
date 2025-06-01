"""Chunk Discourse threads into structured content blocks with metadata."""
# pylint: disable=R0801

import os
import re
from data.chunking.chunking_utils import(
    assign_code_blocks_to_chunks,
    save_chunks,
    read_json_file,
    build_chunk_dict,
    get_text_splitter
)
from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("chunking")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "topics_with_posts.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "processed", "chunks_discourse_docs.json")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
CODE_BLOCK_PLACEHOLDER_PATTERN = r"\[\[(?:CODE_BLOCK|CODE_SNIPPET)_(\d+)\]\]"
TRIPLE_BACKTICK_CODE_PATTERN = r"```(?:\w+\n)?(.*?)```"
INLINE_BACKTICK_CODE_PATTERN = r"`([^`\n]+?)`"

def extract_code_blocks(text):
    """
    Extracts code blocks and replaces them with indexed placeholders.
    Supports both triple-backtick code blocks and inline code in backticks.

    Args:
        text (str): Raw text including code blocks.

    Returns:
        tuple:
            - List of extracted code blocks (in order of appearance).
            - Modified text with placeholders inserted in place of code.
    """
    code_blocks = []
    placeholder_counter = 0

    # Replace triple backtick code blocks with indexed placeholders
    def replace_triple(match):
        nonlocal placeholder_counter
        code = match.group(1).strip()
        placeholder = f"[[CODE_BLOCK_{placeholder_counter}]]"
        code_blocks.append(code)
        placeholder_counter += 1
        return placeholder

    text = re.sub(TRIPLE_BACKTICK_CODE_PATTERN, replace_triple, text, flags=re.DOTALL)

    # Replace inline backtick code with indexed placeholders
    def replace_inline(match):
        nonlocal placeholder_counter
        code = match.group(1).strip()
        placeholder = f"[[CODE_SNIPPET_{placeholder_counter}]]"
        code_blocks.append(code)
        placeholder_counter += 1
        return placeholder

    text = re.sub(INLINE_BACKTICK_CODE_PATTERN, replace_inline, text)

    return code_blocks, text


def process_thread(thread, text_splitter):
    """
    Processes a single Discourse thread into structured chunks.

    Args:
        thread (dict): Thread data including topic ID, title, and post texts.
        text_splitter (RecursiveCharacterTextSplitter): Chunking utility.

    Returns:
        list[dict]: List of chunk objects with text, metadata, and associated code blocks.
    """
    topic_id = thread.get("topic_id")
    title = thread.get("title", "Untitled")
    posts = thread.get("posts", [])

    # Combine all posts into a single text block
    full_text = "\n\n".join(posts)

    code_blocks, clean_text = extract_code_blocks(full_text)
    chunks = text_splitter.split_text(clean_text)

    processed_chunks = assign_code_blocks_to_chunks(
        chunks,
        code_blocks,
        CODE_BLOCK_PLACEHOLDER_PATTERN,
        logger
    )

    return [
        build_chunk_dict(
            chunk["chunk_text"],
            {
                "data_source": "discourse_threads",
                "topic_id": topic_id,
                "title": title
            },
            chunk["code_blocks"]
        )
        for chunk in processed_chunks
    ]

def extract_chunks(threads):
    """
    Processes all Discourse threads into a flat list of chunks.

    Args:
        threads (list): List of Discourse thread dicts.

    Returns:
        list[dict]: All chunks extracted from all threads.
    """
    all_chunks = []
    text_splitter = get_text_splitter(CHUNK_SIZE, CHUNK_OVERLAP)

    for thread in threads:
        thread_chunks = process_thread(thread, text_splitter)
        all_chunks.extend(thread_chunks)

    return all_chunks

def main():
    """Main entry point."""
    threads = read_json_file(INPUT_PATH, logger)
    if not threads:
        return

    logger.info("Chunking %d Discourse threads.", len(threads))
    all_chunks = extract_chunks(threads)

    save_chunks(OUTPUT_PATH, all_chunks, logger)

if __name__ == "__main__":
    main()
