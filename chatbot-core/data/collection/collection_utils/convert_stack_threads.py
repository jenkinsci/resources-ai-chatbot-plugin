"""Script to convert Stack Overflow CSV thread data to a JSON format."""

import json
import os
import pandas as pd

# The QueryResults.csv is obtained by running the desired query
# on the data explorer tool of StackExchange
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
THREADS_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "..", "raw", "QueryResults.csv")
OUTPUT_JSON_PATH = os.path.join(SCRIPT_DIR, "..", "..", "raw", "stack_overflow_threads.json")

def convert_stack_threads():
    """Read CSV thread data and export it as a structured JSON file."""
    df = pd.read_csv(THREADS_CSV_PATH)

    data = df.to_dict(orient="records")

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    convert_stack_threads()
