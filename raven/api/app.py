"""FastAPI backend for Raven."""

from __future__ import annotations

import asyncio
import json
import socket
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from raven.config import (
    ALLOWED_ORIGINS,
    API_KEY,
    ENABLE_WATCHER,
    INDEX_ON_STARTUP,
    INDEXED_EXTENSIONS,
    OPENAI_BASE_URL,
    WATCH_PATHS,
    WATCHER_PATHS,
)
from raven.graph.agent import delete_thread, get_graph, list_thread_ids
from raven.logging_config import get_logger, setup_logging
from raven.rag.indexer import FileIndexer, is_excluded
from raven.rag.vectorstore import get_store
from raven.rag.watcher import FileWatcher

setup_logging()
logger = get_logger("raven.api")


def _run_initial_index() -> None:
    """One-time full index of WATCH_PATHS. Runs in a thread to not block startup."""
    indexer = FileIndexer(store=get_store())
    total_files = 0
    total_chunks = 0
    for watch_path in WATCH_PATHS:
        p = Path(watch_path)
        if not p.exists():
            logger.warning("initial_index_skip", path=str(p), reason="not found")
            continue
        logger.info("initial_index_start", path=str(p))
        n = indexer.index_directory(p)
        total_chunks += n
        total_files += 1
    logger.info("initial_index_done", paths=total_files, chunks=total_chunks)


@asynccontextmanager
async def lifespan(app: FastAPI):
    watcher: FileWatcher | None = None
    if INDEX_ON_STARTUP:
        logger.info("initial_index_scheduled", paths=WATCH_PATHS)
        asyncio.get_running_loop().run_in_executor(None, _run_initial_index)
    if ENABLE_WATCHER:
        watcher = FileWatcher(indexer=FileIndexer(store=get_store()), paths=WATCHER_PATHS)
        # start() walks the tree to install inotify watches — run it off the event
        # loop so a large directory can't block uvicorn from binding the port.
        asyncio.get_running_loop().run_in_executor(None, watcher.start)
        logger.info("watcher_enabled", paths=WATCHER_PATHS)
    try:
        yield
    finally:
        if watcher is not None:
            watcher.stop()
            logger.info("watcher_stopped")


