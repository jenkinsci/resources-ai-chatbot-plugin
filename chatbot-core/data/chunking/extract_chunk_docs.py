"""Script to chunk Jenkins HTML documentation into text blocks with metadata."""
# pylint: disable=R0801

from bs4 import BeautifulSoup
from data.chunking.base_chunker import BaseChunker
from data.chunking.chunking_utils import(
    extract_code_blocks,
    extract_title,
    assign_code_blocks_to_chunks,
    build_chunk_dict,
)

class DocsChunker(BaseChunker):
    """Chunks Jenkins HTML documentation."""

    def __init__(self):
        """Initializes the DocsChunker."""
        super().__init__(
            source_name="Jenkins Docs",
            input_file="processed/filtered_jenkins_docs.json",
            output_file="chunks_docs.json"
        )

    def extract_chunks(self, items):
        """
        Processes all Jenkins documentation pages by chunking their content.

        Args:
            items (dict): A dictionary mapping URLs to raw HTML strings.

        Returns:
            list[dict]: A list of all processed chunks across all docs.
        """
        all_chunks = []
        for url, html in items.items():
            page_chunks = self.process_page(url, html)
            all_chunks.extend(page_chunks)
        return all_chunks

    def process_page(self, url, html):
        """
        Processes a single Jenkins documentation page.

        Args:
            url (str): Source URL of the documentation page.
            html (str): Raw HTML content of the page.

        Returns:
            list[dict]: A list of chunk dictionaries for the page.
        """
        soup = BeautifulSoup(html, "html.parser")
        title = extract_title(soup)
        code_blocks = extract_code_blocks(soup, "pre", self.PLACEHOLDER_TEMPLATE)

        text = soup.get_text(separator="\n", strip=True)
        if code_blocks and self.PLACEHOLDER_TEMPLATE.format(0) not in text:
            self.logger.warning(
                "Extracted %d code blocks for %s but no placeholders found in text.",
                len(code_blocks),
                url
            )
        chunks = self.text_splitter.split_text(text)

        processed_chunks = assign_code_blocks_to_chunks(
            chunks,
            code_blocks,
            self.CODE_BLOCK_PLACEHOLDER_PATTERN,
            self.logger
        )

        return [
            build_chunk_dict(
                chunk["chunk_text"],
                {
                    "data_source": "jenkins_documentation",
                    "source_url": url,
                    "title": title
                },
                chunk["code_blocks"]
            )
            for chunk in processed_chunks
        ]

def main():
    """Main entry point."""
    chunker = DocsChunker()
    chunker.run()

if __name__ == "__main__":
    main()
