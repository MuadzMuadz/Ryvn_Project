"""Firecrawl integration — scrape & crawl via local Docker instance."""
from __future__ import annotations

import logging

from firecrawl import FirecrawlApp

from raven.config import FIRECRAWL_API_KEY, FIRECRAWL_API_URL

logger = logging.getLogger("raven.firecrawl")


def _client() -> FirecrawlApp:
    return FirecrawlApp(api_key=FIRECRAWL_API_KEY, api_url=FIRECRAWL_API_URL)


def scrape_url(url: str) -> str:
    """Scrape a single URL and return markdown content."""
    try:
        doc = _client().scrape(url, formats=["markdown"], only_main_content=True)
    except Exception as e:
        logger.warning("scrape failed for %s: %s", url, e)
        return ""
    return doc.markdown or ""


def crawl_url(url: str, max_pages: int = 10) -> list[dict]:
    """Crawl a URL and return list of {url, content} dicts."""
    try:
        job = _client().crawl(url, limit=max_pages)
    except Exception as e:
        logger.warning("crawl failed for %s: %s", url, e)
        return []
    pages = getattr(job, "data", None) or []
    out: list[dict] = []
    for p in pages:
        meta = getattr(p, "metadata", None) or {}
        page_url = meta.get("url") if isinstance(meta, dict) else getattr(meta, "url", "")
        out.append({"url": page_url or "", "content": getattr(p, "markdown", "") or ""})
    return out


def search_web(query: str, limit: int = 5) -> list[dict]:
    """Search the web via Firecrawl."""
    try:
        result = _client().search(query, limit=limit)
    except Exception as e:
        logger.warning("search failed for %s: %s", query, e)
        return []
    web = getattr(result, "web", None) or []
    out: list[dict] = []
    for item in web:
        out.append({
            "title": getattr(item, "title", ""),
            "url": getattr(item, "url", ""),
            "description": getattr(item, "description", ""),
        })
    return out
