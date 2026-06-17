# Sprint 1 — Prompt Pack (Atomik per Sub-Task)

> Target agent: **Zed.ai IDE (Agent Panel)**
> Bahasa: **Indonesian**
> Granularitas: **1 prompt per sub-task** dari `SPRINT1_BREAKDOWN.md`
> Repo: `https://github.com/MuadzMuadz/Ryvn_Project.git`

---

## Cara Pakai

1. **Buka Zed di root project Ryvn.** Pastikan `raven/` source tree sudah ada (kalau belum, clone dulu dari repo di atas — lihat **PRE-0** di bawah).
2. **Sebelum setiap prompt:** cek CLAUDE.md (`Read CLAUDE.md before every task. Show a plan first. Never delete files without my approval.`).
3. **Copy satu prompt utuh** (dari "Konteks" sampai "Pagar pembatas") ke Agent Panel Zed.
4. **Review diff sebelum apply.** Zed default ngasih preview — manfaatkan.
5. **Commit setelah setiap sub-task selesai** dengan message format `sprint1/<day>.<num>: <short desc>` (CLAUDE.md project rules: commit setiap fix).
6. Setiap prompt sudah include **kriteria terima** dan **pagar pembatas** — agent wajib lapor kalau gak bisa penuhi.

**Aturan global untuk semua prompt di bawah** (implisit, boleh dirujuk):

- Jangan hapus file tanpa konfirmasi user.
- Jangan `git push --force`, jangan rewrite history, jangan `rm -rf` — minta user eksekusi manual.
- Jangan masukkan secret asli ke kode atau commit.
- Setelah perubahan, tampilkan ringkasan diff + verifikasi manual yang perlu dijalankan.

---

## PRE-0 — Clone Repo (kalau `raven/` belum ada)

```
Konteks:
Folder project saat ini cuma punya file config + docs, belum ada source tree `raven/`.
Repo sumber: https://github.com/MuadzMuadz/Ryvn_Project.git

Tugas:
1. Periksa apakah `raven/` sudah ada di working directory.
2. Kalau belum, clone dari repo di atas ke folder sementara lalu copy isinya (tanpa overwrite `.env`, `.env.example`, `SPRINT1_BREAKDOWN.md`, `ROADMAP_APR_JUN_2026.md`, `RYVN_ANALYSIS.md`, `CLAUDE.md`, `docs/`).
3. Laporkan file apa saja yang di-copy dan mana yang di-skip karena konflik.

Kriteria terima:
- `raven/` hadir dengan struktur minimal: `raven/__init__.py`, `raven/config.py`, `raven/api/app.py`, `raven/graph/`, `raven/rag/`.
- File-file existing di root (SPRINT, ROADMAP, ANALYSIS, .env) tetap utuh.

Pagar pembatas:
- Jangan hapus / overwrite file apapun di root yang sudah ada.
- Kalau `raven/` ternyata sudah ada, STOP dan lapor ke user — jangan auto-merge.
```

---

# DAY 1 (17 Apr) — Repo Cleanup & Security Fix

## 1.1 — Bersihkan `.env.example`

```
Konteks:
File `.env.example` di root repo bocorin API key asli (`sk-ZvPat...`), IP internal (`***REMOVED***`), dan username user di path `WATCH_PATHS`. Ini harus jadi template bersih, bukan leak artifact.

Tugas:
Edit `.env.example` supaya jadi template placeholder:
- `OPENAI_API_KEY=sk-your-openai-or-litellm-key`
- `OPENAI_BASE_URL=http://localhost:4000/v1`
- `OPENAI_MODEL=gpt-4o-mini` (biarkan)
- `FIRECRAWL_API_URL=http://localhost:3002` (biarkan)
- `FIRECRAWL_API_KEY=fc-local` (biarkan — bukan secret real)
- `EMBEDDING_MODEL=all-MiniLM-L6-v2` (biarkan)
- `CHROMA_PERSIST_DIR=./data/vectors` (biarkan)
- `WATCH_PATHS=/path/to/your/docs,/path/to/your/downloads`
- `INDEXED_EXTENSIONS=.txt,.md,.pdf,.docx,.py,.js,.ts,.json,.csv` (biarkan)
- TAMBAH blok baru di bagian paling bawah:
  ```
  # Auth (Sprint 1)
  API_KEY=replace-with-strong-random-string
  ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
  LOG_LEVEL=INFO
  ```

Kriteria terima:
- Tidak ada `sk-ZvPat` di file hasil.
- Tidak ada `***REMOVED***` atau username real di WATCH_PATHS.
- Blok auth (API_KEY, ALLOWED_ORIGINS, LOG_LEVEL) tersedia.

Pagar pembatas:
- Jangan sentuh file `.env` (yang asli) — hanya `.env.example`.
- Jangan commit `.env` (lihat task 1.2).
```

## 1.2 — Update `.gitignore`

```
Konteks:
`.gitignore` saat ini sudah exclude `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `data/vectors/`, `data/indexed/`, `data/uploads/`, `*.egg-info/`, `dist/`, `.DS_Store`. Sprint 1 mau tambah checkpoint SQLite + index state file.

Tugas:
Edit `.gitignore`. Tambahkan entri berikut (jangan duplikasi yang sudah ada):
- `data/` (generic — cover semua subfolder termasuk `sessions.db`)
- `*.db`
- `index_state.json`
- `*.egg-info/` → sudah ada, skip
- `.pytest_cache/`
- `htmlcov/`
- `.coverage`
- `.mypy_cache/`
- `.ruff_cache/`

Urutkan logis: virtual env → python caches → tooling caches → data/secrets.

Kriteria terima:
- `git check-ignore -v data/sessions.db` return positive.
- `git check-ignore -v index_state.json` return positive.
- Tidak ada baris duplikat.

Pagar pembatas:
- Jangan hapus entri lama yang sudah ada.
- Jangan `git rm --cached` apapun — itu task terpisah.
```

## 1.3 — Handoff: Git History Rewrite

```
Konteks:
`.env.example` pernah commit dengan API key asli (`sk-ZvPat...`). Walaupun sudah dibersihkan di working tree (task 1.1), key itu masih ada di git history dan dianggap compromised.

Tugas:
JANGAN jalankan rewrite history. Sebagai gantinya, HASILKAN file `docs/SPRINT1_DAY1_GIT_HISTORY_HANDOFF.md` yang berisi:

1. **Peringatan:** key sudah bocor — rotasi dulu di provider (LiteLLM / OpenAI) SEBELUM rewrite. Rewrite tidak membersihkan snapshot yang sudah di-clone orang lain.
2. **Langkah backup:**
   ```
   cd ..
   git clone --mirror https://github.com/MuadzMuadz/Ryvn_Project.git Ryvn_Project-backup.git
   ```
3. **Opsi A — git filter-repo (rekomendasi):**
   ```
   pip install git-filter-repo
   cd Ryvn_Project
   git filter-repo --path .env.example --invert-paths --force
   # Lalu add ulang .env.example bersih dan commit
   ```
4. **Opsi B — BFG:**
   ```
   echo "***REMOVED***" > /tmp/secrets.txt
   bfg --replace-text /tmp/secrets.txt
   git reflog expire --expire=now --all && git gc --prune=now --aggressive
   rm /tmp/secrets.txt
   ```
5. **Force push (IRREVERSIBLE):**
   ```
   git push origin --force --all
   git push origin --force --tags
   ```
6. **Catatan tim:** semua kontributor perlu re-clone. SHA lama jadi invalid.

Kriteria terima:
- File `docs/SPRINT1_DAY1_GIT_HISTORY_HANDOFF.md` ada dengan 6 bagian di atas.
- File sebutin eksplisit: "key rotation harus dulu, baru rewrite".

Pagar pembatas:
- JANGAN eksekusi `git filter-repo`, `bfg`, atau `git push --force` sendiri.
- JANGAN hapus `.env.example` — sudah di-cleanup di task 1.1.
```

