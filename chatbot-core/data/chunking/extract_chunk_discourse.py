"""Chunk Discourse threads into structured content blocks with metadata."""
# pylint: disable=R0801

import re
from data.chunking.base_chunker import BaseChunker
from data.chunking.chunking_utils import(
    assign_code_blocks_to_chunks,
    build_chunk_dict,
)

class DiscourseChunker(BaseChunker):
    """Chunks Discourse threads."""

    def __init__(self):
        """Initializes the DiscourseChunker."""
        super().__init__(
            source_name="Discourse Threads",
            input_file="raw/topics_with_posts.json",
            output_file="chunks_discourse_docs.json"
        )
        self.code_block_placeholder_pattern = r"\[\[(?:CODE_BLOCK|CODE_SNIPPET)_(\d+)\]\]"
        self.triple_backtick_code_pattern = r"```(?:\w+\n)?(.*?)```"
        self.inline_backtick_code_pattern = r"`([^`\n]+?)`"

    def extract_code_blocks(self, text):
        """
        Extracts code blocks and replaces them with indexed placeholders.
        Supports both triple-backtick code blocks and inline code in backticks.

        Args:
            text (str): Raw text including code blocks.

        Returns:
            tuple: (List of extracted code blocks, modified text with placeholders).
        """
        code_blocks = []
        placeholder_counter = 0

        def replace_triple(match):
            nonlocal placeholder_counter
            code = match.group(1).strip()
            placeholder = f"[[CODE_BLOCK_{placeholder_counter}]]"
            code_blocks.append(code)
            placeholder_counter += 1
            return placeholder

        text = re.sub(self.triple_backtick_code_pattern, replace_triple, text, flags=re.DOTALL)

        def replace_inline(match):
            nonlocal placeholder_counter
            code = match.group(1).strip()
            placeholder = f"[[CODE_SNIPPET_{placeholder_counter}]]"
            code_blocks.append(code)
            placeholder_counter += 1
            return placeholder

        text = re.sub(self.inline_backtick_code_pattern, replace_inline, text)

        return code_blocks, text

    def extract_chunks(self, items):
        """
        Processes all Discourse threads into a flat list of chunks.

        Args:
            items (list): List of Discourse thread dicts.

        Returns:
            list[dict]: All chunks extracted from all threads.
        """
        all_chunks = []
        for thread in items:
            thread_chunks = self.process_thread(thread)
            all_chunks.extend(thread_chunks)
        return all_chunks

    def process_thread(self, thread):
        """
        Processes a single Discourse thread into structured chunks.

        Args:
            thread (dict): Thread data including topic ID, title, and post texts.

        Returns:
            list[dict]: List of chunk objects for the thread.
        """
        topic_id = thread.get("topic_id")
        title = thread.get("title", "Untitled")
        posts = thread.get("posts", [])
        full_text = "\n\n".join(posts)

        code_blocks, clean_text = self.extract_code_blocks(full_text)
        chunks = self.text_splitter.split_text(clean_text)

        processed_chunks = assign_code_blocks_to_chunks(
            chunks, code_blocks, self.code_block_placeholder_pattern, self.logger
        )

        return [
            build_chunk_dict(
                chunk["chunk_text"],
                {"data_source": "discourse_threads", "topic_id": topic_id, "title": title},
                chunk["code_blocks"]
            )
            for chunk in processed_chunks
        ]

def main():
    """Main entry point."""
    chunker = DiscourseChunker()
    chunker.run()

if __name__ == "__main__":
    main()
