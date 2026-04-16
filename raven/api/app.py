"""FastAPI backend for Raven."""
from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from raven.graph.agent import get_graph
from raven.rag.indexer import FileIndexer
from raven.rag.vectorstore import get_store

app = FastAPI(title="Raven API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory sessions: session_id -> state dict
_sessions: dict[str, dict] = {}


def _get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "messages": [],
            "retrieved_docs": [],
            "tool_calls": [],
            "metadata": {},
        }
    return _sessions[session_id]


# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class IndexRequest(BaseModel):
    path: str


# ── SSE stream ────────────────────────────────────────────────────────────────

async def _stream(session_id: str, message: str) -> AsyncIterator[dict]:
    state = _get_session(session_id)
    state["messages"].append(HumanMessage(content=message))

    graph = get_graph()
    final_output: dict = {}
    full_answer: list[str] = []

    async for event in graph.astream_events(state, version="v2"):
        kind = event["event"]
        name = event.get("name", "")
        data = event.get("data", {})

        # ── capture final graph state ─────────────────────────────────────
        if kind == "on_chain_end" and name == "LangGraph":
            final_output = data.get("output", {})

        # ── retrieval done ────────────────────────────────────────────────
        elif kind == "on_chain_end" and name == "retrieve":
            docs = data.get("output", {}).get("retrieved_docs", [])
            if docs:
                yield {
                    "event": "retrieval",
                    "data": json.dumps([
                        f"{d['metadata'].get('filename', 'unknown')} ({round(d['score'] * 100)}%)"
                        for d in docs
                    ]),
                }

        # ── collect tokens silently ───────────────────────────────────────
        elif kind == "on_chat_model_stream":
            chunk = data.get("chunk")
            if chunk and chunk.content:
                full_answer.append(chunk.content)

        # ── tool start ────────────────────────────────────────────────────
        elif kind == "on_tool_start":
            yield {
                "event": "tool_start",
                "data": json.dumps({"tool": name, "input": data.get("input", {})}),
            }

        # ── tool end ──────────────────────────────────────────────────────
        elif kind == "on_tool_end":
            output = data.get("output", "")
            yield {
                "event": "tool_end",
                "data": json.dumps({"tool": name, "output": str(output)[:500]}),
            }

    # ── send complete answer once ─────────────────────────────────────────
    if full_answer:
        yield {"event": "message", "data": json.dumps({"text": "".join(full_answer)})}

    # persist final state to session
    if final_output:
        _sessions[session_id] = {**state, **final_output}

    yield {"event": "done", "data": json.dumps({"session_id": session_id})}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    return EventSourceResponse(
        _stream(session_id, req.message),
        headers={"X-Session-Id": session_id},
    )


@app.post("/index")
async def index_path(req: IndexRequest):
    from pathlib import Path
    import logging
    logger = logging.getLogger("raven.indexer")

    p = Path(req.path)
    if not p.exists():
        return JSONResponse({"error": f"Path not found: {req.path}"}, status_code=404)

    indexer = FileIndexer()
    total_chunks = 0
    total_files = 0
    skipped = 0

    if p.is_file():
        n = indexer.index_file(p)
        logger.info(f"indexed {p.name} → {n} chunks")
        total_chunks = n
        total_files = 1
    else:
        from raven.config import INDEXED_EXTENSIONS
        from raven.rag.indexer import EXCLUDE_DIRS
        files = [
            f for f in p.glob("**/*")
            if f.is_file()
            and f.suffix.lower() in INDEXED_EXTENSIONS
            and not any(part in EXCLUDE_DIRS for part in f.parts)
        ]
        for file in files:
            n = indexer.index_file(file)
            if n == 0:
                skipped += 1
            else:
                total_chunks += n
                total_files += 1
            logger.info(f"{'skip' if n == 0 else 'idx '} {file.name} ({n} chunks)")

    return {
        "path": str(p),
        "indexed_files": total_files,
        "skipped_files": skipped,
        "total_chunks": total_chunks,
    }


@app.get("/stats")
async def stats():
    store = get_store()
    sessions = len(_sessions)
    return {"chunks": store.count(), "active_sessions": sessions}


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"cleared": session_id}


@app.post("/index/init")
async def index_init():
    """Index semua WATCH_PATHS via SSE stream."""
    from pathlib import Path
    import asyncio
    from raven.config import WATCH_PATHS, INDEXED_EXTENSIONS
    from raven.rag.indexer import EXCLUDE_DIRS

    async def _stream() -> AsyncIterator[dict]:
        indexer = FileIndexer()
        grand_total_files = 0
        grand_total_chunks = 0

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
            loop = asyncio.get_event_loop()
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
            yield {"event": "path_done", "data": json.dumps({"path": str(p), "files": path_files, "chunks": path_chunks})}

        yield {"event": "done", "data": json.dumps({"total_files": grand_total_files, "total_chunks": grand_total_chunks})}

    return EventSourceResponse(_stream())


@app.get("/health")
async def health():
    return {"status": "ok"}
