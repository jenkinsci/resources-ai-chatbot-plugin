"""Script to chunk Jenkins HTML documentation into text blocks with metadata."""
# pylint: disable=R0801

import os
from bs4 import BeautifulSoup
from data.chunking.chunking_utils import(
    extract_code_blocks,
    extract_title,
    assign_code_blocks_to_chunks,
    save_chunks,
    read_json_file,
    build_chunk_dict,
    get_text_splitter
)
from utils import LoggerFactory
from config.pipeline_loader import load_pipeline_config

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("chunking")

# Load pipeline configuration
PIPELINE_CONFIG = load_pipeline_config()
chunking_config = PIPELINE_CONFIG["chunking"]["docs"]
general_config = PIPELINE_CONFIG["general"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "..", general_config["processed_data_dir"].replace("data/", ""), chunking_config["input_file"])
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", general_config["processed_data_dir"].replace("data/", ""), chunking_config["output_file"])

CHUNK_SIZE = chunking_config["chunk_size"]
CHUNK_OVERLAP = chunking_config["chunk_overlap"]
CODE_BLOCK_PLACEHOLDER_PATTERN = PIPELINE_CONFIG["chunking"]["code_block_placeholder_pattern"]
PLACEHOLDER_TEMPLATE = PIPELINE_CONFIG["chunking"]["placeholder_template"]

def process_page(url, html, text_splitter):
    """
    Processes a single Jenkins documentation page:
    - Parses the HTML
    - Extracts title and code blocks
    - Converts to plain text and splits into chunks
    - Reassigns code blocks to appropriate chunks

    Args:
        url (str): Source URL of the documentation page.
        html (str): Raw HTML content of the page.
        text_splitter (RecursiveCharacterTextSplitter): LangChain text splitter instance.

    Returns:
        list[dict]: A list of chunk dictionaries with text, metadata, and code blocks.
    """
    soup = BeautifulSoup(html, "lxml")
    title = extract_title(soup)
    code_blocks = extract_code_blocks(soup, "pre", PLACEHOLDER_TEMPLATE)

    text = soup.get_text(separator="\n", strip=True)
    # Validate that the placeholders are not removed if code blocks were extracted
    if code_blocks and PLACEHOLDER_TEMPLATE.format(0) not in text:
        logger.warning(
            "Extracted %d code blocks for %s but no placeholders found in text. "
            "Possible issue with placeholder insertion.",
            len(code_blocks),
            url
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
                "data_source": "jenkins_documentation",
                "source_url": url,
                "title": title
            },
            chunk["code_blocks"]
        )
        for chunk in processed_chunks
    ]

def extract_chunks(docs):
    """
    Processes all Jenkins documentation pages by chunking their content.

    Args:
        docs (dict): A dictionary mapping URLs to raw HTML strings.

    Returns:
        list[dict]: A list of all processed chunks across all docs.
    """
    all_chunks = []
    text_splitter = get_text_splitter(CHUNK_SIZE, CHUNK_OVERLAP)

    for url, html in docs.items():
        page_chunks = process_page(url, html, text_splitter)
        all_chunks.extend(page_chunks)

    return all_chunks

def main():
    """Main entry point."""
    docs = read_json_file(INPUT_PATH, logger)
    if not docs:
        return

    logger.info("Chunking from %d page docs.", len(docs.keys()))
    all_chunks = extract_chunks(docs)

    save_chunks(OUTPUT_PATH, all_chunks, logger)

if __name__ == "__main__":
    main()
