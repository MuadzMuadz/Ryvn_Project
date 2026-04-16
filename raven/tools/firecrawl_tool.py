"""Firecrawl integration — scrape & crawl via local Docker instance."""
from __future__ import annotations

from typing import Optional
from firecrawl import FirecrawlApp

from raven.config import FIRECRAWL_API_URL, FIRECRAWL_API_KEY


def _client() -> FirecrawlApp:
    return FirecrawlApp(api_key=FIRECRAWL_API_KEY, api_url=FIRECRAWL_API_URL)


def scrape_url(url: str, formats: list[str] | None = None) -> str:
    """Scrape a single URL and return markdown content."""
    app = _client()
    result = app.scrape_url(url, params={"formats": formats or ["markdown"]})
    return result.get("markdown", result.get("content", ""))


def crawl_url(url: str, max_pages: int = 10) -> list[dict]:
    """Crawl a URL and return list of {url, markdown} dicts."""
    app = _client()
    result = app.crawl_url(
        url,
        params={
            "crawlerOptions": {"limit": max_pages},
            "pageOptions": {"onlyMainContent": True},
        },
    )
    pages = result.get("data", [])
    return [{"url": p.get("url", ""), "content": p.get("markdown", "")} for p in pages]


def search_web(query: str, limit: int = 5) -> list[dict]:
    """Search the web via Firecrawl and return results."""
    app = _client()
    result = app.search(query, params={"pageOptions": {"onlyMainContent": True}, "searchOptions": {"limit": limit}})
    return result.get("data", [])
