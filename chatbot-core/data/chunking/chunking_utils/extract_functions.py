"""Functions for extracting titles and code blocks from HTML content."""

import re
from bs4 import NavigableString

def extract_title(soup):
    """
    Extracts the title from a BeautifulSoup-parsed HTML document.

    Priority:
    1. <h1> element if present
    2. <title> tag as fallback
    3. Returns "Untitled" if neither is found

    Args:
        soup (BeautifulSoup): Parsed HTML document.

    Returns:
        str: The extracted title string.
    """
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    if soup.title:
        return soup.title.get_text(strip=True)
    return "Untitled"

def extract_code_blocks(soup, tag, placeholder_template):
    """
    Extracts all code blocks of a specified HTML tag (e.g., <pre>, <code>),
    replaces them with numbered placeholders, and returns the list of raw code strings.

    Args:
        soup (BeautifulSoup): Parsed HTML content.
        tag (str): HTML tag to search for (e.g., "pre", "code").

    Returns:
        list[str]: A list of code block strings, in the order they were found.
    """
    code_blocks = []
    for i, code_block in enumerate(soup.find_all(tag)):
        placeholder = placeholder_template.format(i)
        code_blocks.append(code_block.get_text(strip=True))
        code_block.replace_with(NavigableString(placeholder))
    return code_blocks

def assign_code_blocks_to_chunks(chunks, code_blocks, placeholder_pattern, logger):
    """
    Assigns relevant code blocks to each chunk based on placeholder references.
    
    Args:
        chunks: List of text chunks (strings).
        code_blocks: List of all extracted code blocks.
        placeholder_pattern: Regex pattern to find placeholder indices

    Returns:
        A list of dicts with 'chunk_text' and corresponding 'code_blocks'.
    """
    processed_chunks = []

    for chunk in chunks:
        matches = re.findall(placeholder_pattern, chunk)
        indices = set()

        for match in matches:
            try:
                idx = int(match)
                if idx < len(code_blocks):
                    indices.add(idx)
                else:
                    logger.warning(
                        "Placeholder index %d out of range (max index %d). Skipping.",
                        idx, len(code_blocks) - 1
                    )
            except ValueError:
                logger.warning(
                    "Malformed placeholder index: '%s'. Skipping.",
                    match
                )

        chunk_code_blocks = [code_blocks[i] for i in sorted(indices)]

        processed_chunks.append({
            "chunk_text": chunk,
            "code_blocks": chunk_code_blocks
        })

    return processed_chunks
