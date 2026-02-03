"""Script to fetch and save Jenkins plugin names from the experimental update site."""

import json
import os
import requests
import sys
from typing import List
from bs4 import BeautifulSoup
from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("collection")

URL = "https://updates.jenkins.io/experimental/latest/"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "plugin_names.json")

def fetch_plugin_names() -> List[str]:
    """
    Fetches a list of available plugin artifact names (.hpi) from the Jenkins update site.
    
    Returns:
        List[str]: List of raw plugin file names (e.g., 'git.hpi', 'docker-slaves.hpi').
    """
    logger.info("Fetching plugin index page from %s...", URL)
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("Failed to fetch plugin list from %s: %s", URL, e)
        sys.exit(1)

    soup = BeautifulSoup(response.content, "html.parser")

    plugin_list: List[str] = []
    ul = soup.find("ul", class_="artifact-list")
    if ul:
        for li in ul.find_all("li"):
            a_tag = li.find("a")
            if a_tag and "href" in a_tag.attrs:
                href = a_tag["href"]
                if href.endswith(".hpi"):
                    plugin_name = href.strip()
                    if plugin_name:
                        plugin_list.append(plugin_name)

    logger.info("Found %d plugins.", len(plugin_list))
    return plugin_list

def save_plugin_names(plugin_names_with_extension: List[str]) -> None:
    """Remove `.hpi` extensions and save plugin names to a JSON file.

    Args:
        plugin_names_with_extension (List[str]): List of plugin filenames with `.hpi` extension.
    """
    # Using removesuffix (Python 3.9+) is a safer and more readable way
    # to remove the file extension than string slicing.
    plugin_names = [plugin_name.removesuffix(".hpi") for plugin_name in plugin_names_with_extension]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(plugin_names, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d plugin names to %s", len(plugin_names), OUTPUT_PATH)

if __name__ == "__main__":
    plugins = fetch_plugin_names()
    if plugins:
        save_plugin_names(plugins)