## 1.4 — Tambah field auth ke `raven/config.py`

```
Konteks:
`raven/config.py` adalah loader env vars. Sprint 1 butuh 3 field baru untuk auth + CORS + logging.

Tugas:
Edit `raven/config.py`. Tambahkan di bawah definisi config existing:
```python
API_KEY = os.getenv("API_KEY", "")
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

Kalau file pakai pattern class/dataclass (bukan module-level constants), sesuaikan style — tapi semantiknya sama.

Kriteria terima:
- Import `from raven import config; print(config.API_KEY, config.ALLOWED_ORIGINS, config.LOG_LEVEL)` berhasil.
- Default `ALLOWED_ORIGINS` adalah list `["http://localhost:3000"]` bukan string.
- Empty string di ALLOWED_ORIGINS ter-filter (misal `"a,,b"` → `["a", "b"]`).

Pagar pembatas:
- Jangan ubah field config yang sudah ada.
- Jangan hardcode default API_KEY — biar kosong, validasi di middleware.
```

---

# DAY 2 (18 Apr) — Auth + CORS + Path Guard

## 2.1 — API Key Middleware

```
Konteks:
`raven/api/app.py` FastAPI app belum punya auth. Endpoint sensitif (`/chat`, `/index`, `/index/init`, `DELETE /session/{id}`) harus require header `X-API-Key`.

Tugas:
1. Di `raven/api/app.py`, tambahkan dependency baru:
   ```python
   from fastapi import Depends, Header, HTTPException

   def require_api_key(x_api_key: str | None = Header(default=None)):
       if config.API_KEY and x_api_key != config.API_KEY:
           raise HTTPException(status_code=401, detail="Invalid API key")
   ```
2. Tambahkan `dependencies=[Depends(require_api_key)]` ke route decorator untuk:
   - `POST /chat`
   - `POST /index`
   - `POST /index/init`
   - `DELETE /session/{session_id}`
3. Endpoint `GET /health` dan `GET /stats` tetap public (tidak butuh auth).

Kriteria terima:
- Kalau `config.API_KEY` kosong → semua request lolos (backward compat untuk dev).
- Kalau `config.API_KEY` di-set dan header salah/hilang → 401 dengan detail `"Invalid API key"`.
- Kalau header match → request lanjut normal.

Pagar pembatas:
- Jangan taruh API_KEY di response atau error message.
- Jangan bikin middleware global yang block semua route — pakai `Depends` per-route.
```

## 2.2 — CORS Lockdown

```
Konteks:
`raven/api/app.py` saat ini (diasumsikan) pakai `allow_origins=["*"]` di CORSMiddleware. Harus restrict ke origin dari config.

Tugas:
Di `raven/api/app.py`, temukan `app.add_middleware(CORSMiddleware, ...)` lalu ganti jadi:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

Kriteria terima:
- `allow_origins` referensi `config.ALLOWED_ORIGINS`, bukan list literal `"*"`.
- `allow_methods` eksplisit `["GET", "POST", "DELETE"]` (bukan `["*"]`).
- `allow_credentials=True`.

Pagar pembatas:
- Jangan tambah middleware baru yang konflik (misal reset headers).
- Kalau ternyata belum ada CORSMiddleware sama sekali, tambahkan dengan config ini.
```

## 2.3 — Path Validation di `/index` dan `/index/init`

```
Konteks:
Endpoint `/index` dan `/index/init` terima `path` dari request dan langsung pass ke indexer. Ini rawan path traversal + symlink escape. Harus restrict ke `config.WATCH_PATHS`.

Tugas:
1. Di `raven/api/app.py`, tambahkan helper:
   ```python
   from pathlib import Path

   ALLOWED_ROOTS = [Path(p).resolve() for p in config.WATCH_PATHS]

   def _validate_path(raw: str) -> Path:
       p = Path(raw).resolve()
       if p.is_symlink():
           raise HTTPException(status_code=403, detail="Symlinks not allowed")
       if not any(
           str(p) == str(root) or str(p).startswith(str(root) + "/")
           for root in ALLOWED_ROOTS
       ):
           raise HTTPException(status_code=403, detail="Path outside allowed roots")
       if not p.exists():
           raise HTTPException(status_code=404, detail="Path not found")
       return p
   ```
2. Di handler `/index` dan `/index/init`, panggil `validated = _validate_path(req.path)` sebelum pass ke indexer.
3. `ALLOWED_ROOTS` dihitung sekali di module load — jangan per-request.

Kriteria terima:
- Request `path=/etc/passwd` → 403 "Path outside allowed roots".
- Request `path=<watch_path>/../../etc` → 403 (karena `.resolve()` normalize dulu).
- Request path symlink → 403.
- Request path valid di dalam WATCH_PATHS → lanjut.

Pagar pembatas:
- `startswith(root + "/")` penting — cegah false match misal root=`/home/a` cocok dengan `/home/abc`.
- Jangan ubah schema request body (field name tetap `path`).
```

## 2.4 — Recursion Limit di Graph

```
Konteks:
`raven/graph/agent.py` compile graph tanpa `recursion_limit`. LangGraph default 25, tapi eksplisitkan biar jelas dan cegah infinite loop.

Tugas:
Di `raven/graph/agent.py`, temukan pemanggilan `.compile(...)` dan tambahkan `recursion_limit=25`. Contoh:
```python
_graph = g.compile(recursion_limit=25)
```
(Kalau task 3.2 sudah dijalankan duluan, checkpointer juga di-pass di sini — tapi untuk task 2.4 cukup recursion_limit saja.)

Kriteria terima:
- `recursion_limit=25` eksplisit di `.compile()`.
- Graph tetap bisa di-import tanpa error.

Pagar pembatas:
- Jangan ubah node structure atau edges.
- Kalau LangGraph version support `RunnableConfig` untuk set limit per-invoke, pilih cara `.compile` agar global.
```

---

# DAY 3 (19 Apr) — Persistent Sessions (SqliteSaver)

## 3.1 — Tambah Dependency `langgraph-checkpoint-sqlite`

```
Konteks:
Butuh checkpointer SQLite supaya session history survive restart.

Tugas:
Edit `pyproject.toml`. Di list `dependencies`, tambahkan:
```
"langgraph-checkpoint-sqlite>=2.0.0",
```
Urutkan alfabetis (langgraph-checkpoint-sqlite setelah `langgraph`). Lalu jalankan:
```
uv sync
```
dan laporkan output.

Kriteria terima:
- `pyproject.toml` punya entry baru.
- `uv.lock` ter-update.
- `uv run python -c "from langgraph.checkpoint.sqlite import SqliteSaver"` tidak error.

Pagar pembatas:
- Jangan ubah versi dep lain.
- Jangan downgrade `langgraph` — minimal `>=1.1.4` (existing).
```

## 3.2 — Integrasi SqliteSaver ke Graph

```
Konteks:
`raven/graph/agent.py` compile graph tanpa checkpointer. Sprint 1 Day 3 mau pakai SqliteSaver di `./data/sessions.db`.

Tugas:
Edit `raven/graph/agent.py`:
1. Import di atas:
   ```python
   from pathlib import Path
   from langgraph.checkpoint.sqlite import SqliteSaver
   import sqlite3
   ```
