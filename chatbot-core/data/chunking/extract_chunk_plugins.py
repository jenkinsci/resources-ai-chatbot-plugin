"""Chunk Jenkins plugin HTML docs into structured text blocks with metadata."""
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
INPUT_PATH = os.path.join(SCRIPT_DIR, "..", "processed", "processed_plugin_docs.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "processed", "chunks_plugin_docs.json")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
CODE_BLOCK_PLACEHOLDER_PATTERN = r"\[\[CODE_BLOCK_(\d+)\]\]"
PLACEHOLDER_TEMPLATE = "[[CODE_BLOCK_{}]]"

def process_plugin(plugin_name, html, text_splitter):
    """
    Process a single Jenkins plugin documentation HTML:
    - Extracts code blocks
    - Converts content to plain text
    - Splits it into overlapping chunks
    - Reassigns code blocks to the appropriate chunks

    Args:
        plugin_name (str): Name of the Jenkins plugin (used as metadata title).
        html (str): Raw HTML content of the plugin documentation.
        text_splitter (RecursiveCharacterTextSplitter): Text splitter to use for chunking.

    Returns:
        list[dict]: List of chunk dictionaries with text, metadata, and code blocks.
    """
    soup = BeautifulSoup(html, "lxml")
    code_blocks = extract_code_blocks(soup, "pre", PLACEHOLDER_TEMPLATE)

    text = soup.get_text(separator="\n", strip=True)
    # Validate that the placeholders are not removed if code blocks were extracted
    if code_blocks and PLACEHOLDER_TEMPLATE.format(0) not in text:
        logger.warning(
            "Extracted %d code blocks for %s but no placeholders found in text. "
            "Possible issue with placeholder insertion.",
            len(code_blocks),
            plugin_name
        )
    chunks = text_splitter.split_text(text)

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
                "data_source": "jenkins_plugins_documentation",
                "title": plugin_name
            },
            chunk["code_blocks"]
        )
        for chunk in processed_chunks
    ]

def extract_chunks(plugin_docs):
    """
    Process all Jenkins plugin documentation files by extracting and chunking them.

    Args:
        plugin_docs (dict): Mapping from plugin name to HTML content.

    Returns:
        list[dict]: All processed chunks for all plugins.
    """
    all_chunks = []
    text_splitter = get_text_splitter(CHUNK_SIZE, CHUNK_OVERLAP)

    for plugin_name, html in plugin_docs.items():
        plugin_chunks = process_plugin(plugin_name, html, text_splitter)
        all_chunks.extend(plugin_chunks)

    return all_chunks

def main():
    """Main entry point."""
    plugin_docs = read_json_file(INPUT_PATH, logger)
    if not plugin_docs:
        return

    logger.info("Chunking from %d plugin docs.", len(plugin_docs.keys()))
    all_chunks = extract_chunks(plugin_docs)

    save_chunks(OUTPUT_PATH, all_chunks, logger)

if __name__ == "__main__":
    main()
