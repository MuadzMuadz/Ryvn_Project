"""Tests for raven.api.app — uses FastAPI TestClient."""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_embedder():
    """Mock embedder for vectorstore."""
    with patch("raven.rag.vectorstore.APIEmbedder") as cls:
        instance = MagicMock()
        instance.embed.side_effect = lambda texts: [[0.1] * 384 for _ in texts]
        cls.return_value = instance
        yield instance


@pytest.fixture
def _reload_app(tmp_chroma_dir, tmp_watch_path, monkeypatch, mock_embedder):
    """Ensure config is loaded with test env vars before importing app."""
    monkeypatch.setenv("API_KEY", "test-key-123")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_chroma_dir))
    monkeypatch.setenv("WATCH_PATHS", str(tmp_watch_path))
    import raven.config as cfg

    importlib.reload(cfg)
    import raven.rag.vectorstore as vs_mod

    vs_mod._instance = None


@pytest.fixture
def api_client(_reload_app):
    from fastapi.testclient import TestClient
    from raven.api.app import app

    client = TestClient(app)
    client.headers.update({"X-API-Key": "test-key-123"})
    return client


@pytest.fixture
def api_client_noauth(_reload_app):
    from fastapi.testclient import TestClient
    from raven.api.app import app

    return TestClient(app)


def test_api_ui_served(api_client_noauth):
    """GET / serves the web chat UI publicly (no API key needed)."""
    r = api_client_noauth.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Raven" in r.text


def test_api_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") in {"ok", "degraded"}


def test_api_auth_required(api_client_noauth):
    r = api_client_noauth.post("/chat", json={"message": "hi", "session_id": "s1"})
    assert r.status_code == 401


def test_api_auth_valid_index(api_client, tmp_watch_path):
    """Auth header accepted — test with /index on a valid path (avoids LLM call)."""
    # Create a test file
    f = tmp_watch_path / "hello.txt"
    f.write_text("test content for indexing")
    r = api_client.post("/index", json={"path": str(f)})
    # Should not be 401 (auth ok) — might be 403 if path validation
    # reloads roots from config, but not 401
    assert r.status_code != 401


def test_api_index_path_validation(api_client):
    r = api_client.post("/index", json={"path": "/etc/passwd"})
    assert r.status_code == 403


def test_api_stats(api_client):
    r = api_client.get("/stats")
    assert r.status_code == 200
    body = r.json()
    assert "chunks" in body
    assert "session_count" in body
