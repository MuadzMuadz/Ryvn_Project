# Sprint 1 — Audit Day 1-3 (Commit `02cf8a9`)

**Tanggal audit:** 17 April 2026
**Basis:** `SPRINT1_BREAKDOWN.md` Day 1-3 + codebase di `Raven/` HEAD = `02cf8a9`
**Commit yang diaudit:** `02cf8a9` — "refactor: harden API with auth, persistent sessions, path validation, and improved RAG pipeline"

---

## Ringkasan Skor

| Day | Sub-task | Status | Catatan |
|-----|----------|--------|---------|
| 1.1 | Clean `.env.example` | ✅ DONE | Missing `LOG_LEVEL` field |
| 1.2 | Update `.gitignore` | ❌ PARTIAL | Missing `data/`, `*.db`, `index_state.json` — PLUS `data/sessions.db*` sudah ter-track di git (leak!) |
| 1.3 | Git history rewrite | ❌ NOT DONE | Key `sk-ZvPat…` + IP `***REMOVED***` masih ada di commit `b91f06f` |
| 1.4 | Auth fields di `config.py` | ⚠️ MOSTLY | `API_KEY` + `ALLOWED_ORIGINS` OK, `LOG_LEVEL` missing |
| 2.1 | API key middleware | ✅ DONE | Deviasi: `/stats` ikut di-auth (spec: public) |
| 2.2 | CORS lockdown | ✅ DONE | Perfect match |
| 2.3 | Path validation | ⚠️ PARTIAL | Missing symlink check (`p.is_symlink()`) |
| 2.4 | Recursion limit 25 | ❌ NOT DONE | `.compile(checkpointer=saver)` — no `recursion_limit=` |
| 3.1 | Dep `langgraph-checkpoint-sqlite` | ✅ DONE | `>=3.0.3` (lebih baru dari spec `>=2.0.0`) |
| 3.2 | Integrate SqliteSaver | ✅ DONE (BETTER) | Pakai `AsyncSqliteSaver` + `aiosqlite` — async native |
| 3.3 | Remove `_sessions` dict | ✅ DONE | Pakai `config={"configurable": {"thread_id": ...}}` |
| 3.4 | `/stats` pakai SQL count | ❌ DEVIATION | Return `{chunks, allowed_roots}` — no `session_count` |
| 3.5 | Auto-create `data/` | ⚠️ PARTIAL | Ada di saver init, tapi `data/vectors/` gak eksplisit di-create; no startup hook |

**Tally:** ✅ 6 • ⚠️ 4 • ❌ 3 dari total 13 sub-task.

---

## Detail Per Sub-Task

### ✅ 1.1 — `.env.example` cleanup

Leaked key `sk-ZvPat…` sudah diganti placeholder `sk-your-key-here`. IP private `***REMOVED***` sudah generic `localhost`. `WATCH_PATHS` sudah placeholder.

**Deviasi:**
- Field `LOG_LEVEL=INFO` gak ada di `.env.example`.
- `WATCH_PATHS` hanya 1 path (`/path/to/your/documents`) — spec kasih 2 path contoh (docs + downloads).
- Field BONUS ada: `PORT=1802`.

**Action:** Tambah `LOG_LEVEL=INFO` ke `.env.example` saat lu ke Day 5 (atau sekarang kalau mau sekaligus).

---

### ❌ 1.2 — `.gitignore` update

**Current `.gitignore`:**
```
.env
.venv/
__pycache__/
*.pyc
data/vectors/
data/indexed/
data/uploads/
*.egg-info/
dist/
.DS_Store
```

**Missing per spec:**
- `data/` (generic — akan cover `sessions.db`, `*.db-shm`, `*.db-wal` sekaligus)
- `*.db`
- `index_state.json`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `htmlcov/`, `.coverage` (untuk Day 6-8 nanti)

**Critical consequence:**
File `data/sessions.db`, `data/sessions.db-shm`, `data/sessions.db-wal` **sudah di-track git** (confirmed via `git ls-files data/`). Session conversation history sekarang ada di repo. Ini leak (potensi PII + isi chat).

