"""Initialize the utils package by exposing key helper functions."""

from .filter_functions import (
    remove_container_by_class,
    remove_tags,
    extract_page_content_container,
    remove_html_comments,
    remove_edge_navigation_blocks,
    get_visible_text_length,
    strip_html_body_wrappers
)

from .split_doc_types import(
    split_type_docs
)
