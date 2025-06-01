"""Preprocess Jenkins documentation by extracting and cleaning HTML content."""

import json
import os
from bs4 import BeautifulSoup
from data.preprocessing.preprocessing_utils import (
    remove_container_by_class,
    remove_tags,
    extract_page_content_container,
    remove_html_comments,
    remove_edge_navigation_blocks,
    split_type_docs,
    strip_html_body_wrappers
)
from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("preprocessing")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DOCS_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "jenkins_docs.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "processed", "processed_jenkins_docs.json")

def filter_content(urls, data, is_developer_content):
    """
    Filters HTML content for a list of URLs by extracting the main section
    and cleaning out unwanted elements like TOC, scripts, images, nav blocks, and comments.

    Parameters:
    - urls (list): List of URLs to filter.
    - data (dict): Dictionary of raw HTML content keyed by URL.
    - is_developer_content (bool): Whether the content is from developer docs.

    Returns:
    - dict: Filtered HTML content keyed by URL.
    """
    config = get_config(is_developer_content)
    filtered_contents = {}

    for url in urls:
        if url not in data:
            logger.warning("URL not found in data: %s", url)
            continue
        content = data[url]
        soup = BeautifulSoup(content, "lxml")

        content_extracted = extract_page_content_container(soup, config["class_to_extract"])
        if content_extracted == "":
            logger.warning(
                "NO %s FOUND IN A %sDEVELOPER PAGE! Skipping page: %s",
                config["class_to_extract"],
                "" if is_developer_content else "NON ",
                url
            )
            continue

        # Remove eventually toc(table of content)
        content_without_toc = remove_container_by_class(content_extracted, "toc")

        # Remove eventually img or script tags
        content_filtered_by_tags = remove_tags(content_without_toc)

        # Remove eventually navigation blocks (for docs under /developer this is not necessary)
        content_without_navigation_blocks = (
            content_filtered_by_tags if is_developer_content
            else remove_edge_navigation_blocks(content_filtered_by_tags)
        )

        content_without_comments = remove_html_comments(content_without_navigation_blocks)

        filtered_contents[url] = strip_html_body_wrappers(content_without_comments)

    return filtered_contents

def get_config(is_developer_content):
    """
    Returns configuration options depending on doc type. Introduced to maintain in the future
    a unique filter_content function, without hardcoding parameters whether it is a developer
    content or not.

    Parameters:
    - is_developer_content (bool): Whether the content is from developer docs.

    Returns:
    - dict: Configuration dict with class name to extract.
    """
    if is_developer_content:
        return {
            "class_to_extract": "col-8"
        }

    return {
        "class_to_extract": "col-lg-9"
    }


def main():
    """Main entry point."""
    try:
        with open(INPUT_DOCS_PATH, "r", encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, OSError) as e:
        logger.error("File error while reading %s: %s", INPUT_DOCS_PATH, e)
        return
    except json.JSONDecodeError as e:
        logger.error("JSON decode error in %s: %s", INPUT_DOCS_PATH, e)
        return

    developer_urls, non_developer_urls = split_type_docs(data, logger)

    logger.info("Processing Developer contents")
    developer_content_filtered = filter_content(developer_urls, data, True)
    logger.info("Processing  Non Developer contents")
    non_developer_content_filtered = filter_content(non_developer_urls, data, False)

    output = {}
    output["developer_docs"] = developer_content_filtered
    output["non_developer_docs"] = non_developer_content_filtered

    try:
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)
    except OSError as e:
        logger.error("File error while  writing %s: %s", OUTPUT_PATH, e)
        return

if __name__ == "__main__":
    main()
