"""Script to filter Discourse threads with accepted answers from a topic list."""

import json
import os
from utils import LoggerFactory

logger_factory = LoggerFactory.instance()
logger = logger_factory.get_logger("collection")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DISCOURSE_TOPIC_LIST_PATH = os.path.join(SCRIPT_DIR, "..", "..", "raw", "discourse_topic_list.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "..", "raw", "filtered_discourse_topics.json")

def filter_discourse_threads():
    """Filter topics that have accepted answers and exclude unanswered threads."""
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(DISCOURSE_TOPIC_LIST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

        accepted_answers = 0
        non_answered_topics = 0

        filtered_topics = []

        for topic in data.values():
            if topic["has_accepted_answer"]:
                accepted_answers += 1
                filtered_topics.append(topic)
            if topic["posts_count"] == 1:
                non_answered_topics += 1

        logger.info("There are %d answered topics over %d",
            len(data.keys()) - non_answered_topics,
            len(data.keys())
        )
        logger.info("There are %d topics with accepted answers over %d answered topics",
            accepted_answers,
            len(data.keys()) - non_answered_topics
        )

        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(filtered_topics, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    filter_discourse_threads()
