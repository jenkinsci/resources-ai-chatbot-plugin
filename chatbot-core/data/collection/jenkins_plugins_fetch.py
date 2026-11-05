"""Script to fetch and store documentation content for Jenkins plugins."""
import asyncio
import json
import os

import httpx
from bs4 import BeautifulSoup

from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("collection")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "plugin_names.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "plugin_docs.json")
BASE_URL = "https://plugins.jenkins.io"


async def fetch_plugin_content(client, plugin_name, semaphore, retries=3):
    """
    Fetches the main documentation content asynchronously using a shared client and semaphore.
    """
    # The semaphore ensures we don't overwhelm the Jenkins servers
    async with semaphore:
        url = f"https://plugins.jenkins.io/{plugin_name}/"
        for attempt in range(retries):
            try:
                response = await client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")
                content_div = soup.find("div", class_="content")
                if content_div:
                    return plugin_name, str(content_div)

                logger.warning("No content found for %s", plugin_name)
                return plugin_name, None

            # 1. Catch HTTP Status errors (like 404 or 500)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Instantly skip dead links without retrying
                    logger.warning(
                        "Dead link (404) for %s. Skipping.", plugin_name)
                    return plugin_name, None

                logger.error("HTTP error fetching %s (attempt %d): %s",
                             plugin_name, attempt + 1, e)
                await asyncio.sleep(1.5 * (attempt + 1))

            # 2. Catch actual network failures (Timeouts, disconnected internet)
            except httpx.RequestError as e:
                logger.error(
                    "Network error fetching %s (attempt %d): %s", plugin_name, attempt + 1, e)
                await asyncio.sleep(1.5 * (attempt + 1))

        logger.error("Failed to fetch %s after %d attempts",
                     plugin_name, retries)
        return plugin_name, None


async def collect_plugin_docs(plugin_names):
    """
    Creates the async tasks and executes them concurrently.
    """
    result = {}

    # Limit concurrent network requests to 15 at a time to prevent rate-limiting
    semaphore = asyncio.Semaphore(15)

    # Reusing one AsyncClient for all requests is significantly faster than
    # opening a new one each time
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Create a list of tasks (they don't run yet)
        tasks = [
            fetch_plugin_content(client, plugin_name, semaphore)
            for plugin_name in plugin_names
        ]

        # asyncio.gather fires all the tasks concurrently
        logger.info("Executing %d async requests...", len(tasks))
        responses = await asyncio.gather(*tasks)

        # Responses come back in a list of tuples: [(plugin_name, content), ...]
        for plugin_name, content in responses:
            if content:
                result[plugin_name] = content

    return result


async def main():
    """
    Loads plugin names, collects documentation asynchronously, and writes it to a JSON file.
    """
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        plugin_names = json.load(f)

    logger.info(
        "Loaded %d plugin names. Starting concurrent fetch...", len(plugin_names))
    collected_docs = await collect_plugin_docs(plugin_names)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(collected_docs, f, indent=2, ensure_ascii=False)

    logger.info("Saved %d plugins to %s", len(collected_docs), OUTPUT_PATH)

if __name__ == "__main__":
    # Boot up the async event loop
    asyncio.run(main())
