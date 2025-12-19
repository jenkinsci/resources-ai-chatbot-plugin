"""Module for crawling and collecting content from Jenkins documentation pages."""

import json
import os
from urllib.parse import urljoin, urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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


def create_session_with_retries():
    """Create a requests session with automatic retry on rate limits.
    
    Uses exponential backoff and respects Retry-After header from server.
    This is an optimistic approach - we don't slow down unless the server
    tells us to.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,  # 1s, 2s, 4s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Key: url ; Value: content of that page
page_content = {}

non_canonic_content_urls = set()


def normalize_url(url):
    """Normalize URL by adding trailing slash for non-HTML pages."""
    if '.html' not in url and not url.endswith('/'):
        url += '/'
    return url


def is_valid_url(url):
    """Check if the URL is a valid link to a new page, internal to the doc, 
        or a redirect to another page
    """
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and BASE_URL in url and "#" not in url


def extract_page_content_container(soup):
    """Extract main content from the page.
    
    Developer docs use col-8, non-developer docs use col-lg-9.
    Falls back to container if neither is found.
    """
    content_div = (
        soup.find("div", class_="col-8") or 
        soup.find("div", class_="col-lg-9") or
        soup.find("div", class_="container")
    )
    if content_div:
        return str(content_div)
    return ""


def crawl(start_url):
    """Iteratively crawl documentation pages using stack-based DFS.
    
    Uses an explicit stack instead of recursion to avoid RecursionError
    on deep documentation structures. Maintains the same traversal order
    as the original recursive implementation.
    
    Args:
        start_url: The URL to begin crawling from.
    """
    session = create_session_with_retries()
    stack = [start_url]

    while stack:
        url = stack.pop()

        # Normalize URL before checking visited
        url = normalize_url(url)

        # Fast skip for already visited or invalid URLs
        if url in visited_urls:
            continue

        if not is_valid_url(url):
            continue

        logger.info("Visiting: %s", url)

        try:
            visited_urls.add(url)

            response = session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            content = extract_page_content_container(soup)
            if content:
                page_content[url] = content
            else:
                non_canonic_content_urls.add(url)

            # Find all links in the page
            links = soup.find_all("a", href=True)

            # Push links in reverse order to maintain original DFS traversal order
            # Stack is LIFO, so reversed() ensures first link gets processed first
            for link in reversed(links):
                href = link['href']
                full_url = urljoin(url, href)
                # Normalize before pushing to prevent duplicate stack entries
                full_url = normalize_url(full_url)
                if is_valid_url(full_url) and full_url not in visited_urls:
                    stack.append(full_url)

        except requests.RequestException as e:
            logger.error("Error accessing %s: %s", url, e)
            continue  # Skip this URL, continue with remaining stack

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
