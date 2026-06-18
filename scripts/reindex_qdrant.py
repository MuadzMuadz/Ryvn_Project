"""One-shot full re-index into Qdrant (Chroma -> Qdrant migration).

Run after pointing QDRANT_URL at the server and clearing index_state.json.
Resumable: FileIndexer persists per-file hashes as it goes, so a re-run skips
files already indexed.
"""

from __future__ import annotations

import time

from raven.rag.indexer import FileIndexer
from raven.rag.vectorstore import get_store

ROOTS = [
    "/home/maxzcv/project",
    "/home/maxzcv/works",
    "/mnt/c/Users/LEGION/Documents",
]


def main() -> None:
    store = get_store()
    indexer = FileIndexer(store=store)
    print(f"[reindex] start; collection count = {store.count()}", flush=True)
    grand_total = 0
    for root in ROOTS:
        t0 = time.time()
        print(f"[reindex] indexing {root} ...", flush=True)
        n = indexer.index_directory(root, recursive=True)
        grand_total += n
        print(
            f"[reindex] done {root}: +{n} chunks in {time.time() - t0:.0f}s "
            f"(running total {grand_total}, store count {store.count()})",
            flush=True,
        )
    print(f"[reindex] FINISHED. total chunks added = {grand_total}, "
          f"final store count = {store.count()}", flush=True)


if __name__ == "__main__":
    main()
