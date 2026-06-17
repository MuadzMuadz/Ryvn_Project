#!/usr/bin/env bash
# Periodic Linux-side indexing for Raven, invoked by raven-index.timer.
# Indexes through the running daemon's HTTP API so ChromaDB is only ever written
# by a single process (the daemon). Unchanged files are skipped via hash dedup.
set -uo pipefail

BASE="${RAVEN_URL:-http://localhost:1802}"
PATHS=("/home/maxzcv/project" "/home/maxzcv/works")

for p in "${PATHS[@]}"; do
  [ -d "$p" ] || continue
  echo "[raven-index] indexing $p ..."
  curl -s -m 7200 -X POST "$BASE/index" \
    -H "Content-Type: application/json" \
    -d "{\"path\":\"$p\"}" && echo
done
