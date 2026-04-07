"""Module for retrieving and filtering topics from the 'Using Jenkins' category on Discourse."""

import json
import os
import requests
from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("collection")

BASE_URL = "https://community.jenkins.io"
CATEGORY_SLUG = "using-jenkins"
CATEGORY_ID = 7 # 'Using Jenkins' Category
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "discourse_topic_list.json")


def fetch_page(category_slug, category_id, page):
    """Fetch a specific page of topics in a category."""
    if page != 0:
        url = f"{BASE_URL}/c/{category_slug}/{category_id}.json?page={page}"
    else:
        url = f"{BASE_URL}/c/{category_slug}/{category_id}.json"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def extract_topics(data):
    """Extract topics and more_topics_url from the response data."""
    topics = data["topic_list"]["topics"]
    more_topics_url = data["topic_list"].get("more_topics_url", "")
    return topics, more_topics_url

def get_wrong_and_correct_topics(topics):
    """Get the right and wrong topics with respect to the category. At the moment the 
        non desired picked category is the one with id 9, that represent a sub-category 
        of 'Using Jenkins'
    """
    right_topics = []
    wrong_topics = []
    for topic in topics:
        # 8 is the sub-category ask a question
        if topic["category_id"] == 7 or topic["category_id"] == 8:
            right_topics.append(topic)
        else:
            wrong_topics.append(topic)
    return right_topics, wrong_topics


def get_category_topics(category_slug, category_id):
    """Iterate through all topic pages in a category."""
    page = 0
    explored_pages = set()
    explored_topics = {}

    while True:
        logger.info("Fetching page %d...", page)
        data = fetch_page(category_slug, category_id, page)
        topics, more_topics_url = extract_topics(data)

        right_category_topics, wrong_category_topics = get_wrong_and_correct_topics(topics)

        logger.info("Page %d - Found %d topics", page, len(topics))
        logger.info("Right category Topics %d - Wrong category Topics %d",
            len(right_category_topics),
            len(wrong_category_topics)
        )

        for topic in right_category_topics:
            id_topic = topic["id"]
            if id_topic not in explored_topics:
                explored_topics[id_topic] = topic

        explored_pages.add(page)

        if not more_topics_url:
            logger.info("No more topics to explore.")
            break

        # Extract the next page number from the more_topics_url
        try:
            page = int(more_topics_url.split('page=')[-1])
        except (IndexError, ValueError):
            logger.error("Failed to parse next page number.")
            break

        if page in explored_pages:
            logger.info("Already explored page %d.", page)
            break

    logger.info("Explored %d topics", len(explored_topics.keys()))
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(explored_topics, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    get_category_topics(CATEGORY_SLUG, CATEGORY_ID)
