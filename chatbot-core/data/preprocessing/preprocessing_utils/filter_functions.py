"""Utility functions for parsing and cleaning HTML content using BeautifulSoup."""

from bs4 import BeautifulSoup, Comment

def extract_page_content_container(soup, class_name):
    """
    Extracts the HTML content of the first div with the given class name.

    Parameters:
    - soup (BeautifulSoup): Parsed HTML document.
    - class_name (str): Class name of the div to extract.

    Returns:
    - str: HTML string of the matching div, or empty string if not found.
    """
    content_div = soup.find("div", class_=class_name)
    if content_div:
        return str(content_div)
    return ""


def remove_container_by_class(content, class_name):
    """
    Given HTML content and a class name, removes the content inside the div
    with that class name and returns the remaining HTML.

    Parameters:
    - content (str): HTML string.
    - class_name (str): Class name of the div to extract.

    Returns:
    - str: HTML filtered from the div with class class_name.
    """
    soup = BeautifulSoup(content, "lxml")
    content_div = soup.find("div", class_=class_name)

    if content_div:
        content_div.decompose()

    return str(soup)

def remove_tags(content, tags_to_remove=None):
    """
    Removes all specified tags from the given HTML content.
    
    Parameters:
    - content (str): The HTML string to clean.
    - tags_to_remove (list of str): Tag names to remove (e.g., ["img", "script"]).
    
    Returns:
    - str: Cleaned HTML content with specified tags removed.
    """
    if tags_to_remove is None:
        tags_to_remove = ["img", "script", "style", "iframe", "object", "embed", "form"]

    soup = BeautifulSoup(content, "lxml")

    for tag in tags_to_remove:
        for element in soup.find_all(tag):
            element.decompose()

    return str(soup)

def remove_edge_navigation_blocks(content):
    """
    Removes the first navigation block and the last one (plus any following elements)
    from the direct children of `.col-lg-9`, based on expected structure.

    Parameters:
    - content (str): HTML string.

    Returns:
    - str: HTML filtered from any not wanted navigation elements.
    """
    soup = BeautifulSoup(content, "lxml")
    container = soup.find("div", class_="col-lg-9")
    if not container:
        return str(soup)

    def is_navigation_block(div):
        if div.name != "div":
            return False
        children = div.find_all(recursive=False)
        return (
            len(children) == 1 and
            children[0].name == "div" and
            "row" in children[0].get("class", []) and
            "body" not in children[0].get("class", [])
        )

    # Remove top navigation block
    children = container.find_all(recursive=False)
    if children and is_navigation_block(children[0]):
        children[0].decompose()

    # Refresh children and find bottom nav (and remove everything after it)
    children = container.find_all(recursive=False)
    is_navigation_block_found = False
    for i, div in enumerate(children):
        if is_navigation_block(div) or (div.name == "div" and div.get("id") == "feedback"):
            for div_to_remove in children[i:]:
                div_to_remove.extract()
            is_navigation_block_found = True
            break

    if not is_navigation_block_found:
        feedback_div = container.find("div", id="feedback")
        if feedback_div:
            feedback_div.decompose()

    return str(soup)

def remove_html_comments(content):
    """
    Removes all HTML comments from the given HTML content string.

    Parameters:
    - content (str): HTML string.

    Returns:
    - str: HTML with all comments removed.
    """
    soup = BeautifulSoup(content, "lxml")

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    return str(soup)

def get_visible_text_length(html_content):
    """
    Calculates the length of visible text in the HTML content.

    Parameters:
    - html_content (str): Raw HTML content.

    Returns:
    - int: Number of visible text characters.
    """
    soup = BeautifulSoup(html_content, "lxml")
    text = soup.get_text(separator=" ", strip=True)
    return len(text)

def strip_html_body_wrappers(html):
    """
    Removes the <html> and <body> wrapper tags from the given HTML content,
    returning only the contents within the <body> tag.

    Parameters:
    - html (str): HTML string, typically a fragment that may have been wrapped by a parser.

    Returns:
    - str: HTML string containing only the inner contents of the <body> tag,
           or the full HTML if no <body> is present.
    """
    soup = BeautifulSoup(html, "lxml")
    return ''.join(str(child) for child in soup.body.contents) if soup.body else str(soup)
