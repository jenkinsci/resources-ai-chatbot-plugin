import requests
import json
from bs4 import BeautifulSoup
import os
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "plugin_names.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "plugin_docs.json")
BASE_URL = "https://plugins.jenkins.io"

def fetch_plugin_content(plugin_name, retries=3):
    """
    Fetches the main documentation content from the plugin's page on plugins.jenkins.io.
    
    Retries the request up to `retries` times if network issues occur.
    
    Args:
        plugin_name (str): The name of the plugin.
        retries (int): Number of retry attempts on failure.
        
    Returns:
        str or None: The HTML content of the plugin's <div class="content">, or None if not found or failed.
    """
    url = f"https://plugins.jenkins.io/{plugin_name}/"
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            content_div = soup.find("div", class_="content")
            if content_div:
                return str(content_div)
            else:
                print(f"No content found for {plugin_name}")
                return None

        except requests.RequestException as e:
            print(f"Error fetching {plugin_name} (attempt {attempt + 1}): {e}")
            time.sleep(1.5 * (attempt + 1))

    print(f"Failed to fetch {plugin_name} after {retries} attempts")
    return None

def collect_plugin_docs(plugin_names):
    """
    Iterates through all plugin names and collects their documentation content.
    
    Args:
        plugin_names (List[str]): List of plugin names to fetch.
        
    Returns:
        dict: A dictionary mapping plugin names to their extracted HTML content.
    """
    result = {}
    for idx, plugin_name in enumerate(plugin_names):
        print(f"[{idx+1}/{len(plugin_names)}] Fetching {plugin_name}...")
        content = fetch_plugin_content(plugin_name)
        if content:
            result[plugin_name] = content
    return result

def main():
    """
    Loads plugin names, collects documentation, and writes it to a JSON file.
    """
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        plugin_names = json.load(f)

    collected_docs = collect_plugin_docs(plugin_names)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(collected_docs, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(collected_docs)} plugins to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
