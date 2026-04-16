"""LangChain tools exposed to the agent."""
from __future__ import annotations

from langchain_core.tools import tool

from raven.rag.vectorstore import get_store
from raven.rag.indexer import FileIndexer
from raven.tools.firecrawl_tool import scrape_url, crawl_url, search_web

_store = get_store()
_indexer = FileIndexer(store=_store)


@tool
def search_local_docs(query: str, n_results: int = 5) -> str:
    """Search local indexed documents by semantic similarity."""
    docs = _store.query(query, n_results=n_results)
    if not docs:
        return "No relevant documents found."
    return "\n---\n".join(
        f"[{d['metadata'].get('filename', 'unknown')}] (score: {d['score']:.2f})\n{d['text']}"
        for d in docs
    )


@tool
def index_local_path(path: str) -> str:
    """Index a local file or directory into the knowledge base."""
    from pathlib import Path
    p = Path(path)
    if p.is_file():
        n = _indexer.index_file(p)
        return f"Indexed {n} chunks from {p.name}"
    elif p.is_dir():
        n = _indexer.index_directory(p)
        return f"Indexed {n} chunks from directory {p}"
    else:
        return f"Path not found: {path}"


@tool
def scrape_webpage(url: str) -> str:
    """Scrape a web page and return its content as markdown using Firecrawl."""
    content = scrape_url(url)
    return content[:8000] if content else "Failed to scrape page."


@tool
def crawl_website(url: str, max_pages: int = 5) -> str:
    """Crawl a website and return content from multiple pages using Firecrawl."""
    pages = crawl_url(url, max_pages=max_pages)
    if not pages:
        return "No pages crawled."
    return "\n\n---\n\n".join(f"## {p['url']}\n{p['content'][:2000]}" for p in pages)


@tool
def web_search(query: str, limit: int = 5) -> str:
    """Search the web for current information using Firecrawl."""
    results = search_web(query, limit=limit)
    if not results:
        return "No results found."
    return "\n\n".join(
        f"**{r.get('title', 'Untitled')}** ({r.get('url', '')})\n{r.get('markdown', r.get('description', ''))[:500]}"
        for r in results
    )


@tool
def get_indexed_stats() -> str:
    """Get statistics about the local knowledge base."""
    count = _store.count()
    return f"Vector store contains {count} document chunks."


TOOLS = [
    search_local_docs,
    index_local_path,
    scrape_webpage,
    crawl_website,
    web_search,
    get_indexed_stats,
]

TOOLS_BY_NAME = {t.name: t for t in TOOLS}
