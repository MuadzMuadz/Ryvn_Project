"""Migrate LangGraph checkpoints from local SQLite -> Postgres (ryvn-postgres).

SQLite and Postgres savers use DIFFERENT on-disk schemas (Postgres normalizes
channel values into a separate `checkpoint_blobs` table), so a raw SQL table copy
produces unreadable checkpoints. Instead we read through the SQLite saver and write
through the Postgres saver, which serializes correctly for each backend.

Usage (sends straight to the target Postgres):
  DATABASE_URL=postgresql://user:pass@HOST:5432/raven \
  uv run python scripts/migrate_checkpoints_sqlite_to_pg.py
"""

from __future__ import annotations

import asyncio
import os

import aiosqlite
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from raven.config import SESSIONS_DB


async def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("Set DATABASE_URL to the target Postgres DSN.")
    if not SESSIONS_DB.exists():
        raise SystemExit(f"No source DB at {SESSIONS_DB}")

    conn = await aiosqlite.connect(str(SESSIONS_DB))
    src = AsyncSqliteSaver(conn)

    pool = AsyncConnectionPool(
        conninfo=dsn,
        max_size=5,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    await pool.open()
    dst = AsyncPostgresSaver(pool)
    await dst.setup()

    # Oldest first so parent checkpoints are written before their children.
    tuples = [ct async for ct in src.alist(None)]
    tuples.reverse()
    print(f"[migrate] {len(tuples)} checkpoints to copy ...", flush=True)

    n_writes = 0
    for ct in tuples:
        new_versions = ct.checkpoint.get("channel_versions", {})
        await dst.aput(ct.config, ct.checkpoint, ct.metadata, new_versions)
        if ct.pending_writes:
            by_task: dict[str, list[tuple[str, object]]] = {}
            for task_id, channel, value in ct.pending_writes:
                by_task.setdefault(task_id, []).append((channel, value))
            for task_id, writes in by_task.items():
                await dst.aput_writes(ct.config, writes, task_id)
                n_writes += len(writes)

    threads = {ct.config["configurable"]["thread_id"] for ct in tuples}
    print(
        f"[migrate] DONE: {len(tuples)} checkpoints, {n_writes} writes, "
        f"{len(threads)} threads -> Postgres",
        flush=True,
    )
    await pool.close()
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
