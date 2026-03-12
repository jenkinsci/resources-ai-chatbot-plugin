"""Module for crawling and collecting content from Jenkins documentation pages."""

import asyncio
import json
import os
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import aiohttp
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("collection")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "../raw/jenkins_docs.json")

# Home URL of jenkins doc
BASE_URL = "https://www.jenkins.io/doc/"

# Sitemap URL
SITEMAP_URL = "https://www.jenkins.io/sitemap.xml"
SITEMAP_NS = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Max parallel requests
MAX_CONCURRENT = 15

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
        soup.find("div", class_="col-8")
        or soup.find("div", class_="col-lg-9")
        or soup.find("div", class_="container")
    )
    if content_div:
        return str(content_div)
    return ""


def fetch_sitemap_urls():
    """Fetch and parse the sitemap.xml, returning all /doc/ URLs.

    Returns:
        list: A list of normalized URLs under the Jenkins /doc/ prefix.
    """
    logger.info("Fetching sitemap from %s", SITEMAP_URL)
    session = create_session_with_retries()
    try:
        response = session.get(SITEMAP_URL, timeout=10)
        response.raise_for_status()

        root = ElementTree.fromstring(response.content)
        urls = [
            normalize_url(loc.text)
            for loc in root.findall(".//ns:loc", SITEMAP_NS)
            if loc.text and BASE_URL in loc.text
        ]

        logger.info("Sitemap yielded %d /doc/ URLs", len(urls))
        return urls

    except requests.RequestException as e:
        logger.error("Failed to fetch sitemap: %s", e)
        return []
    except ElementTree.ParseError as e:
        logger.error("Failed to parse sitemap XML: %s", e)
        return []


async def fetch_and_process_page(session, url, semaphore, queue, visited_lock):
    """Fetch a page, extract content, and enqueue any new links — all in one async step.

    Args:
        session: An aiohttp ClientSession.
        url: The URL to fetch.
        semaphore: An asyncio.Semaphore to limit concurrency.
        queue: An asyncio.Queue to push newly discovered URLs into.
        visited_lock: An asyncio.Lock.
    """
    retries = 3
    backoff_factor = 1  # 1s, 2s, 4s between retries
    retryable_statuses = {429, 500, 502, 503, 504}
    html = None

    async with semaphore:
        for attempt in range(retries + 1):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        html = await response.text()
                        break

                    if response.status in retryable_statuses and attempt < retries:
                        delay = backoff_factor * (2 ** attempt)
                        logger.warning(
                            "HTTP %d for %s (attempt %d/%d), retrying in %ds",
                            response.status, url, attempt + 1, retries, delay
                        )
                        await asyncio.sleep(delay)
                        continue

                    logger.warning("HTTP %d for %s — skipping", response.status, url)
                    return

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < retries:
                    delay = backoff_factor * (2 ** attempt)
                    logger.warning(
                        "Error fetching %s (attempt %d/%d): %s, retrying in %ds",
                        url, attempt + 1, retries, e, delay
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Failed to fetch %s after %d retries: %s", url, retries, e)
                    return

    if html is None:
        return

    # Process the page: extract content and discover new links
    logger.info("Visiting: %s", url)
    soup = BeautifulSoup(html, "html.parser")

    content = extract_page_content_container(soup)
    if content:
        page_content[url] = content
    else:
        non_canonic_content_urls.add(url)

    # Find all links in the page and enqueue new ones
    links = soup.find_all("a", href=True)
    for link in links:
        href = link['href']
        full_url = urljoin(url, href)
        full_url = normalize_url(full_url)
        if not is_valid_url(full_url):
            continue

        async with visited_lock:
            if full_url in visited_urls:
                continue
            visited_urls.add(full_url)

        await queue.put(full_url)


async def worker(session, semaphore, queue, visited_lock):
    """Worker that pulls URLs from the queue and processes them.

    Args:
        session: An aiohttp ClientSession.
        semaphore: An asyncio.Semaphore to limit concurrency.
        queue: An asyncio.Queue of URLs to process.
        visited_lock: An asyncio.Lock.
    """
    while True:
        url = await queue.get()

        if url is None:
            queue.task_done()
            break
        try:
            await fetch_and_process_page(session, url, semaphore, queue, visited_lock)
        except Exception as exc:
            logger.error("Unexpected error processing %s: %s", url, exc)
        finally:
            queue.task_done()


async def crawl(start_url):
    """Crawl documentation pages using async parallel fetching.

    Seeds the queue from the sitemap first, then follows in-page links
    to discover any additional URLs not present in the sitemap.
    Pages are fetched and processed concurrently via async workers.

    Args:
        start_url: The base URL to include in the initial queue.
    """
    # Phase 1: Seed with sitemap URLs
    sitemap_urls = fetch_sitemap_urls()
    all_seed_urls = list(sitemap_urls) + [start_url]

    queue = asyncio.Queue()

    # Mark all seeds as visited and enqueue them
    for url in all_seed_urls:
        if url not in visited_urls:
            visited_urls.add(url)
            queue.put_nowait(url)

    logger.info("Queue seeded with %d sitemap URLs", len(sitemap_urls))

    # Phase 2: Fetch and process pages in parallel
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)
    timeout = aiohttp.ClientTimeout(total=30)
    visited_lock = asyncio.Lock()

    async with aiohttp.ClientSession(connector=connector,timeout=timeout) as session:
        workers = [
            asyncio.create_task(worker(session, semaphore, queue, visited_lock))
            for _ in range(MAX_CONCURRENT)
        ]

        await queue.join()

        for _ in workers:
            await queue.put(None)

        await asyncio.gather(*workers)

def start_crawl():
    """Start the crawling process from the base URL."""
    logger.info("Crawling started")
    asyncio.run(crawl(BASE_URL))
    logger.info("Total pages found: %d", len(visited_urls))
    logger.info("Total pages with content: %d", len(page_content))
    logger.info("Non canonic content page structure links: %s", non_canonic_content_urls)
    logger.info("Crawling ended")

    logger.info("Saving results in json")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(page_content, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    start_crawl()
