"""Utility to split documentation pages into developer and non-developer categories."""

from bs4 import BeautifulSoup

def extract_page_content_container(soup, class_name):
    """
    Checks if a div with the given class name exists in the HTML.

    Parameters:
    - soup (BeautifulSoup): Parsed HTML document.
    - class_name (str): Class name of the div to check.

    Returns:
    - bool: True if the div exists, False otherwise.
    """
    content_div = soup.find("div", class_=class_name)
    return bool(content_div)

def split_type_docs(data, logger):
    """
    Splits documentation pages into developer and non-developer types
    based on the presence of specific container classes.

    Parameters:
    - data (dict): Dictionary where keys are URLs and values are HTML content.

    Returns:
    - tuple: (developer_urls, non_developer_urls), both as lists of URLs.
    """
    logger.info("There are %d pages", len(data))

    non_developer_urls = []
    developer_urls = []
    soups = {}

    # Every doc page that is not in the /developer part has the content in the col-lg-9 class
    for url, content in data.items():
        soup = BeautifulSoup(content, "lxml")
        if extract_page_content_container(soup, "col-lg-9"):
            non_developer_urls.append(url)
        else:
            soups[url] = soup

    logger.info("Non-developer docs (col-lg-9): %d", len(non_developer_urls))

    # Every doc page that is in the /developer part has the content in the col-8 class
    for url, soup_c in soups.items():
        if extract_page_content_container(soup_c, "col-8"):
            developer_urls.append(url)

    logger.info("Developer docs (col-8): %d", len(developer_urls))

    return developer_urls, non_developer_urls