2. Di fungsi `get_graph()` (atau tempat `.compile()` dipanggil), pastikan folder `./data/` dibuat:
   ```python
   Path("./data").mkdir(parents=True, exist_ok=True)
   ```
3. Bikin checkpointer dan pass ke `.compile()`:
   ```python
   conn = sqlite3.connect("./data/sessions.db", check_same_thread=False)
   checkpointer = SqliteSaver(conn)
   _graph = g.compile(checkpointer=checkpointer, recursion_limit=25)
   ```
   Catatan: pakai `sqlite3.connect` langsung (bukan context manager) karena graph hidup selama server.

Kriteria terima:
- Setelah start server dan 1x `/chat`, file `data/sessions.db` muncul.
- Tabel `checkpoints` ada di DB (cek: `sqlite3 data/sessions.db ".tables"`).

Pagar pembatas:
- Jangan pakai `:memory:` — harus file-based.
- `check_same_thread=False` wajib untuk FastAPI async workers.
- Jangan delete DB existing — kalau ada, biarkan.
```

## 3.3 — Refactor `app.py`: hapus `_sessions` dict

```
Konteks:
`raven/api/app.py` punya manual `_sessions: dict` untuk nyimpen history per session. Sekarang checkpointer yang urus — state management manual jadi dead code.

Tugas:
Edit `raven/api/app.py`:
1. Hapus deklarasi `_sessions: dict[str, ...] = {}` (dan annotation type-nya).
2. Setiap `graph.invoke(...)` atau `graph.astream_events(...)` wajib pakai config:
   ```python
   cfg = {"configurable": {"thread_id": session_id}}
   await graph.ainvoke(state, config=cfg)
   # atau
   async for event in graph.astream_events(state, config=cfg, version="v2"):
       ...
   ```
3. `DELETE /session/{session_id}` harus hapus thread dari checkpointer:
   ```python
   # Sementara: drop rows manual via sqlite3 (LangGraph belum ekspose delete API stabil)
   import sqlite3
   conn = sqlite3.connect("./data/sessions.db")
   conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (session_id,))
   conn.execute("DELETE FROM writes WHERE thread_id = ?", (session_id,))
   conn.commit()
   conn.close()
   ```
   Wrap dengan try/except + log.

Kriteria terima:
- `_sessions` dict tidak ada lagi di file.
- `/chat` tetap jalan (history di-resume dari checkpointer).
- `DELETE /session/<id>` hapus row dari `checkpoints` tabel.

Pagar pembatas:
- Jangan `DROP TABLE` atau delete semua row — hanya thread_id yang diminta.
- Jangan ubah schema request/response body.
```

## 3.4 — Update `/stats` Endpoint

```
Konteks:
`/stats` sebelumnya laporin `session_count` dari `len(_sessions)`. Sekarang `_sessions` dihapus — source of truth adalah SQLite.

Tugas:
Edit handler `/stats` di `raven/api/app.py`. Ganti session count jadi hasil query:
```python
import sqlite3

def _count_sessions() -> int:
    try:
        conn = sqlite3.connect("./data/sessions.db")
        cur = conn.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints")
        (n,) = cur.fetchone()
        conn.close()
        return int(n)
    except sqlite3.Error:
        return 0
```
Panggil `_count_sessions()` di dalam handler. Field lain di response (`document_count`, dll) biarkan.

Kriteria terima:
- `GET /stats` return JSON dengan `session_count` dari DB.
- Kalau DB belum ada, `session_count == 0` (tidak throw).

Pagar pembatas:
- Jangan bikin koneksi global ke SQLite di module scope — open/close per call (cheap).
- Jangan ekspos thread_id atau isi checkpoint di `/stats`.
```

## 3.5 — Auto-create Folder `data/`

```
Konteks:
SqliteSaver dan Chroma butuh folder `data/`. Kalau user fresh clone, folder belum ada → error saat startup.

Tugas:
Di `raven/api/app.py` (atau entry point umum), tambahkan startup hook:
```python
from pathlib import Path

@app.on_event("startup")
async def _ensure_data_dirs():
    Path("./data").mkdir(parents=True, exist_ok=True)
    Path("./data/vectors").mkdir(parents=True, exist_ok=True)
```

