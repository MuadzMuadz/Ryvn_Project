"""Tests for raven.config."""

import importlib

import pytest


def test_config_defaults(monkeypatch: pytest.MonkeyPatch):
    """Config loads sensible defaults when env vars are missing."""
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    # Prevent load_dotenv from re-loading .env during reload
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: None)
    import raven.config as cfg

    importlib.reload(cfg)
    assert cfg.API_KEY == ""
    assert cfg.LOG_LEVEL == "INFO"
    assert cfg.ALLOWED_ORIGINS == ["http://localhost:3000"]


def test_config_env_override(monkeypatch: pytest.MonkeyPatch):
    """Env vars override config defaults."""
    monkeypatch.setenv("API_KEY", "xyz")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://a.com, http://b.com")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    import raven.config as cfg

    importlib.reload(cfg)
    assert cfg.API_KEY == "xyz"
    assert "http://a.com" in cfg.ALLOWED_ORIGINS
    assert "http://b.com" in cfg.ALLOWED_ORIGINS
    assert cfg.LOG_LEVEL == "DEBUG"
