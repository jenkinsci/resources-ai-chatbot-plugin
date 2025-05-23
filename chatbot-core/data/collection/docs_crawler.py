import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json

# Home URL of jenkins doc
BASE_URL = "https://www.jenkins.io/doc/"

# Set to check for duplicates
visited_urls = set()

# Key: url ; Value: content of that page
page_content = {}

# Number of failed links
failed_links = 0

non_canonic_content_urls = set()

def is_valid_url(url):
    """Check if the URL is a valid link to a new page, internal to the doc, or a redirect to another page"""
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and BASE_URL in url and "#" not in url

def extract_page_content_container(soup):
    """Extract content from the 'container' div class"""
    content_div = soup.find("div", class_="container")
    if content_div:
        return str(content_div)
    return ""


def crawl(url):
    """Recursively crawl documentation pages starting from the base URL"""

    global failed_links
    
    # Avoid multiple visits
    if url in visited_urls:
        return
    
    print(f"Visiting: {url}") 
    try:
        visited_urls.add(url)

        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        content = extract_page_content_container(soup)
        if content:
            page_content[url] = content
        else:
            non_canonic_content_urls.add(url)
        
        # Find all links in the page
        links = soup.find_all("a", href=True)
        if '.html' not in url and not url.endswith('/'):
            url += '/'
        
        for link in links:
            href = link['href']
            full_url = urljoin(url, href)
            if is_valid_url(full_url):
                crawl(full_url)
    
    except requests.RequestException as e:
        failed_links += 1
        print(f"Error accessing {url}: {e}")

def start_crawl():
    """Start the crawling process from the base URL."""
    print("Crawling started")
    crawl(BASE_URL)
    print(f"Total pages found: {len(visited_urls)}")
    print(f"Total pages with content: {len(page_content)}")
    print(f"Number of bad links: {failed_links}")
    print("Non canonic content page structure links:")
    print(non_canonic_content_urls)
    print("Crawling ended")

    print("Saving results in json")
    with open("../raw/jenkins_docs.json", "w", encoding="utf-8") as f:
        json.dump(page_content, f, ensure_ascii=False, indent=2)
        
if __name__ == "__main__":
    start_crawl()