(FastAPI `on_event("startup")` deprecated di 0.95+ — kalau version mendukung, pakai lifespan context manager sebagai gantinya:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("./data").mkdir(parents=True, exist_ok=True)
    Path("./data/vectors").mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(lifespan=lifespan)
```
Pilih yang sesuai dengan version.)

Kriteria terima:
- Hapus `data/` → start server → folder `data/` dan `data/vectors/` ter-create.

Pagar pembatas:
- `exist_ok=True` wajib — jangan throw kalau sudah ada.
- Jangan buat file dummy di dalam folder.
```

---

# DAY 4 (21 Apr) — True SSE Streaming

## 4.1 — Per-Token SSE Streaming

```
Konteks:
`raven/api/app.py` saat ini di handler `/chat` collect semua LLM chunk ke list `full_answer` lalu yield sekali di akhir. Ini bukan true streaming — client nunggu respon lengkap dulu. Harus yield per-token.

Tugas:
Temukan blok `async for event in graph.astream_events(...)` di handler `/chat`. Cari branch `elif kind == "on_chat_model_stream":` dan ubah jadi:
```python
elif kind == "on_chat_model_stream":
    chunk = data.get("chunk")
    if chunk and getattr(chunk, "content", None):
        yield {
            "event": "token",
            "data": json.dumps({"text": chunk.content}),
        }
```
Hapus akumulator `full_answer = []` dan yield final `"message"` setelah loop. Kalau ada logic yang gabungin full text untuk simpan ke state, pindahin collect-nya ke bagian `on_chain_end` atau biarkan checkpointer yang simpan.

Kriteria terima:
- Jalankan `curl -N -H "X-API-Key: $KEY" -X POST /chat -d '{"message":"hi"}'` → event `token` muncul multiple kali (bukan sekali `message`).
- Tidak ada variabel `full_answer` di handler.

Pagar pembatas:
- Jangan hilangkan event lain (`retrieval`, `tool_start`, `tool_end`, `done`).
- Kalau chunk kosong (content `""`) → skip, jangan yield empty token.
```

## 4.2 — Update SSE Events Schema

```
Konteks:
Setelah task 4.1, event `message` gak ada lagi. Schema perlu di-dokumentasikan biar client tau apa yang datang.

Tugas:
1. Di `raven/api/app.py`, tambahkan docstring / comment di atas handler `/chat` yang list semua event SSE:
   - `retrieval` — retrieved docs (field: `docs`)
   - `tool_start` — tool call initiated (field: `name`, `input`)
   - `tool_end` — tool result (field: `name`, `output`)
   - `token` — individual LLM token (field: `text`) — NEW
   - `done` — stream complete (field: `session_id`)
2. Pastikan event `done` di-emit sekali di akhir loop dengan payload `{"session_id": ...}`.
3. Kalau ada Bruno collection / docs yang refer ke event `message`, update reference ke `token`.

Kriteria terima:
- Docstring handler list 5 event di atas.
- Event `done` selalu di-emit terakhir, bahkan kalau error di tengah (pakai try/finally).

Pagar pembatas:
- Jangan rename event existing (`retrieval`, `tool_start`, `tool_end`, `done`) — cuma tambah `token` dan retire `message`.
- Jangan ubah kontrak `data` jadi non-JSON (tetap `json.dumps(...)`).
```

## 4.3 — Fix Deprecated Event Loop di `/index/init`

```
Konteks:
Handler `/index/init` pakai `asyncio.get_event_loop()` yang deprecated di Python 3.10+ (emit DeprecationWarning di 3.12, bakal error di 3.14).

Tugas:
Di `raven/api/app.py` handler `/index/init`, ganti:
```python
loop = asyncio.get_event_loop()
```
jadi:
```python
loop = asyncio.get_running_loop()
```
Cari occurrence lain dari `get_event_loop()` di file yang sama — ganti semua kalau context-nya di dalam async function.

Kriteria terima:
- `grep -n "get_event_loop" raven/api/app.py` → 0 hasil (kecuali kalau ada di sync function legit).
- `python -W error::DeprecationWarning -c "import raven.api.app"` tidak throw.

Pagar pembatas:
- `get_running_loop()` hanya valid di dalam async function. Kalau ada pemanggilan di sync context, harus pakai `asyncio.new_event_loop()` atau refactor lebih jauh — lapor balik kalau ketemu kasus ini.
```

## 4.4 — Non-Blocking `/index` via `run_in_executor`

```
Konteks:
Handler `/index` panggil `indexer.index_file(path)` langsung — itu blocking (I/O + CPU untuk embedding). Di FastAPI async route, ini bikin event loop stuck dan semua request lain mandek.

Tugas:
Di `raven/api/app.py` handler `/index`, wrap pemanggilan indexer:
```python
import asyncio

loop = asyncio.get_running_loop()
validated_path = _validate_path(req.path)
n = await loop.run_in_executor(None, indexer.index_file, validated_path)
```
Kalau `index_file` return dict/object (bukan int), sesuaikan — tapi tetap pakai `run_in_executor`.

Kalau handler punya sync variant (misal untuk batch), sync boleh tetap sync.

Kriteria terima:
- `/index` tidak block `/health` — test manual: post `/index` dengan folder besar, sambil itu hit `/health` — `/health` harus responsif.
- `await` present di pemanggilan indexer.

Pagar pembatas:
- Jangan pindah logic indexer ke async — library-nya sync, biarkan.
- Jangan pakai thread pool custom kecuali ada alasan kuat.
```

---

# DAY 5 (22 Apr) — Structured Logging + Error Handling

## 5.1 — Tambah Dependency `structlog`

```
Konteks:
Project pakai `print()` dan `logging` bare. Butuh structured logging untuk production observability.

Tugas:
Edit `pyproject.toml`, tambah di `dependencies`:
```
"structlog>=24.0.0",
```
Urutkan alfabetis. Jalankan `uv sync`. Laporkan output.

Kriteria terima:
- `uv run python -c "import structlog; print(structlog.__version__)"` print versi >= 24.0.0.
- `uv.lock` ter-update.

Pagar pembatas:
- Jangan tambah dep logging lain (loguru, etc.) — stick ke structlog.
```

## 5.2 — Bikin `raven/logging_config.py`

```
Konteks:
Butuh file dedicated untuk setup structlog supaya semua entry point (FastAPI, CLI, worker) konsisten.

Tugas:
Buat file BARU `raven/logging_config.py`:
```python
"""Structlog configuration for Ryvn."""
from __future__ import annotations

import logging
import os

import structlog


def setup_logging() -> None:
    """Configure structlog for dev (console) or production (JSON)."""
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        level=log_level,
    )

    is_production = os.getenv("RYVN_ENV", "").lower() == "production"
    renderer = (
        structlog.processors.JSONRenderer()
        if is_production
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

Panggil `setup_logging()` dari:
- `raven/api/app.py` (di awal module atau di lifespan)
- `raven/main.py` (CLI entry) kalau ada

Kriteria terima:
- `from raven.logging_config import setup_logging, get_logger` berhasil.
- Server startup log-nya pakai format structlog (berwarna di dev, JSON di production).

Pagar pembatas:
- Jangan buang stdlib `logging.basicConfig` — dep lain (uvicorn, httpx) masih pakai stdlib.
- Jangan force level ke DEBUG di code — hormati env var.
```

## 5.3 — Ganti `print()` / bare `logging` dengan structlog

```
Konteks:
File `raven/api/app.py`, `raven/rag/indexer.py`, `raven/graph/nodes.py`, `raven/graph/tools.py`, `raven/rag/watcher.py` pakai `print()` atau `logging.info()` generik. Migrasi ke structlog dengan structured fields.

Tugas:
Untuk tiap file di atas:
1. Import: `from raven.logging_config import get_logger` lalu `logger = get_logger(__name__)` di top-level.
2. Ganti semua `print(...)` dan `logging.xxx(...)` jadi `logger.info("event_name", key=value, ...)` atau level sesuai.
3. Event name pakai snake_case, deskriptif:
   - `app.py`: `request_received`, `request_completed` (method, path, session_id, latency_ms, status)
   - `indexer.py`: `file_indexed` (path, chunks, bytes), `file_skipped` (path, reason), `file_failed` (path, error)
   - `nodes.py`: `retrieval_done` (count, query), `tool_called` (name, args_summary), `llm_invoked` (model, tokens_in)
   - `tools.py`: `tool_start`, `tool_end` (name, duration_ms, success)
   - `watcher.py`: `file_event` (type in [created, modified, deleted, moved], path)
4. Untuk latency, wrap handler dengan `time.perf_counter()` di awal/akhir.

Kriteria terima:
- `grep -rn "^\s*print(" raven/` → 0 hasil (kecuali di CLI output yang legit).
- `grep -rn "logging\." raven/` hanya muncul di `logging_config.py` dan `logging.basicConfig`.
- Start server + 1 request → log JSON (atau console) punya field `event`, `level`, `timestamp`.

Pagar pembatas:
- Jangan log isi full chat message atau content user (PII). Log summary: length, hash, session_id.
- Jangan log API_KEY, file absolute paths di luar WATCH_PATHS, atau stack trace exception full di level INFO (pakai level ERROR).
```

## 5.4 — Narrow Exception Handling di `indexer.py`

```
Konteks:
`raven/rag/indexer.py` pakai `except Exception: return 0` — ini swallow semua error termasuk KeyboardInterrupt / bug logic.

Tugas:
Di `raven/rag/indexer.py`:
1. Identifikasi semua `except Exception:` yang terlalu luas.
2. Ganti dengan exception spesifik sesuai konteks:
   ```python
   from pypdf.errors import PdfReadError

   try:
       ... # PDF read logic
   except (PdfReadError, UnicodeDecodeError, OSError, ValueError) as e:
       logger.warning("index_file_failed", path=str(path), error=str(e), error_type=type(e).__name__)
       return 0
   ```
3. Untuk branch `.docx` pakai exception dari `docx2txt` (atau `OSError` + `KeyError`).
4. Tambah logging `.warning` dengan field structured.

Kriteria terima:
- `grep -n "except Exception" raven/rag/indexer.py` → 0 hasil (atau 1 hasil kalau memang perlu catch-all di outer loop dengan logger.exception).
- File error (corrupt PDF) di-log dengan level WARNING, bukan silent return.

Pagar pembatas:
- Jangan `raise` ulang exception di hot path (itu break indexing flow).
- Jangan log seluruh content file — hanya metadata.
```

## 5.5 — Streaming File Hash (cegah OOM)

```
Konteks:
`raven/rag/indexer.py` mungkin baca whole file ke memory buat hash. File besar (>1GB) → OOM.

Tugas:
Di `raven/rag/indexer.py`, temukan fungsi `_file_hash` (atau yang serupa) dan ubah jadi:
```python
import hashlib
from pathlib import Path

def _file_hash(path: Path, chunk: int = 1 << 20) -> str:
    """SHA-256 hash dari file, baca chunk-by-chunk."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while blob := f.read(chunk):
            h.update(blob)
    return h.hexdigest()[:16]
```
Kalau belum ada fungsi hash, tambah function ini dan pakai di `index_file` untuk dedupe state.

Kriteria terima:
- Hash 1GB file tidak spike memory > 10MB (manual verify via `top` / `psutil`).
- `_file_hash` return string hex 16 char.

Pagar pembatas:
- Jangan ganti algoritma (tetap sha256 untuk consistency dengan `index_state.json`).
- Kalau `index_state.json` existing pakai hash full 64-char, JANGAN truncate — pertahankan schema.
```

## 5.6 — Graph Iteration Counter di `nodes.py`

```
Konteks:
Graph bisa loop antara `agent_node` → `tools` → `agent_node`. Tanpa counter, hard untuk debug kalau recursion limit hit.

Tugas:
Di `raven/graph/nodes.py` fungsi `agent_node`:
1. Baca counter dari state:
   ```python
   metadata = state.get("metadata", {}) or {}
   iteration = metadata.get("iteration", 0) + 1
   ```
2. Log:
   ```python
   logger.info("agent_iteration", iteration=iteration, session_id=state.get("session_id"))
   ```
3. Return state dengan metadata ter-update:
   ```python
   return {
       ...,
       "metadata": {**metadata, "iteration": iteration},
   }
   ```
(Sesuaikan dengan schema state existing — kalau State pakai TypedDict, pastikan `metadata` field ada.)

Kriteria terima:
- Log `agent_iteration iteration=1,2,3,...` muncul per invoke.
- State schema tetap valid (tidak break existing fields).

Pagar pembatas:
- Kalau `metadata` bukan field existing di State, tambah ke schema dulu (dan dokumentasi-kan).
- Jangan increment counter di tool node — hanya agent node.
```

---

# DAY 6-7 (23-24 Apr) — Test Suite

## 6.1 — Tambah Test Dependencies

```
Konteks:
Project belum ada tests. Butuh pytest + httpx (FastAPI TestClient) + coverage.

Tugas:
Edit `pyproject.toml`, ubah `[dependency-groups] dev`:
```
[dependency-groups]
dev = [
    "ipython",
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5",
    "httpx>=0.27",
]
```
Jalankan `uv sync`. Laporkan output.

Kriteria terima:
- `uv run pytest --version` print versi >= 8.
- `uv run python -c "import httpx, pytest_asyncio; print('ok')"` → `ok`.

Pagar pembatas:
- Jangan hapus `ipython` dari dev group.
- Jangan tambah ke `dependencies` utama — hanya dev group.
```

## 6.2 — Bikin Struktur Folder `tests/`

```
Konteks:
Belum ada folder `tests/`. Butuh skeleton sebelum tulis test body.

Tugas:
Bikin file-file kosong (atau minimal stub) di:
```
tests/__init__.py                # empty
tests/conftest.py                # fixtures (task 6.3)
tests/test_config.py             # stub (task 6.4)
tests/test_indexer.py            # stub (task 6.4)
tests/test_vectorstore.py        # stub (task 6.4)
tests/test_api.py                # stub (task 6.4)
tests/test_graph.py              # stub (task 6.4)
tests/test_watcher.py            # stub (task 6.4)
```

Setiap stub file minimal berisi docstring placeholder:
```python
"""Tests for <module>. Populated in task 6.4."""
```

Kriteria terima:
- `uv run pytest` jalankan 0 test tanpa error collection.
- Semua 7 file ada.

Pagar pembatas:
- Jangan tulis test body dulu — itu task 6.4.
```

## 6.3 — Tulis `conftest.py` Fixtures

```
Konteks:
Fixture dasar untuk semua test file.

Tugas:
Isi `tests/conftest.py`:
```python
"""Shared pytest fixtures."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Pastikan env var ter-set SEBELUM import raven
os.environ.setdefault("API_KEY", "test-key-123")
os.environ.setdefault("WATCH_PATHS", "/tmp/ryvn-test-watch")
os.environ.setdefault("CHROMA_PERSIST_DIR", "/tmp/ryvn-test-chroma")


@pytest.fixture
def tmp_chroma_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated Chroma dir per test."""
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(chroma))
    return chroma


@pytest.fixture
def tmp_watch_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Writable watch path for indexer tests."""
    watch = tmp_path / "watch"
    watch.mkdir()
    monkeypatch.setenv("WATCH_PATHS", str(watch))
    return watch


@pytest.fixture
def sample_txt(tmp_watch_path: Path) -> Path:
    p = tmp_watch_path / "sample.txt"
    p.write_text("Hello Ryvn. This is a sample document for testing RAG.")
    return p


@pytest.fixture
def sample_md(tmp_watch_path: Path) -> Path:
    p = tmp_watch_path / "doc.md"
    p.write_text("# Title\n\nParagraph about LangGraph and agents.")
    return p


@pytest.fixture
def mock_llm() -> MagicMock:
    """Fake LLM returning scripted responses."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="mocked answer", tool_calls=[])
    return llm


@pytest.fixture
def api_client(tmp_chroma_dir: Path, tmp_watch_path: Path) -> Iterator[TestClient]:
    """FastAPI TestClient with API_KEY header helper."""
    from raven.api.app import app  # import after env vars set

    client = TestClient(app)
    client.headers.update({"X-API-Key": "test-key-123"})
    yield client


@pytest.fixture
def api_client_noauth(tmp_chroma_dir: Path, tmp_watch_path: Path) -> Iterator[TestClient]:
    """TestClient TANPA header API_KEY — untuk test 401."""
    from raven.api.app import app

    client = TestClient(app)
    yield client
```

Kriteria terima:
- `uv run pytest --collect-only` collect 0 test tapi import conftest tanpa error.
- Fixture `api_client` dan `tmp_chroma_dir` bisa di-inject ke test.

Pagar pembatas:
- Jangan set env var ke value production.
- Jangan import `raven.api.app` di top-level conftest — harus lazy (di fixture) supaya env var di-set dulu.
```

## 6.4 — Tulis 15 Test

```
Konteks:
Target: 15 test green, cover config, indexer, vectorstore, API, graph.

Tugas:
Isi 5 file test dengan body berikut (split per file sesuai area). Semua test HARUS passing. Boleh skip test yang butuh dep external (misal model download) dengan `@pytest.mark.skipif`.

### tests/test_config.py (2 test)
```python
import importlib
import os

import pytest


def test_config_defaults(monkeypatch: pytest.MonkeyPatch):
    for k in ("API_KEY", "ALLOWED_ORIGINS", "LOG_LEVEL"):
        monkeypatch.delenv(k, raising=False)
    import raven.config as cfg
    importlib.reload(cfg)
    assert cfg.API_KEY == ""
    assert cfg.LOG_LEVEL == "INFO"
    assert cfg.ALLOWED_ORIGINS == ["http://localhost:3000"]


def test_config_env_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_KEY", "xyz")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://a.com, http://b.com")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    import raven.config as cfg
    importlib.reload(cfg)
    assert cfg.API_KEY == "xyz"
    assert "http://a.com" in cfg.ALLOWED_ORIGINS
    assert "http://b.com" in cfg.ALLOWED_ORIGINS
    assert cfg.LOG_LEVEL == "DEBUG"
```

### tests/test_indexer.py (4 test)
```python
from pathlib import Path
import pytest


def test_indexer_txt_file(sample_txt: Path, tmp_chroma_dir: Path):
    from raven.rag.indexer import Indexer  # sesuaikan nama class
    idx = Indexer()
    n = idx.index_file(sample_txt)
    assert n > 0


def test_indexer_skip_unchanged(sample_txt: Path, tmp_chroma_dir: Path):
    from raven.rag.indexer import Indexer
    idx = Indexer()
    n1 = idx.index_file(sample_txt)
    n2 = idx.index_file(sample_txt)  # hash sama → skip
    assert n1 > 0
    assert n2 == 0


def test_indexer_directory(tmp_watch_path: Path, sample_txt: Path, sample_md: Path, tmp_chroma_dir: Path):
    from raven.rag.indexer import Indexer
    idx = Indexer()
    n = idx.index_directory(tmp_watch_path)
    assert n >= 2


def test_chunking_overlap(sample_txt: Path):
    """Chunk punya overlap (kalau config chunk_overlap > 0)."""
    from raven.rag.indexer import Indexer
    idx = Indexer()
    chunks = idx._chunk_text(sample_txt.read_text())  # akses helper
    assert len(chunks) >= 1
```
(Adjust nama class/method sesuai source real. Kalau tidak ada helper `_chunk_text`, ganti dengan test behavior lain.)

### tests/test_vectorstore.py (2 test)
```python
def test_vectorstore_add_query(tmp_chroma_dir):
    from raven.rag.vectorstore import VectorStore  # sesuaikan
    vs = VectorStore()
    vs.add([{"text": "LangGraph helps build agent loops.", "source": "doc1"}])
    results = vs.query("agent loops", k=1)
    assert len(results) >= 1


def test_vectorstore_delete_by_source(tmp_chroma_dir):
    from raven.rag.vectorstore import VectorStore
    vs = VectorStore()
    vs.add([
        {"text": "foo", "source": "a"},
        {"text": "bar", "source": "b"},
    ])
    vs.delete_by_source("a")
    results = vs.query("foo", k=5)
    assert all(r.get("source") != "a" for r in results)
```

### tests/test_api.py (5 test)
```python
def test_api_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") in {"ok", "degraded"}


def test_api_auth_required(api_client_noauth):
    r = api_client_noauth.post("/chat", json={"message": "hi", "session_id": "s1"})
    assert r.status_code == 401


def test_api_auth_valid(api_client):
    # Cukup cek bukan 401; isi response bisa apa aja (mungkin 500 kalau LLM gak connect)
    r = api_client.post("/chat", json={"message": "hi", "session_id": "s1"})
    assert r.status_code != 401


def test_api_index_path_validation(api_client):
    r = api_client.post("/index", json={"path": "/etc/passwd"})
    assert r.status_code == 403


def test_api_stats(api_client):
    r = api_client.get("/stats")
    assert r.status_code == 200
    body = r.json()
    assert "session_count" in body
```

### tests/test_graph.py (2 test)
```python
def test_graph_should_continue_with_tool_calls():
    from raven.graph.nodes import should_continue
    state = {"messages": [type("M", (), {"tool_calls": [{"name": "search"}]})()]}
    assert should_continue(state) == "tools"


def test_graph_should_continue_end():
    from raven.graph.nodes import should_continue
    state = {"messages": [type("M", (), {"tool_calls": []})()]}
    assert should_continue(state) in {"__end__", "end", None}
```

Kriteria terima:
- `uv run pytest -v` → 15 passed.
- Tidak ada test yang pakai network external (LLM / Firecrawl) — mock atau skip.

Pagar pembatas:
- Adjust import path / class name kalau source beda. Kalau ada ambiguitas, baca source dulu lalu adapt.
- Jangan monkey-patch `raven.config` di test luar pakai fixture — pakai monkeypatch.
```

## 6.5 — Configure Pytest

```
Konteks:
Default pytest belum auto-mode async. Harus aktifkan supaya test async jalan.

Tugas:
Edit `pyproject.toml`, tambahkan:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra --strict-markers"
filterwarnings = [
    "error::DeprecationWarning:raven.*",
]
```

Kriteria terima:
- `uv run pytest -v` pick up tests tanpa arg `tests/`.
- Async test (kalau ada) jalan tanpa `@pytest.mark.asyncio`.

Pagar pembatas:
- Jangan set `filterwarnings = ["error"]` global — hanya untuk `raven.*` biar gak strict ke dep.
```

## 6.6 — Jalankan Test + Coverage

```
Konteks:
Target: 15 test green, coverage ≥ 40% di `rag/` dan `api/`.

Tugas:
1. Run:
   ```
   uv run pytest --cov=raven --cov-report=term-missing --cov-report=html -v
   ```
2. Simpan output text ke `docs/SPRINT1_DAY7_COVERAGE.md` (manual copy-paste atau `| tee`).
3. Kalau ada test fail → lapor mana yang fail dan root cause, jangan silent skip.
4. Kalau coverage < 40% di `rag/` atau `api/`, tambah 1-2 test kecil sampai target tercapai (test edge case, e.g. empty input).

Kriteria terima:
- 15+ test passed.
- `htmlcov/index.html` ada.
- Coverage `rag/` dan `api/` ≥ 40%.
- File `docs/SPRINT1_DAY7_COVERAGE.md` berisi ringkasan coverage.

Pagar pembatas:
- Jangan hapus test yang fail — fix source atau test-nya.
- Jangan `--no-cov` — coverage WAJIB di run ini.
```

---

# DAY 8 (25 Apr) — Dev Tooling (Ruff + Mypy)

## 8.1 — Config Ruff + Mypy di `pyproject.toml`

```
Konteks:
Belum ada linter/type checker config. Standardize pakai ruff (lint + format) dan mypy (gradual).

Tugas:
Edit `pyproject.toml`, tambahkan section:
```toml
[tool.ruff]
target-version = "py312"
line-length = 100
src = ["raven", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM", "RUF"]
ignore = ["E501"]  # line length dihandle formatter

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # gradual
ignore_missing_imports = true
pretty = true
```

Tambah juga ke `[dependency-groups] dev`:
```
"ruff>=0.8.0",
"mypy>=1.13",
```

Jalankan `uv sync`. Laporkan.

Kriteria terima:
- `uv run ruff --version` dan `uv run mypy --version` print versi.
- Config section lengkap di `pyproject.toml`.

Pagar pembatas:
- Jangan aktifkan `disallow_untyped_defs = true` (terlalu strict untuk gradual adoption).
- Jangan tambah rule ruff yang bikin massive churn (misal `D` untuk pydocstyle).
```

## 8.2 — Run Ruff Fix

```
Konteks:
Jalankan ruff auto-fix dan format di source tree.

Tugas:
1. `uv run ruff check --fix raven/ tests/`
2. `uv run ruff format raven/ tests/`
3. Review diff. Kalau ada perubahan yang ubah behavior (bukan cuma cosmetic), highlight ke user — JANGAN auto-commit.
4. Commit hasilnya (kalau user OK) dengan message: `sprint1/8.2: ruff check --fix + format`.

Kriteria terima:
- `uv run ruff check raven/ tests/` → "All checks passed!"
- `uv run ruff format --check raven/ tests/` → "X files already formatted".

Pagar pembatas:
- Kalau ruff suggest `noqa` massal → pilih fix yang minimal, lapor balik.
- Jangan auto-fix rule `F401` (unused import) di `__init__.py` re-exports — tambah `# noqa: F401`.
```

## 8.3 — Run Mypy

```
Konteks:
Jalankan mypy untuk catch type error kritis. Gradual — hanya fix yang critical (bug beneran), sisanya ignore dengan komentar.

Tugas:
1. `uv run mypy raven/`
2. Untuk tiap error:
   - Kalau error = bug nyata (misal return type salah, None deref) → fix source.
   - Kalau error = library tanpa stub (import-untyped) → config sudah `ignore_missing_imports=true`, harusnya silent.
   - Kalau error = incompatible types di edge case rare → tambah `# type: ignore[error-code]` dengan komentar alasan.
3. Laporkan jumlah error sebelum/sesudah.

Kriteria terima:
- `uv run mypy raven/` → error count berkurang signifikan (target: 0 error critical, sisanya ignore eksplisit).
- Tidak ada `# type: ignore` tanpa error code spesifik.

Pagar pembatas:
- Jangan ubah logic demi bikin mypy happy — kalau ambigu, `# type: ignore` + komentar.
- Jangan aktifkan `strict = true` di config.
```

## 8.4 — Pre-commit Hook (Opsional)

```
Konteks:
Optional nice-to-have: pre-commit hook untuk auto-ruff sebelum commit.

Tugas:
Bikin file BARU `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: [--maxkb=1024]
```

Tambah ke README nanti (task 9.1) instruksi: `pip install pre-commit && pre-commit install`.

Kriteria terima:
- File `.pre-commit-config.yaml` ada dan valid YAML.

Pagar pembatas:
- Jangan install pre-commit di CI — ini local dev only (untuk sekarang).
- Jangan tambah hook yang slow (misal bandit, semgrep) — Sprint 2+.
```

---

# DAY 9 (28 Apr) — README + Health Check

## 9.1 — Tulis `README.md`

```
Konteks:
Project belum ada `README.md` di root (hanya docs di `docs/`). Newcomer wajib bisa setup dalam 10 menit.

Tugas:
Bikin file BARU `README.md` di root dengan struktur berikut (dalam Bahasa Indonesia + English hybrid untuk command):

1. **Judul + 1-sentence description**
   `Ryvn — personal AI assistant dengan local RAG (ChromaDB) dan web access via Firecrawl.`

2. **Architecture (ASCII diagram sederhana)**
   ```
   ┌─────────┐   ┌──────────────┐   ┌─────────────┐
   │  CLI /  │──▶│  FastAPI     │──▶│  LangGraph  │
   │  Client │◀──│  (SSE)       │◀──│  Agent      │
   └─────────┘   └──────┬───────┘   └──────┬──────┘
                        │                  │
                  ┌─────▼─────┐      ┌────▼────┐
                  │  Chroma   │      │ Tools:  │
                  │  (RAG)    │      │ search, │
                  └───────────┘      │ fetch,  │
                                     │ index   │
                                     └─────────┘
   ```

3. **Prerequisites**
   - Python 3.12+
   - uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
   - Docker (untuk Firecrawl + LiteLLM proxy)

4. **Quick Start**
   ```bash
   git clone https://github.com/MuadzMuadz/Ryvn_Project.git
   cd Ryvn_Project
   cp .env.example .env
   # edit .env: API_KEY, OPENAI_API_KEY, WATCH_PATHS
   uv sync
   ./start.sh
   ```

5. **CLI Usage**
   ```bash
   uv run raven
   # di dalam REPL:
   /index /path/to/docs
   /exit
   ```

6. **API Endpoints** (tabel)
   | Method | Path | Auth | Deskripsi |
   |--------|------|------|-----------|
   | GET    | /health | No | Health check dengan status dependency |
   | GET    | /stats | No | Session count + document count |
   | POST   | /chat | Yes | SSE streaming chat (events: retrieval, tool_start, tool_end, token, done) |
   | POST   | /index | Yes | Index single file / folder |
   | POST   | /index/init | Yes | Full re-index |
   | DELETE | /session/{id} | Yes | Hapus session history |

7. **Environment Variables** (tabel, referensi `.env.example`)

8. **Testing Manual via Bruno**
   Link ke Bruno collection (kalau ada) atau `curl` examples:
   ```bash
   curl -H "X-API-Key: $API_KEY" http://localhost:1802/health
   curl -N -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
        -X POST http://localhost:1802/chat \
        -d '{"message":"hello","session_id":"s1"}'
   ```

9. **Development**
   ```bash
   uv run ruff check raven/ tests/
   uv run ruff format raven/ tests/
   uv run mypy raven/
   uv run pytest --cov=raven -v
   ```

10. **License** — Proprietary.

Kriteria terima:
- README.md di root dengan 10 section di atas.
- Semua command runnable (copy-paste).

Pagar pembatas:
- Jangan masukkan secret asli atau IP internal.
- Jangan klaim fitur yang belum ada (misal "Windows support" kalau belum tested).
```

## 9.2 — Enhance Health Check

```
Konteks:
`/health` saat ini return `{"status": "ok"}` statis. Harus cek dependency nyata (Chroma, SQLite checkpoint, LLM endpoint).

Tugas:
Edit handler `GET /health` di `raven/api/app.py`:
```python
@app.get("/health")
async def health():
    checks: dict[str, str] = {"api": "ok"}

    # Chroma
    try:
        _ = _store.count()  # atau method equivalent
        checks["chroma"] = "ok"
    except Exception as e:
        checks["chroma"] = f"error: {type(e).__name__}"

    # Sessions DB
    try:
        import sqlite3
        conn = sqlite3.connect("./data/sessions.db", timeout=1)
        conn.execute("SELECT 1").fetchone()
        conn.close()
        checks["sessions_db"] = "ok"
    except Exception as e:
        checks["sessions_db"] = f"error: {type(e).__name__}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {
        "status": overall,
        "checks": checks,
        "version": __version__,
    }
```

Impor `__version__` dari `raven`.

Kriteria terima:
- `/health` dengan Chroma & DB up → `status: ok`, semua checks `ok`.
- `/health` kalau Chroma down (misal folder permissions locked) → `status: degraded`, field `chroma` contains `error: ...`.
- Response include `version`.

Pagar pembatas:
- Jangan ekspos stack trace di response.
- Timeout query harus pendek (1-2 detik) — `/health` tidak boleh lama.
```

## 9.3 — Tambah `__version__` ke `raven/__init__.py`

```
Konteks:
Untuk consistency dan health check output.

Tugas:
Edit `raven/__init__.py`, tambahkan di atas:
```python
"""Ryvn — personal AI assistant."""
from __future__ import annotations

__version__ = "0.2.0"
__all__ = ["__version__"]
```

Kalau file sudah ada content, sisipkan `__version__` di atas (setelah docstring).

Kriteria terima:
- `python -c "import raven; print(raven.__version__)"` → `0.2.0`.

Pagar pembatas:
- Jangan hapus export yang sudah ada di `__init__.py`.
```

---

# DAY 10 (29-30 Apr) — Integration + Tag v0.2.0

## 10.1 — E2E Smoke Test (Manual Checklist)

```
Konteks:
Sebelum tag release, verifikasi fresh clone → running server → semua endpoint responsif.

Tugas:
Bikin / update `docs/SPRINT1_DAY10_SMOKE_TEST.md` dengan checklist:

- [ ] Fresh clone: `git clone ... && cd Ryvn_Project`
- [ ] Copy env: `cp .env.example .env` lalu isi `API_KEY`, `OPENAI_API_KEY`, `WATCH_PATHS`
- [ ] Install: `uv sync` → tidak error
- [ ] Start: `./start.sh` → uvicorn listen di `:1802`
- [ ] `curl http://localhost:1802/health` → `status: ok`, semua check `ok`
- [ ] `curl -X POST http://localhost:1802/chat -d '{}'` (tanpa API key) → **401**
- [ ] `curl -N -H "X-API-Key: ..." -X POST http://localhost:1802/chat -d '{"message":"hi","session_id":"s1"}'` → SSE stream dengan event `token` multiple
- [ ] `curl -H "X-API-Key: ..." -X POST http://localhost:1802/index -d '{"path":"<valid_watch_path>"}'` → ter-index
- [ ] `curl -H "X-API-Key: ..." -X POST http://localhost:1802/index -d '{"path":"/etc"}'` → **403**
- [ ] Kill server (Ctrl+C), start lagi, re-hit `/chat` dengan `session_id: "s1"` → agent "ingat" context sebelumnya
- [ ] `uv run raven` → CLI REPL muncul, `/exit` clean shutdown

Jalankan manual. Tandai checklist. Commit hasil report (tanpa output yang bocorin path/key real).

Kriteria terima:
- Semua item checked.
- File `docs/SPRINT1_DAY10_SMOKE_TEST.md` ada dengan checklist + 1 paragraf kesimpulan.

Pagar pembatas:
- JANGAN run dengan production API_KEY / credentials — pakai dummy.
- Kalau ada item yang fail, STOP dan balik ke task yang relevan.
```

## 10.2 — Run Full Test Suite

```
Konteks:
Gating sebelum tag: semua test harus green.

Tugas:
```
uv run pytest --cov=raven --cov-report=html --cov-report=term-missing -v
```

Update `docs/SPRINT1_DAY7_COVERAGE.md` (atau bikin baru `SPRINT1_DAY10_COVERAGE.md`) dengan hasil final:
- Total tests, passed, failed, skipped
- Coverage per module
- Link ke `htmlcov/index.html` (local path)

Kalau ada fail → fix dulu, jangan lanjut ke 10.3.

Kriteria terima:
- 15+ test passed, 0 failed.
- Coverage `rag/` dan `api/` ≥ 40%.

Pagar pembatas:
- Jangan `-x` / `--lf` / `-k` untuk filter — jalankan full suite.
```

## 10.3 — Final Ruff + Mypy Pass

```
Konteks:
Last lint/type check sebelum tag.

Tugas:
```
uv run ruff check raven/ tests/
uv run ruff format --check raven/ tests/
uv run mypy raven/
```

Kalau ada error → fix. Kalau format diff → `uv run ruff format raven/ tests/` lalu review.

Kriteria terima:
- Ruff: "All checks passed!"
- Ruff format: "X files already formatted" (0 diff).
- Mypy: 0 error (ignore warnings boleh).

Pagar pembatas:
- Jangan `--no-cache` tanpa alasan.
- Kalau ada error yang butuh ubah behavior, STOP dan diskusi.
```

## 10.4 — Update Version ke `0.2.0`

```
Konteks:
Bump version untuk release.

Tugas:
1. Edit `pyproject.toml`: `version = "0.1.0"` → `version = "0.2.0"`.
2. Verifikasi `raven/__init__.py` sudah `__version__ = "0.2.0"` (task 9.3).
3. Hasilkan CHANGELOG entry (bikin / update `CHANGELOG.md`):
   ```markdown
   # Changelog

   ## [0.2.0] — 2026-04-30

   ### Added
   - API key authentication (`X-API-Key` header) pada endpoint sensitif
   - CORS origin whitelist via `ALLOWED_ORIGINS` env var
   - Path validation untuk `/index` (restrict ke `WATCH_PATHS`, tolak symlink)
   - Persistent session history via `langgraph-checkpoint-sqlite`
   - True per-token SSE streaming (event `token`)
   - Structured logging dengan structlog
   - Test suite (15+ test, coverage ≥40% di rag/ & api/)
   - Ruff + mypy configuration
   - README, enhanced `/health` dependency check

   ### Changed
   - `/chat` event `message` → `token` (breaking untuk client)
   - `.env.example` sanitized (removed leaked key + internal IP)
   - Narrow exception handling di indexer (no more silent `except Exception`)

   ### Fixed
   - Deprecated `asyncio.get_event_loop()` → `asyncio.get_running_loop()`
   - `/index` non-blocking via `run_in_executor`
   - File hash streaming (cegah OOM di file besar)
   - Recursion limit eksplisit di graph compile (`recursion_limit=25`)

   ### Security
   - Leaked API key removed from `.env.example` (rotate key + rewrite git history — lihat `docs/SPRINT1_DAY1_GIT_HISTORY_HANDOFF.md`)
   ```

Kriteria terima:
- `pyproject.toml` version `0.2.0`.
- `raven/__init__.py` `__version__ = "0.2.0"`.
- `CHANGELOG.md` ada dengan entri 0.2.0.

Pagar pembatas:
- Jangan bump ke `0.3.0` atau `1.0.0` — Sprint 1 target eksplisit `0.2.0`.
```

## 10.5 — Git Commit + Tag + Push (Handoff)

```
Konteks:
Finalisasi release v0.2.0. Push ke remote.

Tugas:
JANGAN eksekusi `git push --force` atau delete branch apapun. HASILKAN checklist command yang user jalankan manual di `docs/SPRINT1_DAY10_RELEASE_HANDOFF.md`:

```bash
# 1. Pastikan working tree bersih
git status

# 2. Stage + commit perubahan
git add -A
git commit -m "v0.2.0: hardening — auth, persistent sessions, true SSE, tests, README"

# 3. Tag
git tag -a v0.2.0 -m "Sprint 1 release — security hardening + foundation"

# 4. Push commits + tags
git push origin main
git push origin v0.2.0

# 5. Buat GitHub release (opsional, via web UI atau `gh`)
gh release create v0.2.0 --notes-file CHANGELOG.md
```

Plus catatan: "Kalau belum rotate API key yang bocor, STOP dan rotate dulu. Push tag = snapshot final, harus bersih."

Kriteria terima:
- File `docs/SPRINT1_DAY10_RELEASE_HANDOFF.md` ada dengan 5 langkah di atas + warning rotation.

Pagar pembatas:
- JANGAN auto-run `git push`, `git tag`, atau `gh release create`.
- JANGAN delete branch lokal atau remote.
```

---

# Ringkasan & Tracking

Total sub-task: **41** (matches SPRINT1_BREAKDOWN.md).

| Day | Sub-tasks | Prompt IDs |
|-----|-----------|------------|
| PRE | 1 | PRE-0 |
| 1 | 4 | 1.1, 1.2, 1.3, 1.4 |
| 2 | 4 | 2.1, 2.2, 2.3, 2.4 |
| 3 | 5 | 3.1, 3.2, 3.3, 3.4, 3.5 |
| 4 | 4 | 4.1, 4.2, 4.3, 4.4 |
| 5 | 6 | 5.1, 5.2, 5.3, 5.4, 5.5, 5.6 |
| 6-7 | 6 | 6.1, 6.2, 6.3, 6.4, 6.5, 6.6 |
| 8 | 4 | 8.1, 8.2, 8.3, 8.4 |
| 9 | 3 | 9.1, 9.2, 9.3 |
| 10 | 5 | 10.1, 10.2, 10.3, 10.4, 10.5 |

**Alur rekomendasi per prompt:**

1. Buka file relevan di Zed (tab editor).
2. Paste prompt ke Agent Panel.
3. Review diff preview → apply.
4. Jalankan kriteria terima (command spesifik di prompt).
5. `git add -A && git commit -m "sprint1/<day>.<num>: <desc>"`.
6. Lanjut ke prompt berikutnya.

**Kalau ada prompt yang gagal:** jangan brute-force retry — balik ke pagar pembatas, cek asumsi (misal struktur source code beda), lalu adapt prompt-nya.


---

**Safety recap (applies to ALL prompts):**
- Jangan hapus file tanpa konfirmasi user (CLAUDE.md rule).
- Jangan `git push --force`, `git filter-repo`, `rm -rf` — minta user eksekusi manual.
- Jangan commit secret asli.
- Tampilkan diff sebelum apply.
