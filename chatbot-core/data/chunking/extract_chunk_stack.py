"""Chunk StackOverflow threads into structured blocks with metadata."""
# pylint: disable=R0801

import os
from bs4 import BeautifulSoup
from data.chunking.chunking_utils import(
    extract_code_blocks,
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
INPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "stack_overflow_threads.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "processed", "chunks_stackoverflow_threads.json")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
CODE_BLOCK_PLACEHOLDER_PATTERN = r"\[\[CODE_BLOCK_(\d+)\]\]"
PLACEHOLDER_TEMPLATE = "[[CODE_BLOCK_{}]]"

def clean_html(html):
    """
    Parses and cleans HTML content using BeautifulSoup.

    Args:
        html (str): Raw HTML string containing question and answer.

    Returns:
        BeautifulSoup: Parsed HTML object.
    """
    return BeautifulSoup(html, "lxml")

def process_thread(thread, text_splitter):
    """
    Processes a single StackOverflow Q&A thread:
    - Combines question and answer bodies
    - Parses HTML
    - Extracts code blocks and replaces them with placeholders
    - Splits plain text into overlapping chunks
    - Assigns relevant code blocks to each chunk

    Args:
        thread (dict): StackOverflow thread dictionary.
        text_splitter (RecursiveCharacterTextSplitter): Chunking utility.

    Returns:
        list[dict]: List of chunk objects with text, metadata, and code blocks.
    """
    question_id = thread.get("Question ID")
    question_body = thread.get("Question Body", "")
    answer_body = thread.get("Answer Body", "")

    if question_body == "" or answer_body == "":
        logger.warning(
            "Question %d is missing question/answer content. Extracting 0 chunks from it.", 
            question_id
        )
        return []

    question_and_answer = f"<div>{question_body}</div><div>{answer_body}</div>"
    soup = clean_html(question_and_answer)

    code_blocks = extract_code_blocks(soup, "code", PLACEHOLDER_TEMPLATE)

    full_text = soup.get_text(separator="\n", strip=True)

    chunks = text_splitter.split_text(full_text)
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
                "data_source": "stackoverflow_threads",
                "question_id": question_id,
                "title": thread.get("Question Title", "Untitled"),
                "tags": thread.get("Tags", ""),
                "creation_date": thread.get("CreationDate", ""),
                "question_score": thread.get("Question Score", 0),
                "answer_score": thread.get("Answer Score", 0)
            },
            chunk["code_blocks"]
        )
        for chunk in processed_chunks
    ]

def extract_chunks(threads):
    """
    Processes a list of StackOverflow threads into structured chunks.

    Args:
        threads (list): List of StackOverflow thread dicts.

    Returns:
        list[dict]: All extracted chunks from all threads.
    """
    all_chunks = []
    text_splitter = get_text_splitter(CHUNK_SIZE, CHUNK_OVERLAP)

    for thread in threads:
        chunks = process_thread(thread, text_splitter)
        all_chunks.extend(chunks)

    return all_chunks

def main():
    """Main entry point."""
    threads = read_json_file(INPUT_PATH, logger)
    if not threads:
        return

    logger.info("Chunking from %d stackoverflow threads.", len(threads))
    all_chunks = extract_chunks(threads)

    save_chunks(OUTPUT_PATH, all_chunks, logger)

if __name__ == "__main__":
    main()
