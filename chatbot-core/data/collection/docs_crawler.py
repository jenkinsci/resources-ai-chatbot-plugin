"""Module for crawling and collecting content from Jenkins documentation pages."""

import json
import os
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("collection")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "../raw/jenkins_docs.json")

# Home URL of jenkins doc
BASE_URL = "https://www.jenkins.io/doc/"

# Set to check for duplicates
visited_urls = set()

# Key: url ; Value: content of that page
page_content = {}

non_canonic_content_urls = set()

def is_valid_url(url):
    """Check if the URL is a valid link to a new page, internal to the doc, 
        or a redirect to another page
    """
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and BASE_URL in url and "#" not in url

def extract_page_content_container(soup):
    """Extract content from the 'container' div class"""
    content_div = soup.find("div", class_="container")
    if content_div:
        return str(content_div)
    return ""


def crawl(url):
    """Recursively crawl documentation pages starting from the base URL"""

    # Avoid multiple visits
    if url in visited_urls:
        return

    logger.info("Visiting: %s", url)
    try:
        visited_urls.add(url)

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        content = extract_page_content_container(soup)
        if content:
            page_content[url] = content
        else:
            non_canonic_content_urls.add(url)

        # Find all links in the page
        links = soup.find_all("a", href=True)
        if '.html' not in url and not url.endswith('/'):
            url += '/'

        for link in links:
            href = link['href']
            full_url = urljoin(url, href)
            if is_valid_url(full_url):
                crawl(full_url)

    except requests.RequestException as e:
        logger.error("Error accessing %s: %s", url, e)

def start_crawl():
    """Start the crawling process from the base URL."""
    logger.info("Crawling started")
    crawl(BASE_URL)
    logger.info("Total pages found: %d", len(visited_urls))
    logger.info("Total pages with content: %d", len(page_content))
    logger.info("Non canonic content page structure links: %s", non_canonic_content_urls)
    logger.info("Crawling ended")

    logger.info("Saving results in json")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(page_content, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    start_crawl()
