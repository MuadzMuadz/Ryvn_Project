"""Tests for raven.rag.indexer."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_embedder():
    """Mock the APIEmbedder so tests don't need a real embedding endpoint."""
    with patch("raven.rag.vectorstore.APIEmbedder") as cls:
        instance = MagicMock()
        # Return fake 384-dim embeddings
        instance.embed.side_effect = lambda texts: [[0.1] * 384 for _ in texts]
        cls.return_value = instance
        yield instance


@pytest.fixture
def _isolated_indexer(tmp_chroma_dir, tmp_watch_path, tmp_path, monkeypatch, mock_embedder):
    """Reload config + vectorstore with isolated dirs and mocked embedder."""
    import importlib

    import raven.config as cfg

    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_chroma_dir))
    monkeypatch.setenv("WATCH_PATHS", str(tmp_watch_path))
    importlib.reload(cfg)
    # Isolate the indexer's state file. FileIndexer persists hashes in
    # INDEXED_DIR/index_state.json; without this the suite shares the real
    # data/indexed/ file, and because pytest reuses tmp dir names across runs the
    # cached hash makes index_file() return 0 ("unchanged") -> flaky failures.
    import raven.rag.indexer as ix_mod

    indexed_dir = tmp_path / "indexed"
    indexed_dir.mkdir()
    monkeypatch.setattr(ix_mod, "INDEXED_DIR", indexed_dir)
    # Reset vectorstore singleton so it uses tmp dir
    import raven.rag.vectorstore as vs_mod

    vs_mod._instance = None


def test_indexer_txt_file(sample_txt: Path, _isolated_indexer):
    from raven.rag.indexer import FileIndexer

    idx = FileIndexer()
    n = idx.index_file(sample_txt)
    assert n > 0


def test_indexer_skip_unchanged(sample_txt: Path, _isolated_indexer):
    from raven.rag.indexer import FileIndexer

    idx = FileIndexer()
    n1 = idx.index_file(sample_txt)
    n2 = idx.index_file(sample_txt)
    assert n1 > 0
    assert n2 == 0  # hash unchanged -> skip


def test_indexer_directory(
    tmp_watch_path: Path, sample_txt: Path, sample_md: Path, _isolated_indexer
):
    from raven.rag.indexer import FileIndexer

    idx = FileIndexer()
    n = idx.index_directory(tmp_watch_path)
    assert n >= 2  # at least both files produced chunks


def test_chunking_produces_output():
    from raven.rag.indexer import _chunk

    text = " ".join(f"word{i}" for i in range(1000))
    chunks = _chunk(text)
    assert len(chunks) >= 2


def test_file_hash_streaming(tmp_path: Path):
    """Streaming hash produces consistent results."""
    from raven.rag.indexer import _file_hash

    f = tmp_path / "test.bin"
    f.write_bytes(b"hello world" * 1000)
    h1 = _file_hash(f)
    h2 = _file_hash(f)
    assert h1 == h2
    assert len(h1) == 16