**Action urgent:**
```bash
cd Raven
# 1. Update .gitignore dengan entri di atas
# 2. Un-track file yang sudah masuk
git rm --cached data/sessions.db data/sessions.db-shm data/sessions.db-wal
git commit -m "fix: untrack sqlite session data from repo"
```

---

### ❌ 1.3 — Git history rewrite

**Bukti leak masih hidup di history:**
```
$ git log --all -p -- .env.example | grep "sk-ZvPat\|10.83.81"
-OPENAI_API_KEY=***REMOVED***
-OPENAI_BASE_URL=http://***REMOVED***:4000/v1
+OPENAI_API_KEY=***REMOVED***
+OPENAI_BASE_URL=http://***REMOVED***:4000/v1
```

Commit `02cf8a9` hanya scrub di working tree — commit sebelumnya (`b91f06f` "initial commit") masih memuat key + IP.

**Action (lihat prompt pack 1.3 — handoff):**
1. **Rotate key di provider DULU** (LiteLLM / OpenAI). Anggap key ini compromised.
2. Backup bare clone.
3. `git filter-repo --path .env.example --invert-paths --force`
4. Commit ulang `.env.example` bersih.
5. `git push --force origin main`.
6. Notify siapa saja yang punya clone — mereka perlu re-clone.

---

### ⚠️ 1.4 — Config.py auth fields

**Current:**
```python
API_KEY = os.getenv("API_KEY", "").strip()
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
# ... missing:
# LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

**Catatan bagus (deviation positif):** `.strip()` di API_KEY = defensive bagus.

**Action:** Tambah `LOG_LEVEL` field. Bisa skip sekarang kalau mau gabung sama Day 5 (yang mulai pake structlog).

---

### ✅ 2.1 — API key middleware

`require_api_key` proper:
```python
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not API_KEY:
        return  # auth disabled in dev
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
```

Applied ke: `/chat`, `/index`, `/index/init`, `/stats`, `DELETE /session/{id}`. `/health` public.

**Deviasi:** Spec bilang `/stats` harus **public**. Current: butuh auth. Keputusan:
- Option A: Hapus `dependencies=[Depends(require_api_key)]` dari `/stats` (match spec).
- Option B: Biarkan auth (lebih aman, ada info tentang allowed_roots yang mungkin gak mau di-ekspos).

Gua rekomendasi Option B — lebih aman. Kalau lu setuju, update spec di SPRINT1_BREAKDOWN.md biar gak ada drift.

---

### ✅ 2.2 — CORS lockdown

Perfect match dengan spec:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

No action.

---

### ⚠️ 2.3 — Path validation

**Current:**
```python
def _validate_path(raw: str) -> Path:
    p = Path(raw).expanduser().resolve()
    if not any(str(p) == str(root) or str(p).startswith(str(root) + "/") for root in _ALLOWED_ROOTS):
        raise HTTPException(403, f"Path outside allowed roots (WATCH_PATHS): {p}")
    if not p.exists():
        raise HTTPException(404, f"Path not found: {p}")
    return p
