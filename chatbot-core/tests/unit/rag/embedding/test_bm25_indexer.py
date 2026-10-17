"""Unit tests for rag.embedding.bm25_indexer.BM25Indexer."""

import pytest

from rag.embedding import bm25_indexer
from rag.embedding.bm25_indexer import BM25Indexer

SPARSE_RETRIEVER = "rag.embedding.bm25_indexer.SparseRetriever"

BM25_SETTINGS = {
    "model": "bm25",
    "min_df": 1,
    "tokenizer": "whitespace",
    "stemmer": "english",
    "stopwords": "english",
    "do_lowercasing": True,
    "do_ampersand_normalization": True,
    "do_special_chars_normalization": True,
    "do_acronyms_normalization": True,
    "do_punctuation_removal": True,
}


def _config(index_name="plugins", file_path="data/chunks.jsonl"):
    """Build one indexer config mapping a name to a chunk file."""
    return {"index_name": index_name, "file_path": file_path}


def _make_indexer(mocker, configs=None):
    """Create an indexer with a mock logger and the given configs."""
    return BM25Indexer([] if configs is None else configs, mocker.Mock())


def test_init_stores_configs_logger_and_empty_cache(mocker):
    """__init__ keeps the supplied configs and logger and starts with no retrievers."""
    logger = mocker.Mock()
    configs = [_config("plugins"), _config("docs", "docs.jsonl")]

    indexer = BM25Indexer(configs, logger)

    assert indexer.index_configs == configs
    assert indexer.logger is logger
    assert not indexer.retrievers


def test_init_accepts_empty_config_list(mocker):
    """An empty config list is valid and does not invent retrievers."""
    indexer = _make_indexer(mocker, [])

    assert indexer.index_configs == []
    assert not indexer.retrievers


def test_build_stores_retriever_returned_by_index_config(mocker):
    """build() stores the retriever _index_config returns, keyed by index name."""
    indexer = _make_indexer(mocker, [_config()])
    retriever = mocker.Mock()
    mocker.patch.object(indexer, "_index_config", return_value=retriever)

    indexer.build()

    assert indexer.retrievers == {"plugins": retriever}


def test_build_skips_config_when_index_config_returns_none(mocker):
    """build() does not store a config when indexing returns None."""
    indexer = _make_indexer(mocker, [_config()])
    mocker.patch.object(indexer, "_index_config", return_value=None)

    indexer.build()

    assert not indexer.retrievers


def test_build_keeps_successful_indexes_when_another_returns_none(mocker):
    """A failed config does not drop indexes that were built successfully."""
    configs = [_config("plugins", "plugins.jsonl"), _config("docs", "docs.jsonl")]
    indexer = _make_indexer(mocker, configs)
    plugins = mocker.Mock()
    mocker.patch.object(indexer, "_index_config", side_effect=[plugins, None])

    indexer.build()

    assert indexer.retrievers == {"plugins": plugins}


def test_build_with_empty_configs_does_not_touch_sparse_retriever(mocker):
    """build() with no configs leaves the cache empty and never constructs a retriever."""
    sparse_cls = mocker.patch(SPARSE_RETRIEVER)
    indexer = _make_indexer(mocker, [])

    indexer.build()

    assert not indexer.retrievers
    sparse_cls.assert_not_called()


def test_build_overwrites_duplicate_index_names(mocker):
    """Later configs with the same index name replace the retriever stored earlier."""
    configs = [_config("plugins", "first.jsonl"), _config("plugins", "second.jsonl")]
    indexer = _make_indexer(mocker, configs)
    first = mocker.Mock()
    second = mocker.Mock()
    mocker.patch.object(indexer, "_index_config", side_effect=[first, second])

    indexer.build()

    assert indexer.retrievers == {"plugins": second}


def test_index_config_returns_none_when_sparse_retriever_unavailable(mocker):
    """_index_config returns None and does not log when SparseRetriever is missing."""
    mocker.patch(SPARSE_RETRIEVER, None)
    indexer = _make_indexer(mocker)

    result = indexer._index_config(_config())  # pylint: disable=protected-access

    assert result is None
    indexer.logger.error.assert_not_called()


def test_index_config_logs_and_returns_none_when_indexing_fails(mocker):
    """Indexing errors are logged and turned into a None retriever."""
    indexer = _make_indexer(mocker)
    instance = mocker.Mock()
    instance.index_file.side_effect = OSError("file not found")
    sparse_cls = mocker.patch(SPARSE_RETRIEVER, return_value=instance)

    result = indexer._index_config(_config())  # pylint: disable=protected-access

    assert result is None
    sparse_cls.assert_called_once_with(index_name="plugins", **BM25_SETTINGS)
    indexer.logger.error.assert_called_once_with(
        "Error in creating the index for %s. Error: %s",
        "plugins",
        "file not found",
    )


def test_index_config_returns_indexed_retriever(mocker):
    """A successful index_file result is the retriever _index_config returns."""
    indexer = _make_indexer(mocker)
    constructed = mocker.Mock()
    indexed = mocker.Mock()
    constructed.index_file.return_value = indexed
    mocker.patch(SPARSE_RETRIEVER, return_value=constructed)

    result = indexer._index_config(_config())  # pylint: disable=protected-access

    assert result is indexed


