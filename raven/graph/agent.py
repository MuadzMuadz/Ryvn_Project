"""LangGraph agent with a persistent async checkpointer.

Checkpointer backend is chosen at runtime:
- ``DATABASE_URL`` set  -> Postgres (ryvn-postgres), shared with the rest of the stack.
- otherwise             -> local SQLite file (dev/test, no external service needed).
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from raven.config import DATABASE_URL, SESSIONS_DB
from raven.graph.nodes import agent_node, retrieve_node, should_continue, tool_node
from raven.graph.state import AgentState

_graph = None
_saver = None
_pool = None


async def _get_saver():
    global _saver, _pool
    if _saver is not None:
        return _saver

    if DATABASE_URL:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg.rows import dict_row
        from psycopg_pool import AsyncConnectionPool

        _pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            max_size=10,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        )
        await _pool.open()
        _saver = AsyncPostgresSaver(_pool)
    else:
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(str(SESSIONS_DB))
        _saver = AsyncSqliteSaver(conn)

    await _saver.setup()
    return _saver


def _build_graph(saver):
    g = StateGraph(AgentState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("agent", agent_node)
    g.add_node("tools", tool_node)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "agent")
    g.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    g.add_edge("tools", "agent")
    # recursion_limit is an invoke-time config value, not a compile() argument.
    return g.compile(checkpointer=saver)


async def get_graph():
    global _graph
    if _graph is None:
        saver = await _get_saver()
        _graph = _build_graph(saver)
    return _graph


async def list_thread_ids() -> list[str]:
    """Distinct conversation thread ids, most-recently-active first.

    Backend-agnostic: walks the checkpointer instead of querying a specific DB,
    so it works the same on SQLite and Postgres.
    """
    saver = await _get_saver()
    seen: list[str] = []
    async for ct in saver.alist(None):
        tid = ct.config.get("configurable", {}).get("thread_id")
        if tid and tid not in seen:
            seen.append(tid)
    return seen


async def delete_thread(thread_id: str) -> None:
    saver = await _get_saver()
    await saver.adelete_thread(thread_id)
