"""
Utils function to convert a json file into a jsonl format.
"""

import json
import os

PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
INPUT_PATH = os.path.join(PROCESSED_DATA_DIR, "chunks_plugin_docs.json")
OUTPUT_PATH = os.path.join(PROCESSED_DATA_DIR, "chunks_plugin_docs.jsonl")

def convert_json_to_jsonl(input_file, output_file):
    """
    Function that given a json file, converts it to the jsonl format.
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(output_file, 'w', encoding='utf-8') as f:
        for item in data:
            json_line = json.dumps(item)
            f.write(json_line + '\n')

if __name__== "__main__":
    convert_json_to_jsonl(INPUT_PATH, OUTPUT_PATH)
