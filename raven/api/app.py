"""FastAPI backend for Raven."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from raven.config import (
    ALLOWED_ORIGINS,
    API_KEY,
    INDEXED_EXTENSIONS,
    WATCH_PATHS,
)
from raven.graph.agent import delete_thread, get_graph
from raven.rag.indexer import EXCLUDE_DIRS, FileIndexer
from raven.rag.vectorstore import get_store

logger = logging.getLogger("raven.api")

app = FastAPI(title="Raven API", version="0.1.0")

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
    if not any(str(p) == str(root) or str(p).startswith(str(root) + "/") for root in _ALLOWED_ROOTS):
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

async def _chat_stream(session_id: str, message: str) -> AsyncIterator[dict]:
    graph = await get_graph()
    config = {"configurable": {"thread_id": session_id}}
    new_input = {"messages": [HumanMessage(content=message)]}

    full_answer: list[str] = []

    async for event in graph.astream_events(new_input, config=config, version="v2"):
        kind = event["event"]
        name = event.get("name", "")
        data = event.get("data", {})

        if kind == "on_chain_end" and name == "retrieve":
            docs = data.get("output", {}).get("retrieved_docs", [])
            if docs:
                yield {
                    "event": "retrieval",
                    "data": json.dumps([
                        f"{d['metadata'].get('filename', 'unknown')} ({round(d['score'] * 100)}%)"
                        for d in docs
                    ]),
                }

        elif kind == "on_chat_model_stream":
            chunk = data.get("chunk")
            if chunk and chunk.content:
                full_answer.append(chunk.content)

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

    if full_answer:
        yield {"event": "message", "data": json.dumps({"text": "".join(full_answer)})}

    yield {"event": "done", "data": json.dumps({"session_id": session_id})}


# ── Routes ────────────────────────────────────────────────────────────────────

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
    loop = asyncio.get_event_loop()
    total_chunks = 0
    total_files = 0
    skipped = 0

    if p.is_file():
        n = await loop.run_in_executor(None, indexer.index_file, p)
        logger.info("indexed %s → %d chunks", p.name, n)
        total_chunks = n
        total_files = 1 if n > 0 else 0
        skipped = 1 if n == 0 else 0
    else:
        files = [
            f for f in p.glob("**/*")
            if f.is_file()
            and f.suffix.lower() in INDEXED_EXTENSIONS
            and not any(part in EXCLUDE_DIRS for part in f.parts)
        ]
        for file in files:
            n = await loop.run_in_executor(None, indexer.index_file, file)
            if n == 0:
                skipped += 1
            else:
                total_chunks += n
                total_files += 1
            logger.info("%s %s (%d chunks)", "skip" if n == 0 else "idx ", file.name, n)

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
        loop = asyncio.get_event_loop()

        for watch_path in WATCH_PATHS:
            p = Path(watch_path)
            if not p.exists():
                yield {"event": "skip", "data": json.dumps({"path": str(p), "reason": "not found"})}
                continue

            files = [
                f for f in p.glob("**/*")
                if f.is_file()
                and f.suffix.lower() in INDEXED_EXTENSIONS
                and not any(part in EXCLUDE_DIRS for part in f.parts)
            ]

            yield {"event": "start", "data": json.dumps({"path": str(p), "total_files": len(files)})}

            path_chunks = 0
            path_files = 0
            for i, file in enumerate(files, 1):
                n = await loop.run_in_executor(None, indexer.index_file, file)
                if n > 0:
                    path_chunks += n
                    path_files += 1
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "file": file.name,
                        "chunks": n,
                        "progress": f"{i}/{len(files)}",
                        "status": "skipped" if n == 0 else "indexed",
                    }),
                }

            grand_total_files += path_files
            grand_total_chunks += path_chunks
            yield {
                "event": "path_done",
                "data": json.dumps({"path": str(p), "files": path_files, "chunks": path_chunks}),
            }

        yield {
            "event": "done",
            "data": json.dumps({"total_files": grand_total_files, "total_chunks": grand_total_chunks}),
        }

    return EventSourceResponse(_stream())


@app.get("/stats", dependencies=[Depends(require_api_key)])
async def stats():
    store = get_store()
    return {"chunks": store.count(), "allowed_roots": [str(r) for r in _ALLOWED_ROOTS]}


@app.delete("/session/{session_id}", dependencies=[Depends(require_api_key)])
async def clear_session(session_id: str):
    await delete_thread(session_id)
    return {"cleared": session_id}


@app.get("/health")
async def health():
    checks: dict[str, str] = {"api": "ok"}
    status_code = 200

    try:
        get_store().count()
        checks["chroma"] = "ok"
    except Exception as e:
        checks["chroma"] = f"error: {e.__class__.__name__}"
        status_code = 503

    try:
        await get_graph()
        checks["graph"] = "ok"
    except Exception as e:
        checks["graph"] = f"error: {e.__class__.__name__}"
        status_code = 503

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
