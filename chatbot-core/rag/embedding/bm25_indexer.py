"""
Module for the Sparse Retriever Class.
"""

from retriv import SparseRetriever
from api.config.loader import CONFIG
from utils import LoggerFactory

# pylint: disable=too-few-public-methods
class BM25Indexer:
    """
    Class that represents the indexer for the bm25 Sparse Retriever.
    """
    def __init__(self, index_configs, logger):
        """
        Initialize with a list of index configurations.
        Each config should be a dict with keys: 'index_name' and 'file_path'.
        """
        self.logger = logger
        self.index_configs = index_configs
        self.retrievers = {}

    def build(self):
        """
        Builds and stores retrievers by indexing the provided files.
        """
        for config in self.index_configs:
            retriever = self._index_config(config)
            if retriever:
                self.retrievers[config["index_name"]] = retriever

    def _index_config(self, config):
        """
        Indexes a single file and returns a SparseRetriever object.
        """
        index_name = config["index_name"]
        file_path = config["file_path"]

        sr = SparseRetriever(
            index_name=index_name,
            model="bm25",
            min_df=1,
            tokenizer="whitespace",
            stemmer="english",
            stopwords="english",
            do_lowercasing=True,
            do_ampersand_normalization=True,
            do_special_chars_normalization=True,
            do_acronyms_normalization=True,
            do_punctuation_removal=True
        )
        try:
            sr = sr.index_file(
                path=file_path,
                show_progress=True,
                callback=lambda doc: {
                    "id": doc["id"],
                    "text": doc["chunk_text"],
                }
            )

            return sr
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error("Error in creating the index for %s. Error: %s",
                                index_name, str(e))
            return None

    def get(self, index_name: str):
        """
        Loads a SparseRetriever for the given index name.
        If it's already created in this session, returns the cached one.
        Otherwise, loads it from disk.
        """
        if index_name in self.retrievers:
            return self.retrievers[index_name]

        try:
            sr = SparseRetriever.load(index_name)
            self.retrievers[index_name] = sr
            return sr
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.warning("Index '%s' not found or failed to load: %s", index_name, str(e))
            return None

indexer = BM25Indexer(
        index_configs=[
            {"index_name": "plugins", "file_path": "data/processed/chunks_plugin_docs.jsonl"},
            {"index_name": "docs", "file_path": "data/processed/chunks_docs.jsonl"}
        ],
        logger= LoggerFactory.instance().get_logger("bm25indexer")
    )

if not CONFIG["is_test_mode"]:
    indexer.build()
