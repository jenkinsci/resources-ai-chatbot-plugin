"""Filter Jenkins documentation pages based on content length and link density."""

import json
import os
from bs4 import BeautifulSoup
from data.preprocessing.preprocessing_utils import(
    get_visible_text_length
)
from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("preprocessing")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "..", "processed", "processed_jenkins_docs.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "processed", "filtered_jenkins_docs.json")

MIN_VISIBLE_TEXT_LENGTH = 300
MAX_LINK_RATIO = 0.1

def link_ratio(content):
    """
    Computes the ratio of <a> tags to visible text chunks (roughly per 7 chars).

    Parameters:
    - content (str): Raw HTML content.

    Returns:
    - float: Ratio of links to visible text size.
    """
    soup = BeautifulSoup(content, "html.parser")
    links = soup.find_all("a")
    text = soup.get_text(separator=" ", strip=True)
    text_length = max(len(text), 1)
    chunks = max(text_length / 7, 1)

    return len(links) / chunks

def normalize_url(url):
    """
    Normalizes a URL by removing trailing slashes and 'index.html'.

    Parameters:
    - url (str): Original URL.

    Returns:
    - str: Normalized URL.
    """
    if url.endswith("index.html"):
        url = url[: -len("index.html")]

    if url.endswith("/"):
        url = url[:-1]

    return url

def normalize_url_keys(doc_dict):
    """
    Applies URL normalization to the keys of a documentation dictionary.

    Parameters:
    - doc_dict (dict): Dictionary with URLs as keys.

    Returns:
    - dict: Dictionary with normalized URLs as keys.
    """
    result = {}
    for url, content in doc_dict.items():
        normalized_url = normalize_url(url)
        if normalized_url in result:
            logger.warning("Duplicate normalized URL found: %s.", normalized_url)
        result[normalized_url] = content
    return result

def main():
    """Main entry point."""
    docs = {}

    try:
        with open(INPUT_PATH, "r", encoding='utf-8') as f:
            data = json.load(f)
            developer_docs = normalize_url_keys(data["developer_docs"])
            non_developer_docs = normalize_url_keys(data["non_developer_docs"])
            docs = developer_docs | non_developer_docs
    except (FileNotFoundError, OSError) as e:
        logger.error("File error while reading %s: %s", INPUT_PATH, e)
        return
    except json.JSONDecodeError as e:
        logger.error("JSON decode error in %s: %s", INPUT_PATH, e)
        return

    urls_to_remove = set()
    for url, content in docs.items():
        if ('extensions' not in url) and (get_visible_text_length(content) < MIN_VISIBLE_TEXT_LENGTH
            or link_ratio(content) > MAX_LINK_RATIO):
            logger.info("Filtering the url: %s.", url)
            urls_to_remove.add(url)

    logger.info('There are %d urls to remove.', len(urls_to_remove))

    cleaned_docs = {url: content for url, content in docs.items() if url not in urls_to_remove}

    logger.info("Cleaned docs contain %d pages after filtering.", len(cleaned_docs))

    try:
        with open(OUTPUT_PATH, "w", encoding='utf-8') as f:
            json.dump(cleaned_docs, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error("File error while writing %s: %s", OUTPUT_PATH, e)
        return


if __name__ == "__main__":
    main()