app = FastAPI(title="Raven API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

_ALLOWED_ROOTS = [Path(p).resolve() for p in WATCH_PATHS]


# ── Auth ──────────────────────────────────────────────────────────────────────


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not API_KEY:
        return  # auth disabled in dev
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


# ── Path validation ───────────────────────────────────────────────────────────


def _validate_path(raw: str) -> Path:
    p = Path(raw).expanduser().resolve()
    if p.is_symlink():
        raise HTTPException(status_code=403, detail="Symlinks not allowed")
    if not any(
        str(p) == str(root) or str(p).startswith(str(root) + "/") for root in _ALLOWED_ROOTS
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Path outside allowed roots (WATCH_PATHS): {p}",
        )
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {p}")
    return p


# ── Models ────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class IndexRequest(BaseModel):
    path: str


# ── SSE stream (chat) ─────────────────────────────────────────────────────────


def _message_text(msg) -> str:
    """Extract plain text from an AIMessage whose content may be a str or a list
    of content blocks (some providers return the latter)."""
    content = getattr(msg, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""


async def _chat_stream(session_id: str, message: str) -> AsyncIterator[dict]:
    graph = await get_graph()
    config = {"configurable": {"thread_id": session_id}, "recursion_limit": 25}
    new_input = {"messages": [HumanMessage(content=message)]}

    streamed_text = False  # did any token actually stream to the client?
    final_text = ""  # last model message's text, as a fallback
    try:
        async for event in graph.astream_events(new_input, config=config, version="v2"):
            kind = event["event"]
            name = event.get("name", "")
            data = event.get("data", {})

            if kind == "on_chain_end" and name == "retrieve":
                docs = data.get("output", {}).get("retrieved_docs", [])
                if docs:
                    yield {
                        "event": "retrieval",
                        "data": json.dumps(
                            [
                                f"{d['metadata'].get('filename', 'unknown')} ({round(d['score'] * 100)}%)"
                                for d in docs
                            ]
                        ),
                    }

            elif kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                text = _message_text(chunk) if chunk is not None else ""
                if text:
                    streamed_text = True
                    yield {"event": "token", "data": json.dumps({"text": text})}

            elif kind == "on_chat_model_end":
                # Remember the final answer so we can emit it if the model never
                # streamed tokens (some backends return the full reply at once,
                # which otherwise shows up as an empty "— silence —" in the UI).
                out = data.get("output")
                text = _message_text(out) if out is not None else ""
                if text.strip():
                    final_text = text

            elif kind == "on_tool_start":
                yield {
                    "event": "tool_start",
                    "data": json.dumps({"tool": name, "input": data.get("input", {})}),
                }

            elif kind == "on_tool_end":
                output = data.get("output", "")
                yield {
                    "event": "tool_end",
                    "data": json.dumps({"tool": name, "output": str(output)[:500]}),
                }
    finally:
        if not streamed_text and final_text:
            yield {"event": "token", "data": json.dumps({"text": final_text})}
        yield {"event": "done", "data": json.dumps({"session_id": session_id})}


# ── Routes ────────────────────────────────────────────────────────────────────

_STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
async def ui():
    """Serve the single-file web chat UI (public — page must load before auth)."""
    return FileResponse(_STATIC_DIR / "index.html")


@app.post("/chat", dependencies=[Depends(require_api_key)])
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    return EventSourceResponse(
        _chat_stream(session_id, req.message),
        headers={"X-Session-Id": session_id},
    )


@app.post("/index", dependencies=[Depends(require_api_key)])
async def index_path(req: IndexRequest):
    p = _validate_path(req.path)
    indexer = FileIndexer()
    loop = asyncio.get_running_loop()
    total_chunks = 0
    total_files = 0
    skipped = 0

    if p.is_file():
        n = await loop.run_in_executor(None, indexer.index_file, p)
        logger.info("file_indexed", file=p.name, chunks=n)
        total_chunks = n
        total_files = 1 if n > 0 else 0
        skipped = 1 if n == 0 else 0
    else:
        files = [
            f
            for f in p.glob("**/*")
            if f.is_file()
            and f.suffix.lower() in INDEXED_EXTENSIONS
            and not is_excluded(f)
        ]
        for file in files:
            n = await loop.run_in_executor(None, indexer.index_file, file)
            if n == 0:
                skipped += 1
            else:
                total_chunks += n
                total_files += 1
            logger.info(
                "file_processed",
                file=file.name,
                chunks=n,
                status="skipped" if n == 0 else "indexed",
            )

    return {
        "path": str(p),
        "indexed_files": total_files,
        "skipped_files": skipped,
        "total_chunks": total_chunks,
    }


@app.post("/index/init", dependencies=[Depends(require_api_key)])
async def index_init():
    async def _stream() -> AsyncIterator[dict]:
        indexer = FileIndexer()
        grand_total_files = 0
        grand_total_chunks = 0
        loop = asyncio.get_running_loop()

        for watch_path in WATCH_PATHS:
            p = Path(watch_path)
            if not p.exists():
                yield {"event": "skip", "data": json.dumps({"path": str(p), "reason": "not found"})}
                continue

            files = [
                f
                for f in p.glob("**/*")
                if f.is_file()
                and f.suffix.lower() in INDEXED_EXTENSIONS
                and not is_excluded(f)
            ]

            yield {
                "event": "start",
                "data": json.dumps({"path": str(p), "total_files": len(files)}),
            }

            path_chunks = 0
            path_files = 0
            for i, file in enumerate(files, 1):
                n = await loop.run_in_executor(None, indexer.index_file, file)
                if n > 0:
                    path_chunks += n
                    path_files += 1
                yield {
                    "event": "progress",
                    "data": json.dumps(
                        {
                            "file": file.name,
                            "chunks": n,
                            "progress": f"{i}/{len(files)}",
                            "status": "skipped" if n == 0 else "indexed",
                        }
                    ),
                }

            grand_total_files += path_files
            grand_total_chunks += path_chunks
            yield {
                "event": "path_done",
                "data": json.dumps({"path": str(p), "files": path_files, "chunks": path_chunks}),
            }

        yield {
            "event": "done",
            "data": json.dumps(
                {"total_files": grand_total_files, "total_chunks": grand_total_chunks}
            ),
        }

    return EventSourceResponse(_stream())


async def _count_sessions() -> int:
    try:
        return len(await list_thread_ids())
    except Exception:
        return 0


@app.get("/stats", dependencies=[Depends(require_api_key)])
async def stats():
    store = get_store()
    session_count = await _count_sessions()
    return {
        "chunks": store.count(),
        "session_count": session_count,
        "allowed_roots": [str(r) for r in _ALLOWED_ROOTS],
    }


@app.get("/sessions", dependencies=[Depends(require_api_key)])
async def list_sessions():
    """List conversation sessions (newest first) with a title from the first user message."""
    graph = await get_graph()  # ensures the checkpointer is set up
    try:
        thread_ids = await list_thread_ids()
    except Exception:
        return {"sessions": []}

    sessions = []
    for thread_id in thread_ids:
        title, count = "", 0
        try:
            snap = await graph.aget_state({"configurable": {"thread_id": thread_id}})
            msgs = (snap.values or {}).get("messages", []) if snap else []
            count = len(msgs)
            first = next((m.content for m in msgs if getattr(m, "type", "") == "human"), "")
            if isinstance(first, str) and first.strip():
                title = first.strip()[:60]
        except Exception:
            pass
        sessions.append({"session_id": thread_id, "title": title or "(untitled)", "messages": count})
    return {"sessions": sessions}


@app.get("/session/{session_id}/history", dependencies=[Depends(require_api_key)])
async def session_history(session_id: str):
    """Return the user/assistant messages of a session for restoring the conversation."""
    graph = await get_graph()
    try:
        snap = await graph.aget_state({"configurable": {"thread_id": session_id}})
        msgs = (snap.values or {}).get("messages", []) if snap else []
    except Exception:
        msgs = []
    out = []
    for m in msgs:
        role = getattr(m, "type", "")
        content = getattr(m, "content", "")
        if role in ("human", "ai") and isinstance(content, str) and content.strip():
            out.append({"role": "user" if role == "human" else "assistant", "content": content})
    return {"session_id": session_id, "messages": out}


@app.delete("/session/{session_id}", dependencies=[Depends(require_api_key)])
async def clear_session(session_id: str):
    await delete_thread(session_id)
    return {"cleared": session_id}


def _tcp_reachable(url: str | None, timeout: float = 2.0) -> bool:
    """Quick TCP connect to a base_url's host:port — used to tell if the LLM
    endpoint (the ryvn-litellm proxy) is up, without making a model call."""
    if not url:
        return False
    parsed = urlparse(url)
    if not parsed.hostname:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout):
            return True
    except OSError:
        return False


@app.get("/health")
async def health():
    checks: dict[str, str] = {"api": "ok"}

    try:
        get_store().count()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"error: {e.__class__.__name__}"

    try:
        await get_graph()
        checks["graph"] = "ok"
    except Exception as e:
        checks["graph"] = f"error: {e.__class__.__name__}"

    # LLM endpoint reachability (the ryvn-litellm proxy). No fallback, so an
    # unreachable endpoint makes the service degraded.
    loop = asyncio.get_running_loop()
    llm_up = await loop.run_in_executor(None, _tcp_reachable, OPENAI_BASE_URL)
    checks["llm"] = "ok" if llm_up else "unreachable"

    core_ok = all(checks[k] == "ok" for k in ("api", "qdrant", "graph"))
    overall = "ok" if core_ok and llm_up else "degraded"
    return {"status": overall, "checks": checks}
