"""Module to fetch posts from Jenkins Discourse topics."""

import json
import requests

BASE_URL = "https://community.jenkins.io"
FILE_NAME = "../raw/topics_with_posts.json"
FILTERED_TOPICS_PATH = "../raw/filtered_discourse_topics.json"


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
        print(f"Processing topicId: {topic_id}... Progress at {round((idx/len(topics)) * 100, 2)}%")
        try:
            post_ids = fetch_topic_posts(topic_id)
            posts_content = [fetch_post_content(post_id) for post_id in post_ids]

            result.append({
                "topic_id": topic_id,
                "title": topic["title"],
                "posts": posts_content
            })
        except requests.HTTPError as e:
            print(f"Error fetching topic {topic_id}: {e}")

    return result

def main():
    """Main entry point."""
    topics = []
    with open(FILTERED_TOPICS_PATH, "r", encoding="utf-8") as f:
        topics = json.load(f)

    data = process_topics(topics)

    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Data saved to {FILE_NAME}")

if __name__ == "__main__":
    main()
