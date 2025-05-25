import requests
from bs4 import BeautifulSoup
import json

URL = "https://updates.jenkins.io/experimental/latest/"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "raw", "plugin_names.json")

def fetch_plugin_names():
    """
    Fetches a list of available plugin artifact names (.hpi) from the Jenkins update site.
    
    Returns:
        List[str]: List of raw plugin file names (e.g., 'git.hpi', 'docker-slaves.hpi').
    """
    print("Fetching plugin index page...")
    response = requests.get(URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    plugin_list = []
    ul = soup.find("ul", class_="artifact-list")
    if ul:
        for li in ul.find_all("li"):
            a_tag = li.find("a")
            if a_tag and "href" in a_tag.attrs:
                href = a_tag["href"]
                plugin_name = href.strip("/").strip()
                if plugin_name:
                    plugin_list.append(plugin_name)

    print(f"Found {len(plugin_list)} plugins.")
    return plugin_list

def save_plugin_names(plugin_names_with_extension):
    plugin_names = [plugin_name[0:-4] for plugin_name in plugin_names_with_extension]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(plugin_names, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(plugin_names)} plugin names to {OUTPUT_PATH}")

if __name__ == "__main__":
    plugins = fetch_plugin_names()
    save_plugin_names(plugins)
