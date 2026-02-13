"""Chunk Jenkins plugin HTML docs into structured text blocks with metadata."""
# pylint: disable=R0801

from bs4 import BeautifulSoup
from data.chunking.base_chunker import BaseChunker
from data.chunking.chunking_utils import(
    extract_code_blocks,
    assign_code_blocks_to_chunks,
    build_chunk_dict,
)

class PluginsChunker(BaseChunker):
    """Chunks Jenkins plugin documentation."""

    def __init__(self):
        """Initializes the PluginsChunker."""
        super().__init__(
            source_name="Jenkins Plugins",
            input_file="processed/processed_plugin_docs.json",
            output_file="chunks_plugin_docs.json"
        )
        self.placeholder_template = "[[CODE_BLOCK_{}]]"
        self.code_block_placeholder_pattern = r"\[\[CODE_BLOCK_(\d+)\]\]"

    def extract_chunks(self, items):
        """
        Process all Jenkins plugin documentation files by extracting and chunking them.

        Args:
            items (dict): Mapping from plugin name to HTML content.

        Returns:
            list[dict]: All processed chunks for all plugins.
        """
        all_chunks = []
        for plugin_name, html in items.items():
            plugin_chunks = self.process_plugin(plugin_name, html)
            all_chunks.extend(plugin_chunks)
        return all_chunks

    def process_plugin(self, plugin_name, html):
        """
        Process a single Jenkins plugin documentation HTML.

        Args:
            plugin_name (str): Name of the Jenkins plugin.
            html (str): Raw HTML content of the plugin documentation.

        Returns:
            list[dict]: List of chunk dictionaries.
        """
        soup = BeautifulSoup(html, "lxml")
        code_blocks = extract_code_blocks(soup, "pre", self.placeholder_template)

        text = soup.get_text(separator="\n", strip=True)
        if code_blocks and self.placeholder_template.format(0) not in text:
            self.logger.warning(
                "Extracted %d code blocks for %s but no placeholders found in text.",
                len(code_blocks),
                plugin_name
            )
        chunks = self.text_splitter.split_text(text)

        processed_chunks = assign_code_blocks_to_chunks(
            chunks,
            code_blocks,
            self.code_block_placeholder_pattern,
            self.logger
        )

        return [
            build_chunk_dict(
                chunk["chunk_text"],
                {"data_source": "jenkins_plugins_documentation", "title": plugin_name},
                chunk["code_blocks"]
            )
            for chunk in processed_chunks
        ]

def main():
    """Main entry point."""
    chunker = PluginsChunker()
    chunker.run()

if __name__ == "__main__":
    main()
