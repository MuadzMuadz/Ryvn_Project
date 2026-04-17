"""LangGraph agent with persistent (async) checkpointer."""
from __future__ import annotations

import aiosqlite

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph, END

from raven.config import SESSIONS_DB
from raven.graph.state import AgentState
from raven.graph.nodes import retrieve_node, agent_node, tool_node, should_continue


_graph = None
_saver: AsyncSqliteSaver | None = None
_conn: aiosqlite.Connection | None = None


async def _get_saver() -> AsyncSqliteSaver:
    global _saver, _conn
    if _saver is None:
        SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
        _conn = await aiosqlite.connect(str(SESSIONS_DB))
        _saver = AsyncSqliteSaver(_conn)
        await _saver.setup()
    return _saver


def _build_graph(saver: AsyncSqliteSaver):
    g = StateGraph(AgentState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("agent", agent_node)
    g.add_node("tools", tool_node)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "agent")
    g.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    g.add_edge("tools", "agent")
    return g.compile(checkpointer=saver)


async def get_graph():
    global _graph
    if _graph is None:
        saver = await _get_saver()
        _graph = _build_graph(saver)
    return _graph


async def delete_thread(thread_id: str) -> None:
    saver = await _get_saver()
    await saver.adelete_thread(thread_id)
