"""Chunk StackOverflow threads into structured blocks with metadata."""
# pylint: disable=R0801

from bs4 import BeautifulSoup
from data.chunking.base_chunker import BaseChunker
from data.chunking.chunking_utils import(
    extract_code_blocks,
    assign_code_blocks_to_chunks,
    build_chunk_dict,
)

class StackOverflowChunker(BaseChunker):
    """Chunks StackOverflow threads."""

    def __init__(self):
        """Initializes the StackOverflowChunker."""
        super().__init__(
            source_name="StackOverflow Threads",
            input_file="raw/stack_overflow_threads.json",
            output_file="chunks_stackoverflow_threads.json"
        )
        self.placeholder_template = "[[CODE_BLOCK_{}]]"
        self.code_block_placeholder_pattern = r"\[\[CODE_BLOCK_(\d+)\]\]"

    def extract_chunks(self, items):
        """
        Processes a list of StackOverflow threads into structured chunks.

        Args:
            items (list): List of StackOverflow thread dicts.

        Returns:
            list[dict]: All extracted chunks from all threads.
        """
        all_chunks = []
        for thread in items:
            chunks = self.process_thread(thread)
            all_chunks.extend(chunks)
        return all_chunks

    def process_thread(self, thread):
        """
        Processes a single StackOverflow Q&A thread.

        Args:
            thread (dict): StackOverflow thread dictionary.

        Returns:
            list[dict]: List of chunk objects with text, metadata, and code blocks.
        """
        question_id = thread.get("Question ID")
        question_body = thread.get("Question Body", "")
        answer_body = thread.get("Answer Body", "")

        if not question_body or not answer_body:
            self.logger.warning(
                "Question %s is missing question/answer content. Extracting 0 chunks from it.",
                question_id
            )
            return []

        question_and_answer = f"<div>{question_body}</div><div>{answer_body}</div>"
        soup = BeautifulSoup(question_and_answer, "lxml")

        code_blocks = extract_code_blocks(soup, "code", self.placeholder_template)

        full_text = soup.get_text(separator="\n", strip=True)

        chunks = self.text_splitter.split_text(full_text)
        processed_chunks = assign_code_blocks_to_chunks(
            chunks,
            code_blocks,
            self.code_block_placeholder_pattern,
            self.logger
        )

        return [
            build_chunk_dict(
                chunk["chunk_text"],
                {
                    "data_source": "stackoverflow_threads",
                    "question_id": question_id,
                    "title": thread.get("Question Title", "Untitled"),
                    "tags": thread.get("Tags", ""),
                    "creation_date": thread.get("CreationDate", ""),
                    "question_score": thread.get("Question Score", 0),
                    "answer_score": thread.get("Answer Score", 0)
                },
                chunk["code_blocks"]
            )
            for chunk in processed_chunks
        ]

def main():
    """Main entry point."""
    chunker = StackOverflowChunker()
    chunker.run()

if __name__ == "__main__":
    main()