def test_index_config_passes_bm25_settings_and_document_callback(mocker):
    """Indexing uses BM25 settings and maps each chunk id and text into the index."""
    indexer = _make_indexer(mocker)
    constructed = mocker.Mock()
    indexed = mocker.Mock()
    captured = {}

    def index_file(path, show_progress, callback):
        captured["path"] = path
        captured["show_progress"] = show_progress
        captured["document"] = callback(
            {"id": "chunk-1", "chunk_text": "Jenkins agent"}
        )
        return indexed

    constructed.index_file.side_effect = index_file
    sparse_cls = mocker.patch(SPARSE_RETRIEVER, return_value=constructed)
    config = _config("docs", "data/processed/chunks_docs.jsonl")

    result = indexer._index_config(config)  # pylint: disable=protected-access

    assert result is indexed
    sparse_cls.assert_called_once_with(index_name="docs", **BM25_SETTINGS)
    assert captured == {
        "path": "data/processed/chunks_docs.jsonl",
        "show_progress": True,
        "document": {"id": "chunk-1", "text": "Jenkins agent"},
    }


def test_index_config_propagates_constructor_errors(mocker):
    """SparseRetriever construction sits outside the indexing try block."""
    mocker.patch(SPARSE_RETRIEVER, side_effect=RuntimeError("retriever init failed"))
    indexer = _make_indexer(mocker)

    with pytest.raises(RuntimeError, match="retriever init failed"):
        indexer._index_config(_config())  # pylint: disable=protected-access

    indexer.logger.error.assert_not_called()


def test_get_returns_none_when_sparse_retriever_unavailable(mocker):
    """get() returns None without reading the cache when SparseRetriever is missing."""
    mocker.patch(SPARSE_RETRIEVER, None)
    indexer = _make_indexer(mocker)
    indexer.retrievers["plugins"] = mocker.Mock()

    assert indexer.get("plugins") is None
    indexer.logger.warning.assert_not_called()


def test_get_returns_cached_retriever_without_loading(mocker):
    """An in-memory retriever is returned and SparseRetriever.load is not called."""
    sparse_cls = mocker.patch(SPARSE_RETRIEVER)
    indexer = _make_indexer(mocker)
    cached = mocker.Mock()
    indexer.retrievers["plugins"] = cached

    assert indexer.get("plugins") is cached
    sparse_cls.load.assert_not_called()


def test_get_loads_missing_index_from_disk_and_caches_it(mocker):
    """get() loads an uncached index from disk and stores it for later calls."""
    loaded = mocker.Mock()
    sparse_cls = mocker.patch(SPARSE_RETRIEVER)
    sparse_cls.load.return_value = loaded
    indexer = _make_indexer(mocker)

    assert indexer.get("plugins") is loaded
    assert indexer.get("plugins") is loaded

    sparse_cls.load.assert_called_once_with("plugins")
    assert indexer.retrievers["plugins"] is loaded


def test_get_returns_none_and_warns_when_load_fails(mocker):
    """A missing or unreadable index becomes None and a warning."""
    sparse_cls = mocker.patch(SPARSE_RETRIEVER)
    sparse_cls.load.side_effect = FileNotFoundError("index not found")
    indexer = _make_indexer(mocker)

    assert indexer.get("missing") is None
    indexer.logger.warning.assert_called_once_with(
        "Index '%s' not found or failed to load: %s",
        "missing",
        "index not found",
    )


def test_get_does_not_cache_failed_load(mocker):
    """A failed load is not cached, so a later get() tries the disk again."""
    sparse_cls = mocker.patch(SPARSE_RETRIEVER)
    sparse_cls.load.side_effect = FileNotFoundError("index not found")
    indexer = _make_indexer(mocker)

    assert indexer.get("plugins") is None
    assert indexer.get("plugins") is None

    assert sparse_cls.load.call_count == 2
    assert "plugins" not in indexer.retrievers


def test_get_empty_index_name_is_forwarded_to_load(mocker):
    """An empty index name is not special-cased; load receives it unchanged."""
    loaded = mocker.Mock()
    sparse_cls = mocker.patch(SPARSE_RETRIEVER)
    sparse_cls.load.return_value = loaded
    indexer = _make_indexer(mocker)

    assert indexer.get("") is loaded
    sparse_cls.load.assert_called_once_with("")
    assert indexer.retrievers[""] is loaded


def test_module_indexer_registers_default_sources():
    """The module indexer is wired to the plugins, docs, and discourse chunk files."""
    configs = bm25_indexer.indexer.index_configs

    assert [config["index_name"] for config in configs] == [
        "plugins",
        "docs",
        "discourse",
    ]
    assert [config["file_path"] for config in configs] == [
        "data/processed/chunks_plugin_docs.jsonl",
        "data/processed/chunks_docs.jsonl",
        "data/processed/chunks_discourse_docs.jsonl",
    ]