```

**Bagus:**
- `expanduser()` + `resolve()` — normalize path.
- `startswith(root + "/")` cegah false match (misal `/home/a` matching `/home/abc`).
- Order check: allowed_roots SEBELUM exists (bocorin keberadaan file di luar allowed = leak info juga).

**Gap:** Missing symlink check. Kalau ada symlink `<watch_path>/link → /etc/passwd`, `.resolve()` akan follow symlink sampe target dan mungkin lolos check (kalau target masih di dalam WATCH_PATHS) atau stuck. Tapi kalau target di luar, baru ketahan.

**Bonus catch spec gak punya:** `_validate_path` gak dipanggil di `/index/init` — iterate `WATCH_PATHS` langsung. Secara logika OK (WATCH_PATHS = source of truth), tapi kalau admin salah config path ke root OS, `/index/init` bakal crawl semua. Low risk, tapi worth noting.

**Action:** Tambah `if p.is_symlink(): raise HTTPException(403, "Symlinks not allowed")` sebelum check roots.

---

### ❌ 2.4 — Recursion limit

**Current `raven/graph/agent.py`:**
```python
return g.compile(checkpointer=saver)
```

**Spec:**
```python
return g.compile(checkpointer=saver, recursion_limit=25)
```

Default LangGraph recursion_limit = 25, jadi secara behavior sekarang OK, tapi eksplisit di code = dokumentasi + future-proof.

**Action:** One-liner fix.

---

### ✅ 3.1 — Dep langgraph-checkpoint-sqlite

`pyproject.toml`:
```
"langgraph-checkpoint-sqlite>=3.0.3",
```

Spec-nya `>=2.0.0`, current `>=3.0.3` — lebih baru, OK.

**Bonus dep juga:** `langchain-text-splitters>=0.3` ditambah (bagus).
**Removed deps:** `rich` dan `sentence-transformers` dihapus — kalau `bge-m3` via `langchain-community`, OK. Kalau ada error saat import, perlu cek.

---

### ✅ 3.2 — SqliteSaver integration (BETTER than spec)

Spec pakai `SqliteSaver` (sync) + `sqlite3.connect`. Current pakai `AsyncSqliteSaver` + `aiosqlite` — async native, match FastAPI event loop natively, no thread-safety juggling.

```python
async def _get_saver() -> AsyncSqliteSaver:
    global _saver, _conn
    if _saver is None:
        SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
        _conn = await aiosqlite.connect(str(SESSIONS_DB))
        _saver = AsyncSqliteSaver(_conn)
        await _saver.setup()
    return _saver
```

No action.

---

### ✅ 3.3 — Remove `_sessions` dict

Scan `raven/api/app.py` → no `_sessions: dict`. Chat handler pakai `config = {"configurable": {"thread_id": session_id}}`. Delete session delegated ke `saver.adelete_thread(thread_id)` via `delete_thread()` helper — clean.

No action.

---

### ❌ 3.4 — `/stats` endpoint

**Spec:**
```json
{"session_count": N, "document_count": M, ...}
```

**Current:**
```python
@app.get("/stats", dependencies=[Depends(require_api_key)])
async def stats():
    store = get_store()
    return {"chunks": store.count(), "allowed_roots": [str(r) for r in _ALLOWED_ROOTS]}
```

`chunks` = document_count (oke, beda naming). `session_count` gak ada.

**Action:** Tambah session count via SQL:
```python
import aiosqlite

async def _count_sessions() -> int:
    try:
        async with aiosqlite.connect(str(SESSIONS_DB)) as conn:
            cur = await conn.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints")
            row = await cur.fetchone()
            return int(row[0]) if row else 0
    except Exception:
        return 0
```

---

### ⚠️ 3.5 — Auto-create `data/`

Present di `_get_saver()`:
```python
SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
```

Bikin `./data/` saat saver pertama di-init (lazy — pas first request masuk). OK untuk session DB.

**Gap:**
- `./data/vectors/` gak eksplisit di-create. Chroma biasanya auto-create, tapi tergantung version.
- Gak ada startup hook (FastAPI `lifespan`) — lazy approach kalau boleh, startup approach kalau mau explicit guarantee.

**Action (opsional):** Tambah lifespan:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from raven.config import DATA_DIR, CHROMA_PERSIST_DIR
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(title="Raven API", version="0.1.0", lifespan=lifespan)
```

---

## BONUS — Feature Beyond Day 1-3 Spec

Developer udah melompat sebagian Day 5 + Day 9 sambil kerjain Day 1-3:

1. **Embedding upgrade: `all-MiniLM-L6-v2` → `bge-m3`**
   Multi-lingual, lebih akurat. Good call. Tapi model-nya gede (~2GB), first run bakal download.

2. **Document sanitization + `<document>` wrapping**
   Defense-in-depth against prompt injection dari indexed content. Ini ngelompat ke Sprint 2 scope (security hardening).

3. **`MAX_CONVERSATION_TOKENS` trimming**
   Cegah OOM di long session. Ini juga Sprint 2 scope.

