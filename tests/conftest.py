"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Set env vars BEFORE importing raven modules
os.environ.setdefault("API_KEY", "test-key-123")
os.environ.setdefault("WATCH_PATHS", "/tmp/raven-test-watch")
os.environ.setdefault("QDRANT_URL", ":memory:")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("OPENAI_BASE_URL", "http://localhost:4000/v1")


@pytest.fixture
def qdrant_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the vector store to an isolated in-memory Qdrant per test."""
    monkeypatch.setenv("QDRANT_URL", ":memory:")


@pytest.fixture
def tmp_watch_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Writable watch path for indexer tests."""
    watch = tmp_path / "watch"
    watch.mkdir()
    monkeypatch.setenv("WATCH_PATHS", str(watch))
    return watch


@pytest.fixture
def sample_txt(tmp_watch_path: Path) -> Path:
    p = tmp_watch_path / "sample.txt"
    p.write_text(
        "Hello Raven. This is a sample document for testing RAG indexing. "
        "It contains enough words to verify chunking behavior works correctly "
        "with the default chunk size and overlap parameters."
    )
    return p


@pytest.fixture
def sample_md(tmp_watch_path: Path) -> Path:
    p = tmp_watch_path / "doc.md"
    p.write_text("# Title\n\nParagraph about LangGraph and agents.")
    return p
