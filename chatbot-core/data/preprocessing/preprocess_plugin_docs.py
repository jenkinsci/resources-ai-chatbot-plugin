"""Preprocess HTML content from Jenkins plugin documentation pages."""

import json
import os
from bs4 import BeautifulSoup
from data.preprocessing.preprocessing_utils import (
    remove_tags,
    remove_html_comments,
    get_visible_text_length,
    strip_html_body_wrappers
)
from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("preprocessing")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "plugin_docs.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "processed", "processed_plugin_docs.json")

MIN_VISIBLE_TEXT_LENGTH = 60

def process_plugin_docs(plugin_docs):
    """Clean and filter plugin HTML docs based on content length.

    Args:
        plugin_docs (dict): Raw plugin documentation keyed by plugin name.

    Returns:
        dict: Filtered documentation content.
    """
    processed_plugin_docs = {}

    for plugin_name, html_content in plugin_docs.items():
        soup = BeautifulSoup(html_content, "lxml")
        html_content = str(soup)
        cleaned_html = remove_tags(html_content)
        content_without_comments = remove_html_comments(cleaned_html)
        content_without_wrappers = strip_html_body_wrappers(content_without_comments)

        text_length = get_visible_text_length(content_without_wrappers)
        if text_length > MIN_VISIBLE_TEXT_LENGTH:
            processed_plugin_docs[plugin_name] = content_without_wrappers
        else:
            logger.info(
                "Skipping plugin '%s' - visible text length: %d <= %d",
                plugin_name,
                text_length,
                MIN_VISIBLE_TEXT_LENGTH
            )

    logger.info(
        "Processed %d out of %d plugins.",
        len(processed_plugin_docs),
        len(plugin_docs)
    )

    return processed_plugin_docs

def main():
    """Main entry point."""
    plugin_data = {}

    try:
        with open(INPUT_PATH, "r", encoding='utf-8') as f:
            plugin_data = json.load(f)
    except (FileNotFoundError, OSError) as e:
        logger.error("File error while reading from %s: %s", INPUT_PATH, e)
        return
    except json.JSONDecodeError as e:
        logger.error("JSON decode error in %s: %s", INPUT_PATH, e)
        return

    logger.info("Handling %d plugin docs.", len(plugin_data))

    processed_plugin_docs = process_plugin_docs(plugin_data)

    try:
        with open(OUTPUT_PATH, "w", encoding='utf-8') as f:
            json.dump(processed_plugin_docs, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error("File error while writing to %s: %s", OUTPUT_PATH, e)
        return

    logger.info("Saved processed plugins to %s.", OUTPUT_PATH)

if __name__ == "__main__":
    main()