4. **`/health` enhanced dengan chroma + graph checks**
   Ini Day 9.2 spec. Sudah 70% done:
   ```python
   checks = {"api": "ok", "chroma": ..., "graph": ...}
   ```
   Yang belum: `sessions_db` check + `version` field. Bisa jadi Day 9.2 tinggal finishing touch.

5. **`/index/init` sudah pakai `run_in_executor`**
   Day 4.3 spec — sudah pre-done di commit ini. TAPI masih pakai `asyncio.get_event_loop()` (deprecated) di `/index` dan `/index/init`. Day 4.3 tetep perlu 1-liner fix.

6. **Bruno collection updated**
   Sudah dengan `X-API-Key` header di semua request.

---

## Issue Tambahan (di luar spec)

### 🔧 Dirty working tree — semua file permission 100644 → 100755

```
$ git diff HEAD -- raven/config.py
old mode 100644
new mode 100755
```

33 file ter-flip ke executable mode (likely dari shell di Windows / WSL mount). Zero content change. Ganggu `git status`.

**Fix:**
```bash
cd Raven
git config core.fileMode false       # ignore mode changes di repo ini
git checkout -- .                    # atau: git update-index --chmod=-x <files>
```

Atau revert dengan:
```bash
find . -type f -not -path './.git/*' -not -path './.venv/*' -exec chmod 644 {} +
find . -type f -name '*.sh' -exec chmod 755 {} +
```

### 🔧 `data/sessions.db*` tracked (sudah disebut di 1.2)

```
$ git ls-files data/
data/sessions.db
data/sessions.db-shm
data/sessions.db-wal
```

**Fix (setelah `.gitignore` update):**
```bash
git rm --cached data/sessions.db data/sessions.db-shm data/sessions.db-wal
```

---

## Rencana Fix-Up (Urutan Rekomendasi)

Sebelum lanjut ke Day 4, ada **7 item cleanup** biar Day 1-3 benar-benar done:

| # | Task | Prioritas | Effort |
|---|------|-----------|--------|
| 1 | Rotate leaked API key di LiteLLM/OpenAI | 🔴 CRITICAL | 2 menit |
| 2 | `.gitignore` + untrack `data/sessions.db*` | 🔴 HIGH | 5 menit |
| 3 | Fix file mode 100755 → 100644 + set `core.fileMode false` | 🟡 MED | 5 menit |
| 4 | Tambah `LOG_LEVEL` ke `config.py` + `.env.example` | 🟢 LOW | 2 menit |
| 5 | Tambah symlink check di `_validate_path` | 🟢 LOW | 2 menit |
| 6 | `recursion_limit=25` di `agent.py` | 🟢 LOW | 1 menit |
| 7 | `/stats` tambah `session_count` | 🟢 LOW | 10 menit |
| 8 | Git history rewrite (handoff — eksekusi manual) | 🔴 HIGH | 15 menit |

**Decision point:**
- `/stats` auth-required vs public (spec conflict)
- Mau Chroma `data/vectors/` auto-create eksplisit atau biar lazy?

---

## Kesimpulan

Commit `02cf8a9` kerjain ±**70% Day 1-3** + **bonus scope** dari Day 4, 5, 9.

**Day 1-3 belum tutup** karena:
- `.gitignore` bocor (sessions.db tracked)
- History masih ada leaked key
- Recursion limit missing
- `/stats` schema beda dengan spec
- LOG_LEVEL belum di-plumb

**Rekomendasi next:**
- **Option A:** Gua bikin **patch prompt pack** (7 prompt kecil untuk fix item 2-7 di atas + handoff buat 1 & 8) → lu ke Zed, 25 menit kelar, Day 1-3 resmi tutup.
- **Option B:** Accept bonus scope, skip ke Day 4 langsung — tanggung konsekuensi gap (sessions.db terus leak ke repo, history belum aman).
- **Option C:** Gua langsung eksekusi item 2-7 dari sini (file access ke `Raven/` gua ada) sambil lu rotate key + jalanin history rewrite terpisah.

Yang mana?
