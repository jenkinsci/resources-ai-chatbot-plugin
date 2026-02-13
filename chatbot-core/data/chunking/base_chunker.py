"""Defines the base class for all data source chunkers."""

import os
from abc import ABC, abstractmethod
from data.chunking.chunking_utils import get_text_splitter, read_json_file, save_chunks
from utils import LoggerFactory

class BaseChunker(ABC):
    """Abstract base class for chunking different data sources."""

    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 100

    def __init__(self, source_name, input_file, output_file):
        """Initializes the BaseChunker."""
        self.source_name = source_name
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.input_path = os.path.join(self.script_dir, "..", input_file)
        self.output_path = os.path.join(self.script_dir, "..", "processed", output_file)
        self.text_splitter = get_text_splitter(self.CHUNK_SIZE, self.CHUNK_OVERLAP)
        self.logger = LoggerFactory.instance().get_logger("chunking")

    @abstractmethod
    def extract_chunks(self, items):
        """Processes all items from the input file and returns a list of chunks."""

    def run(self):
        """Main execution logic: read, chunk, and save."""
        items = read_json_file(self.input_path, self.logger)
        if not items:
            self.logger.warning("No items found in %s. Exiting.", self.input_path)
            return

        self.logger.info("Starting chunking for %s from %d items.", self.source_name, len(items))
        all_chunks = self.extract_chunks(items)
        save_chunks(self.output_path, all_chunks, self.logger)
