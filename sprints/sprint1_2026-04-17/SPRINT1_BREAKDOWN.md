# Sprint 1 — Hardening & Foundation
## Daily Breakdown (17-30 April 2026)

**Goal:** Codebase aman, reliable, testable, dan terdokumentasi. Upgrade langsung dari kode yang ada di repo.
**Baseline:** 18 files, 942 lines, zero tests, zero auth, leaked key, CORS wildcard.
**Target:** v0.2.0 tag — secure, persistent sessions, true streaming, 15+ tests, README.

---

## Day 1 (17 Apr) — Repo Cleanup & Security Fix

**Effort:** ~2 jam
**Files touched:** `.env.example`, `.gitignore`, `raven/config.py`

### Tasks

- [ ] **1.1** Fix `.env.example` — replace leaked API key dengan placeholder
  - `OPENAI_API_KEY=sk-your-openai-or-litellm-key`
  - `OPENAI_BASE_URL=http://localhost:4000/v1`
  - `WATCH_PATHS=/path/to/your/docs,/path/to/your/downloads`
  - Hapus IP private + username yang bocor

- [ ] **1.2** Update `.gitignore` — pastikan `.env`, `data/`, `*.db` excluded
  - Tambah: `data/`, `*.db`, `index_state.json`, `__pycache__/`

- [ ] **1.3** Git history rewrite — hapus leaked key dari history
  - `git filter-repo --invert-paths --path .env.example`
  - Atau BFG: `bfg --replace-text passwords.txt`
  - Force push setelah backup bare clone

- [ ] **1.4** Tambah `API_KEY` dan `ALLOWED_ORIGINS` ke `config.py`
  ```python
  API_KEY = os.getenv("API_KEY", "")
  ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
  LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
  ```

**Checkpoint:** `.env.example` bersih, git history nggak ada leak, config punya field auth baru.

---

## Day 2 (18 Apr) — Auth Layer + CORS Lockdown + Path Validation

**Effort:** ~3 jam
**Files touched:** `raven/api/app.py`, `raven/config.py`

### Tasks

- [ ] **2.1** Add API key auth middleware
  ```python
  from fastapi import Depends, Header, HTTPException
  
  def require_api_key(x_api_key: str = Header(None)):
      if config.API_KEY and x_api_key != config.API_KEY:
          raise HTTPException(status_code=401, detail="Invalid API key")
  ```
  Apply ke: `POST /chat`, `POST /index`, `POST /index/init`, `DELETE /session/{id}`

