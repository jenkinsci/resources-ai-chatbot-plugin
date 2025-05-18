import json
import os

def filter_discourse_threads():
    output_path = "../../raw/filtered_discourse_topics.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open("../../raw/discourse_topic_list.json", "r", encoding="utf-8") as f:
        data = json.load(f)

        accepted_answers = 0
        non_answered_topics = 0

        filtered_topics = []

        for id, topic in data.items():
            if topic["has_accepted_answer"] == True:
                accepted_answers += 1
                filtered_topics.append(topic)
            if topic["posts_count"] == 1:
                non_answered_topics += 1

        print(f"There are {len(data.keys()) - non_answered_topics} answered topics over {len(data.keys())}")
        print(f"There are {accepted_answers} topics with accepted answers over {len(data.keys()) - non_answered_topics} answered topics")
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(filtered_topics, f, ensure_ascii=False, indent=2)