import json
import pandas as pd

# The QueryResults.csv is obtained by running the desired query on the data explorer tool of StackExchange
THREADS_CSV_PATH = "../../raw/QueryResults.csv" 
OUTPUT_JSON_PATH = "../../raw/stack_overflow_threads.json"

def convert_stack_threads():
    df = pd.read_csv(THREADS_CSV_PATH)

    data = df.to_dict(orient="records")

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    convert_stack_threads()