- [ ] **2.2** CORS lockdown
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=config.ALLOWED_ORIGINS,  # bukan "*"
      allow_credentials=True,
      allow_methods=["GET", "POST", "DELETE"],
      allow_headers=["*"],
  )
  ```

- [ ] **2.3** Path validation di `/index` dan `/index/init`
  ```python
  ALLOWED_ROOTS = [Path(p).resolve() for p in config.WATCH_PATHS]
  
  def _validate_path(raw: str) -> Path:
      p = Path(raw).resolve()
      if p.is_symlink():
          raise HTTPException(403, "Symlinks not allowed")
      if not any(str(p).startswith(str(root)) for root in ALLOWED_ROOTS):
          raise HTTPException(403, f"Path outside allowed roots")
      if not p.exists():
          raise HTTPException(404, f"Path not found")
      return p
  ```

- [ ] **2.4** Max iteration limit di graph
  - `raven/graph/agent.py`: tambah `recursion_limit=25` di `graph.compile()`

**Checkpoint:** API reject request tanpa key, CORS restrict origins, `/index` tolak path di luar WATCH_PATHS, graph nggak loop infinite.

---

## Day 3 (19 Apr) — Persistent Sessions (SqliteSaver)

**Effort:** ~3 jam
**Files touched:** `raven/api/app.py`, `raven/graph/agent.py`, `pyproject.toml`

### Tasks

- [ ] **3.1** Add dependency: `langgraph-checkpoint-sqlite`
  ```toml
  # pyproject.toml
  dependencies = [
      ...
      "langgraph-checkpoint-sqlite>=2.0.0",
  ]
  ```

- [ ] **3.2** Integrate SqliteSaver ke graph
  ```python
  # raven/graph/agent.py
  from langgraph.checkpoint.sqlite import SqliteSaver
  
  def get_graph():
      global _graph
      if _graph is None:
          checkpointer = SqliteSaver.from_conn_string("./data/sessions.db")
          g = build_graph()
          _graph = g.compile(checkpointer=checkpointer, recursion_limit=25)
      return _graph
  ```

- [ ] **3.3** Refactor `app.py` — hapus `_sessions: dict`, gunakan graph config
  ```python
  # Setiap invoke/astream pakai:
  config = {"configurable": {"thread_id": session_id}}
  ```
  - Hapus manual state management (`_sessions[session_id]`)
  - Session history otomatis di-manage oleh checkpointer

- [ ] **3.4** Update `/stats` endpoint — session count dari SQLite bukan dict

- [ ] **3.5** Buat migration util: `data/` folder auto-create kalau belum ada

**Checkpoint:** Restart server → session history tetap ada. `data/sessions.db` terbentuk.

---

## Day 4 (21 Apr) — True SSE Streaming

**Effort:** ~2 jam
**Files touched:** `raven/api/app.py`

### Tasks

- [ ] **4.1** Fix SSE streaming — yield per token, bukan batch
  ```python
  # SEBELUM (collect-then-dump):
  elif kind == "on_chat_model_stream":
      chunk = data.get("chunk")
      if chunk and chunk.content:
          full_answer.append(chunk.content)
  ...
  if full_answer:
      yield {"event": "message", "data": json.dumps({"text": "".join(full_answer)})}
  
  # SESUDAH (true streaming):
  elif kind == "on_chat_model_stream":
      chunk = data.get("chunk")
      if chunk and chunk.content:
          yield {"event": "token", "data": json.dumps({"text": chunk.content})}
  ```

- [ ] **4.2** Update SSE events schema:
  - `retrieval` — retrieved docs (unchanged)
  - `tool_start` — tool call initiated (unchanged)
  - `tool_end` — tool result (unchanged)
  - `token` — individual LLM token (NEW, replace `message`)
  - `done` — stream complete (unchanged)

- [ ] **4.3** Fix `/index/init` — sudah pakai executor tapi event loop deprecated
  - Ganti `asyncio.get_event_loop()` → `asyncio.get_running_loop()`

- [ ] **4.4** Fix `/index` — tambah `run_in_executor` (currently blocking)
  ```python
  loop = asyncio.get_running_loop()
  n = await loop.run_in_executor(None, indexer.index_file, validated_path)
  ```

**Checkpoint:** Chat response muncul token-by-token di SSE client. `/index` nggak block event loop.

---

## Day 5 (22 Apr) — Structured Logging + Error Handling

**Effort:** ~3 jam
**Files touched:** `raven/api/app.py`, `raven/rag/indexer.py`, `raven/graph/nodes.py`, `raven/graph/tools.py`, `raven/rag/watcher.py`, `pyproject.toml`

### Tasks

- [ ] **5.1** Add structlog dependency
  ```toml
  dependencies = [..., "structlog>=24.0.0"]
  ```

- [ ] **5.2** Configure structlog di entry points
  ```python
  # raven/logging_config.py (NEW FILE)
  import structlog, logging, os
  
  def setup_logging():
      log_level = os.getenv("LOG_LEVEL", "INFO")
      structlog.configure(
          processors=[
              structlog.contextvars.merge_contextvars,
              structlog.processors.add_log_level,
              structlog.processors.TimeStamper(fmt="iso"),
              structlog.dev.ConsoleRenderer() if os.getenv("RYVN_ENV") != "production"
              else structlog.processors.JSONRenderer(),
          ],
          wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level)),
      )
  ```

- [ ] **5.3** Replace semua `print()` dan bare `logging` dengan structlog
  - `app.py`: request logging (method, path, session_id, latency)
  - `indexer.py`: file indexed/skipped/failed events
  - `nodes.py`: retrieval count, tool calls, LLM invocation
  - `watcher.py`: file events (created, modified, deleted, moved)

- [ ] **5.4** Narrow exception handling di `indexer.py`
  ```python
  # SEBELUM:
  except Exception:
      return 0
  
  # SESUDAH:
  except (PdfReadError, UnicodeDecodeError, OSError) as e:
      logger.warning("index_file_failed", path=str(path), error=str(e))
      return 0
  ```

- [ ] **5.5** Fix streaming file hash (OOM prevention)
  ```python
  def _file_hash(path: Path, chunk: int = 1 << 20) -> str:
      h = hashlib.sha256()
      with path.open("rb") as f:
          while blob := f.read(chunk):
              h.update(blob)
      return h.hexdigest()[:16]
  ```

- [ ] **5.6** Add graph loop counter logging
  ```python
  # nodes.py — agent_node
  iteration = state.get("metadata", {}).get("iteration", 0) + 1
  logger.info("agent_iteration", iteration=iteration)
  ```

**Checkpoint:** Logs structured JSON di production, console pretty di dev. Error nggak silent. File hash nggak OOM.

---

## Day 6-7 (23-24 Apr) — Test Suite

**Effort:** ~5 jam
**Files touched:** `tests/` (NEW), `pyproject.toml`

### Tasks

- [ ] **6.1** Add test dependencies
  ```toml
  [dependency-groups]
  dev = ["ipython", "pytest>=8", "pytest-asyncio>=0.24", "pytest-cov", "httpx>=0.27"]
  ```

- [ ] **6.2** Create test structure
  ```
  tests/
    __init__.py
    conftest.py          # fixtures: tmp_path, mock LLM, mock store, test client
    test_config.py       # config loading, defaults, env override
    test_indexer.py      # chunking, hashing, state persistence, file types
    test_vectorstore.py  # add/query/delete (real Chroma in tmp)
    test_api.py          # FastAPI TestClient, auth, CORS, endpoints
    test_graph.py        # mock LLM, routing logic, should_continue
    test_watcher.py      # watchdog events (create, modify, delete)
  ```

- [ ] **6.3** Write conftest.py fixtures
  - `tmp_chroma`: temporary ChromaDB in pytest tmp_path
  - `mock_llm`: fake LLM responses for graph tests
  - `test_client`: FastAPI TestClient with API key header
  - `sample_files`: temp .txt, .md, .pdf files for indexing

- [ ] **6.4** Write 15+ tests:
  1. `test_config_defaults` — defaults load without .env
  2. `test_config_env_override` — env vars override defaults
  3. `test_indexer_txt_file` — index .txt file, verify chunks in store
  4. `test_indexer_skip_unchanged` — same file hash → skip
  5. `test_indexer_remove_file` — remove deletes from store
  6. `test_indexer_directory` — recursive indexing
  7. `test_chunking_overlap` — verify overlap between chunks
  8. `test_vectorstore_add_query` — add docs, query returns results
  9. `test_vectorstore_delete_by_source` — delete filters correct docs
  10. `test_api_health` — GET /health → 200
  11. `test_api_auth_required` — POST /chat without key → 401
  12. `test_api_auth_valid` — POST /chat with key → not 401
  13. `test_api_index_path_validation` — path outside WATCH_PATHS → 403
  14. `test_api_stats` — GET /stats → valid JSON
  15. `test_graph_should_continue` — tool_calls → "tools", else END

- [ ] **6.5** Configure pytest
  ```toml
  # pyproject.toml
  [tool.pytest.ini_options]
  asyncio_mode = "auto"
  testpaths = ["tests"]
  ```

- [ ] **6.6** Run tests + measure coverage
  ```bash
  uv run pytest --cov=raven --cov-report=term-missing -v
  ```
  Target: 15 tests passing, ≥40% coverage di `rag/` dan `api/`.

**Checkpoint:** `uv run pytest` → 15+ green, coverage report generated.

---

## Day 8 (25 Apr) — Dev Tooling (Ruff + Mypy)

**Effort:** ~2 jam
**Files touched:** `pyproject.toml`, scattered type hints

### Tasks

- [ ] **8.1** Add ruff + mypy config
  ```toml
  # pyproject.toml
  [tool.ruff]
  target-version = "py312"
  line-length = 100
  
  [tool.ruff.lint]
  select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM"]
  ignore = ["E501"]  # line length handled by formatter
  
  [tool.ruff.format]
  quote-style = "double"
  
  [tool.mypy]
  python_version = "3.12"
  warn_return_any = true
  warn_unused_configs = true
  disallow_untyped_defs = false  # gradual adoption
  ```

- [ ] **8.2** Run ruff fix
  ```bash
  uv run ruff check --fix raven/
  uv run ruff format raven/
  ```

- [ ] **8.3** Run mypy — fix critical type errors only (gradual)
  ```bash
  uv run mypy raven/ --ignore-missing-imports
  ```

- [ ] **8.4** Add pre-commit hook (optional, nice-to-have)
  ```yaml
  # .pre-commit-config.yaml
  repos:
    - repo: https://github.com/astral-sh/ruff-pre-commit
      rev: v0.8.0
      hooks:
        - id: ruff
        - id: ruff-format
  ```

**Checkpoint:** `ruff check` → 0 errors. `mypy` → only known ignore-missing-imports warnings.

---

## Day 9 (28 Apr) — README + Health Check Enhancement

**Effort:** ~3 jam
**Files touched:** `README.md` (NEW), `raven/api/app.py`

### Tasks

- [ ] **9.1** Write README.md
  - Project description (personal AI assistant with local RAG + web access)
  - Architecture diagram (ASCII)
  - Prerequisites (Python 3.12, uv, Docker for Firecrawl/LiteLLM)
  - Quick start: `cp .env.example .env` → edit → `uv sync` → `./start.sh`
  - CLI usage: `uv run raven` + `/index <path>` + `/exit`
  - API endpoints table (method, path, description, auth required)
  - Environment variables table
  - Link to Bruno collection for manual testing
  - Contributing (run `ruff check`, `pytest` before PR)
  - License: Proprietary

- [ ] **9.2** Enhance health check
  ```python
  @app.get("/health")
  async def health():
      checks = {"api": "ok"}
      try:
          _store.count()
          checks["chroma"] = "ok"
      except Exception as e:
          checks["chroma"] = f"error: {e}"
      overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
      return {"status": overall, "checks": checks, "version": "0.2.0"}
  ```

- [ ] **9.3** Add `__version__` ke `raven/__init__.py`
  ```python
  __version__ = "0.2.0"
  ```

**Checkpoint:** README jelas, newcomer bisa setup dalam 10 menit. `/health` report status setiap dependency.

---

## Day 10 (29-30 Apr) — Integration Test + Tag v0.2.0

**Effort:** ~3 jam

### Tasks

- [ ] **10.1** End-to-end smoke test (manual)
  1. `uv sync` dari fresh clone
  2. `cp .env.example .env` + fill values
  3. `./start.sh` → server up
  4. `curl /health` → all green
  5. `curl /chat` without API key → 401
  6. `curl /chat` with API key → streaming response
  7. `curl /index` with valid path → indexed
  8. `curl /index` with invalid path → 403
  9. Restart server → session masih ada
  10. `uv run raven` → CLI works

- [ ] **10.2** Run full test suite
  ```bash
  uv run pytest --cov=raven --cov-report=html -v
  ```

- [ ] **10.3** Final ruff + mypy pass
  ```bash
  uv run ruff check raven/ tests/
  uv run mypy raven/
  ```

- [ ] **10.4** Update pyproject.toml version → 0.2.0

- [ ] **10.5** Git tag + push
  ```bash
  git add -A
  git commit -m "v0.2.0: hardening — auth, persistent sessions, true SSE, tests, README"
  git tag v0.2.0
  git push origin main --tags
  ```

**Checkpoint:** v0.2.0 tagged. All tests green. README complete. API secured. Sessions persistent.

---

## Sprint 1 Summary

| Day | Date | Focus | Deliverable |
|-----|------|-------|-------------|
| 1 | 17 Apr | Repo cleanup + security | `.env.example` clean, git history rewritten |
| 2 | 18 Apr | Auth + CORS + path guard | API secured, paths validated |
| 3 | 19 Apr | Persistent sessions | SqliteSaver integrated, sessions survive restart |
| 4 | 21 Apr | True SSE streaming | Per-token streaming, non-blocking `/index` |
| 5 | 22 Apr | Logging + error handling | structlog, narrow exceptions, streaming hash |
| 6-7 | 23-24 Apr | Test suite | 15+ tests, ≥40% coverage |
| 8 | 25 Apr | Dev tooling | ruff + mypy configured, code formatted |
| 9 | 28 Apr | README + health check | Documentation, enhanced `/health` |
| 10 | 29-30 Apr | Integration + v0.2.0 | Tag released, smoke tested |

**Total effort estimate:** ~26 jam (~2-3 jam/hari, 10 working days)
**Risk buffer:** Weekend 19-20 Apr + 26-27 Apr = 4 days slack

---

## Files Changed Summary

| File | Change type |
|------|-------------|
| `.env.example` | Modified (cleanup) |
| `.gitignore` | Modified (add exclusions) |
| `pyproject.toml` | Modified (deps, tooling config, version) |
| `raven/__init__.py` | Modified (add __version__) |
| `raven/config.py` | Modified (add auth, logging config) |
| `raven/api/app.py` | Heavy rewrite (auth, CORS, sessions, streaming, health) |
| `raven/graph/agent.py` | Modified (SqliteSaver, recursion_limit) |
| `raven/graph/nodes.py` | Modified (logging, iteration counter) |
| `raven/graph/tools.py` | Modified (logging) |
| `raven/rag/indexer.py` | Modified (logging, narrow exceptions, streaming hash) |
| `raven/rag/watcher.py` | Modified (logging) |
| `raven/logging_config.py` | **NEW** (structlog setup) |
| `README.md` | **NEW** |
| `tests/conftest.py` | **NEW** |
| `tests/test_config.py` | **NEW** |
| `tests/test_indexer.py` | **NEW** |
| `tests/test_vectorstore.py` | **NEW** |
| `tests/test_api.py` | **NEW** |
| `tests/test_graph.py` | **NEW** |
| `tests/test_watcher.py` | **NEW** |
