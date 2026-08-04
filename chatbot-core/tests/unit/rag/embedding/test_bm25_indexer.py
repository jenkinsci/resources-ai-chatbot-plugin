"""Unit tests for rag/embedding/bm25_indexer.py"""
import unittest
from unittest.mock import MagicMock, patch


class TestBM25IndexerInit(unittest.TestCase):
    """Tests for BM25Indexer.__init__"""

    def test_init_stores_configs_and_logger(self):
        """Test that init correctly stores index_configs and logger."""
        from rag.embedding.bm25_indexer import BM25Indexer
        logger = MagicMock()
        configs = [{"index_name": "plugins", "file_path": "some/path.jsonl"}]
        indexer = BM25Indexer(configs, logger)
        self.assertEqual(indexer.index_configs, configs)
        self.assertEqual(indexer.logger, logger)
        self.assertEqual(indexer.retrievers, {})

    def test_init_empty_configs(self):
        """Test that init works with empty config list."""
        from rag.embedding.bm25_indexer import BM25Indexer
        logger = MagicMock()
        indexer = BM25Indexer([], logger)
        self.assertEqual(indexer.index_configs, [])
        self.assertEqual(indexer.retrievers, {})


class TestBM25IndexerBuild(unittest.TestCase):
    """Tests for BM25Indexer.build()"""

    def test_build_stores_retriever_for_valid_config(self):
        """Test that build() stores retriever when _index_config succeeds."""
        from rag.embedding.bm25_indexer import BM25Indexer
        logger = MagicMock()
        configs = [{"index_name": "plugins", "file_path": "some/path.jsonl"}]
        indexer = BM25Indexer(configs, logger)
        mock_retriever = MagicMock()
        indexer._index_config = MagicMock(return_value=mock_retriever)
        indexer.build()
        self.assertIn("plugins", indexer.retrievers)
        self.assertEqual(indexer.retrievers["plugins"], mock_retriever)

    def test_build_skips_config_when_index_config_returns_none(self):
        """Test that build() skips storing when _index_config returns None."""
        from rag.embedding.bm25_indexer import BM25Indexer
        logger = MagicMock()
        configs = [{"index_name": "plugins", "file_path": "some/path.jsonl"}]
        indexer = BM25Indexer(configs, logger)
        indexer._index_config = MagicMock(return_value=None)
        indexer.build()
        self.assertNotIn("plugins", indexer.retrievers)

    def test_build_handles_multiple_configs(self):
        """Test that build() processes multiple configs correctly."""
        from rag.embedding.bm25_indexer import BM25Indexer
        logger = MagicMock()
        configs = [
            {"index_name": "plugins", "file_path": "path1.jsonl"},
            {"index_name": "docs", "file_path": "path2.jsonl"},
        ]
        indexer = BM25Indexer(configs, logger)
        mock_retriever = MagicMock()
        indexer._index_config = MagicMock(return_value=mock_retriever)
        indexer.build()
        self.assertIn("plugins", indexer.retrievers)
        self.assertIn("docs", indexer.retrievers)

    def test_build_empty_configs_does_nothing(self):
        """Test that build() with empty configs leaves retrievers empty."""
        from rag.embedding.bm25_indexer import BM25Indexer
        logger = MagicMock()
        indexer = BM25Indexer([], logger)
        indexer.build()
        self.assertEqual(indexer.retrievers, {})


