"""Module to fetch posts from Jenkins Discourse topics."""

import os
import json
import requests
from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("collection")

BASE_URL = "https://community.jenkins.io"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(SCRIPT_DIR, "..", "raw", "topics_with_posts.json")
FILTERED_TOPICS_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "filtered_discourse_topics.json")

def fetch_topic_posts(topic_id):
    """Fetch all posts in a topic using the topic endpoint."""
    url = f"{BASE_URL}/t/{topic_id}.json"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    topic_data = response.json()

    post_ids = [post["id"] for post in topic_data["post_stream"]["posts"]]
    return post_ids

def fetch_post_content(post_id):
    """Fetch the content of a single post."""
    url = f"{BASE_URL}/posts/{post_id}.json"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    post_data = response.json()
    return post_data.get("raw", "")

def process_topics(topics):
    """Process each topic to fetch posts and save the data structure."""
    result = []

    for idx, topic in enumerate(topics):
        topic_id = topic["id"]
        logger.info("Processing topicId: %d... Progress at %.2f%%",
            topic_id,
            (idx / len(topics)) * 100
        )
        try:
            post_ids = fetch_topic_posts(topic_id)
            posts_content = [fetch_post_content(post_id) for post_id in post_ids]

            result.append({
                "topic_id": topic_id,
                "title": topic["title"],
                "posts": posts_content
            })
        except requests.HTTPError as e:
            logger.error("Error fetching topic %d: %s", topic_id, e)

    return result

def main():
    """Main entry point."""
    topics = []
    with open(FILTERED_TOPICS_PATH, "r", encoding="utf-8") as f:
        topics = json.load(f)

    data = process_topics(topics)

    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info("Data saved to %s", FILE_NAME)

if __name__ == "__main__":
    main()
