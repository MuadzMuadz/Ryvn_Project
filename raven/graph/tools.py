"""LangChain tools exposed to the agent."""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from langchain_core.tools import tool

from raven.config import NOTES_DIR, WATCH_PATHS
from raven.logging_config import get_logger
from raven.rag.indexer import FileIndexer
from raven.rag.vectorstore import get_store
from raven.tools.firecrawl_tool import crawl_url, scrape_url, search_web

logger = get_logger("raven.tools")

_store = get_store()
_indexer = FileIndexer(store=_store)
_ALLOWED_ROOTS = [Path(p).resolve() for p in WATCH_PATHS]


def _slugify(text: str, max_len: int = 60) -> str:
    """Filesystem-safe slug from a note title."""
    slug = re.sub(r"[^\w\s-]", "", text).strip()
    slug = re.sub(r"\s+", " ", slug)
    return slug[:max_len].strip() or "untitled"


def _is_allowed(p: Path) -> bool:
    resolved = p.resolve()
    return any(
        str(resolved) == str(root) or str(resolved).startswith(str(root) + "/")
        for root in _ALLOWED_ROOTS
    )


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
    """Index a local file or directory into the knowledge base. Only paths inside WATCH_PATHS are allowed."""
    p = Path(path).expanduser()
    if not _is_allowed(p):
        return f"Refused: path outside allowed roots (WATCH_PATHS): {p}"
    if not p.exists():
        return f"Path not found: {p}"
    if p.is_file():
        n = _indexer.index_file(p)
        return f"Indexed {n} chunks from {p.name}"
    n = _indexer.index_directory(p)
    return f"Indexed {n} chunks from directory {p}"


@tool
def scrape_webpage(url: str) -> str:
    """Scrape a web page and return its content as markdown via Firecrawl."""
    content = scrape_url(url)
    return content[:8000] if content else "Failed to scrape page."


@tool
def crawl_website(url: str, max_pages: int = 5) -> str:
    """Crawl a website and return content from multiple pages via Firecrawl."""
    pages = crawl_url(url, max_pages=max_pages)
    if not pages:
        return "No pages crawled."
    return "\n\n---\n\n".join(f"## {p['url']}\n{p['content'][:2000]}" for p in pages)


@tool
def web_search(query: str, limit: int = 5) -> str:
    """Search the web for current information via Firecrawl."""
    results = search_web(query, limit=limit)
    if not results:
        return "No results found."
    return "\n\n".join(
        f"**{r.get('title', 'Untitled')}** ({r.get('url', '')})\n{r.get('description', '')[:500]}"
        for r in results
    )


@tool
def save_note(title: str, content: str, tags: str = "", folder: str = "") -> str:
    """Save a markdown note to Raven's notes vault, then index it so it becomes searchable later.

    Use this whenever the user asks you to write something down, remember a fact, jot a summary,
    or keep a record — or when you produce something worth persisting across conversations.
    - title: short note title (becomes the filename).
    - content: the note body, in markdown.
    - tags: optional comma-separated tags (e.g. "meeting,raven").
    - folder: optional subfolder under the notes vault (e.g. "Logs").
    """
    today = datetime.date.today().isoformat()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H%M")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    target_dir = NOTES_DIR / folder.strip("/ ") if folder.strip() else NOTES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    path = target_dir / f"{stamp} - {_slugify(title)}.md"
    frontmatter = (
        "---\n"
        f"title: {title}\n"
        f"created: {today}\n"
        f"tags: [{', '.join(tag_list)}]\n"
        "type: note\n"
        "source: raven\n"
        "---\n\n"
    )
    body = f"# {title}\n\n{content.strip()}\n"
    try:
        path.write_text(frontmatter + body, encoding="utf-8")
    except OSError as e:
        logger.warning("save_note_failed", path=str(path), error=str(e))
        return f"Failed to save note: {e}"

    n = _indexer.index_file(path)
    logger.info("note_saved", path=str(path), chunks=n)
    return f"Saved note '{title}' to {path} ({n} chunks indexed)."


@tool
def get_indexed_stats() -> str:
    """Get statistics about the local knowledge base."""
    return f"Vector store contains {_store.count()} document chunks."


TOOLS = [
    search_local_docs,
    index_local_path,
    save_note,
    scrape_webpage,
    crawl_website,
    web_search,
    get_indexed_stats,
]

TOOLS_BY_NAME = {t.name: t for t in TOOLS}