class TestBM25IndexerIndexConfig(unittest.TestCase):
    """Tests for BM25Indexer._index_config()"""

    def test_index_config_returns_none_when_sparse_retriever_unavailable(self):
        """Test that _index_config returns None when SparseRetriever is None."""
        from rag.embedding.bm25_indexer import BM25Indexer
        import rag.embedding.bm25_indexer as bm25_module
        logger = MagicMock()
        indexer = BM25Indexer([], logger)
        with patch.object(bm25_module, 'SparseRetriever', None):
            result = indexer._index_config(
                {"index_name": "test", "file_path": "test.jsonl"}
            )
        self.assertIsNone(result)

    def test_index_config_returns_none_on_exception(self):
        """Test that _index_config returns None and logs error on exception."""
        from rag.embedding.bm25_indexer import BM25Indexer
        import rag.embedding.bm25_indexer as bm25_module
        logger = MagicMock()
        indexer = BM25Indexer([], logger)
        mock_sr_instance = MagicMock()
        mock_sr_instance.index_file.side_effect = Exception("file not found")
        mock_sr_class = MagicMock(return_value=mock_sr_instance)
        with patch.object(bm25_module, 'SparseRetriever', mock_sr_class):
            result = indexer._index_config(
                {"index_name": "test", "file_path": "test.jsonl"}
            )
        self.assertIsNone(result)
        logger.error.assert_called_once()

    def test_index_config_returns_retriever_on_success(self):
        """Test that _index_config returns retriever on successful indexing."""
        from rag.embedding.bm25_indexer import BM25Indexer
        import rag.embedding.bm25_indexer as bm25_module
        logger = MagicMock()
        indexer = BM25Indexer([], logger)
        mock_sr_instance = MagicMock()
        mock_sr_instance.index_file.return_value = mock_sr_instance
        mock_sr_class = MagicMock(return_value=mock_sr_instance)
        with patch.object(bm25_module, 'SparseRetriever', mock_sr_class):
            result = indexer._index_config(
                {"index_name": "test", "file_path": "test.jsonl"}
            )
        self.assertIsNotNone(result)


class TestBM25IndexerGet(unittest.TestCase):
    """Tests for BM25Indexer.get()"""

    def test_get_returns_none_when_sparse_retriever_unavailable(self):
        """Test that get() returns None when SparseRetriever is None."""
        from rag.embedding.bm25_indexer import BM25Indexer
        import rag.embedding.bm25_indexer as bm25_module
        logger = MagicMock()
        indexer = BM25Indexer([], logger)
        with patch.object(bm25_module, 'SparseRetriever', None):
            result = indexer.get("plugins")
        self.assertIsNone(result)

    def test_get_returns_cached_retriever(self):
        """Test that get() returns cached retriever without loading from disk."""
        from rag.embedding.bm25_indexer import BM25Indexer
        logger = MagicMock()
        indexer = BM25Indexer([], logger)
        mock_retriever = MagicMock()
        indexer.retrievers["plugins"] = mock_retriever
        result = indexer.get("plugins")
        self.assertEqual(result, mock_retriever)

    def test_get_loads_from_disk_when_not_cached(self):
        """Test that get() loads retriever from disk when not in cache."""
        from rag.embedding.bm25_indexer import BM25Indexer
        import rag.embedding.bm25_indexer as bm25_module
        logger = MagicMock()
        indexer = BM25Indexer([], logger)
        mock_retriever = MagicMock()
        mock_sr_class = MagicMock()
        mock_sr_class.load.return_value = mock_retriever
        with patch.object(bm25_module, 'SparseRetriever', mock_sr_class):
            result = indexer.get("plugins")
        self.assertEqual(result, mock_retriever)
        self.assertIn("plugins", indexer.retrievers)

    def test_get_returns_none_when_load_fails(self):
        """Test that get() returns None and logs warning when load fails."""
        from rag.embedding.bm25_indexer import BM25Indexer
        import rag.embedding.bm25_indexer as bm25_module
        logger = MagicMock()
        indexer = BM25Indexer([], logger)
        mock_sr_class = MagicMock()
        mock_sr_class.load.side_effect = Exception("index not found")
        with patch.object(bm25_module, 'SparseRetriever', mock_sr_class):
            result = indexer.get("nonexistent")
        self.assertIsNone(result)
        logger.warning.assert_called_once()

    def test_get_caches_loaded_retriever(self):
        """Test that get() caches the retriever after loading from disk."""
        from rag.embedding.bm25_indexer import BM25Indexer
        import rag.embedding.bm25_indexer as bm25_module
        logger = MagicMock()
        indexer = BM25Indexer([], logger)
        mock_retriever = MagicMock()
        mock_sr_class = MagicMock()
        mock_sr_class.load.return_value = mock_retriever
        with patch.object(bm25_module, 'SparseRetriever', mock_sr_class):
            indexer.get("plugins")
        self.assertIn("plugins", indexer.retrievers)
        self.assertEqual(indexer.retrievers["plugins"], mock_retriever)


if __name__ == "__main__":
    unittest.main()