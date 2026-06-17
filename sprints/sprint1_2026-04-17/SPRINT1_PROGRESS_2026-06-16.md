# Sprint 1 — Progress Audit (Working Tree, 16 Juni 2026)

**Tanggal audit:** 16 Juni 2026
**Basis:** `SPRINT1_BREAKDOWN.md` Day 1-10 vs **working tree** (uncommitted changes di atas `02cf8a9`)
**Catatan:** Update dari `SPRINT1_DAY1-3_AUDIT.md` (yang hanya cover Day 1-3 di commit `02cf8a9`). Banyak kerjaan Day 4-9 sudah masuk tapi **belum di-commit**.

---

## Ringkasan Skor (semua 10 hari)

| Day | Sub-task | Status | Catatan |
|-----|----------|--------|---------|
| 1.1 | Clean `.env.example` | ✅ DONE | `LOG_LEVEL`, `PORT`, `ALLOWED_ORIGINS` sudah ada — gap audit lama tutup |
| 1.2 | `.gitignore` + untrack db | ✅ DONE | `data/`, `*.db`, `index_state.json`, tooling caches ada. `data/sessions.db*` **tidak lagi tracked** |
| 1.3 | Git history rewrite | ❌ NOT DONE | Key `sk-ZvPat…` + IP `***REMOVED***` **masih ada** di history commit `b91f06f` (4 hit) |
| 1.4 | Auth + LOG_LEVEL di config | ✅ DONE | `API_KEY`, `ALLOWED_ORIGINS`, `LOG_LEVEL` lengkap |
| 2.1 | API key middleware | ✅ DONE | Applied ke `/chat`, `/index`, `/index/init`, `/stats`, `/sessions`, history, DELETE. `/` + `/health` public |
| 2.2 | CORS lockdown | ✅ DONE | Perfect match |
| 2.3 | Path validation | ✅ DONE | **Symlink check sudah ada** (`p.is_symlink()`) — gap audit lama tutup |
| 2.4 | Recursion limit 25 | ✅ DONE (BETTER) | Di-set invoke-time: `config={"recursion_limit": 25}` di `_chat_stream` — ini API LangGraph yang benar (spec `compile(recursion_limit=)` salah) |
| 3.1 | Dep checkpoint-sqlite | ✅ DONE | `>=3.0.3` |
| 3.2 | SqliteSaver integration | ✅ DONE (BETTER) | `AsyncSqliteSaver` + `aiosqlite` |
| 3.3 | Remove `_sessions` dict | ✅ DONE | `thread_id` config |
| 3.4 | `/stats` session count | ✅ DONE | `_count_sessions()` SQL `COUNT(DISTINCT thread_id)` — gap audit lama tutup |
| 3.5 | Auto-create `data/` | ✅ DONE | `lifespan` + `mkdir` di saver init |
| 4.1 | True per-token streaming | ✅ DONE | `on_chat_model_stream` → event `token` |
| 4.2 | SSE event schema | ✅ DONE | `retrieval`, `token`, `tool_start`, `tool_end`, `done` |
| 4.3 | `get_running_loop()` | ✅ DONE | Tidak ada `get_event_loop()` deprecated |
| 4.4 | `/index` run_in_executor | ✅ DONE | Non-blocking |
| 5.1 | structlog dep | ✅ DONE | `structlog>=24` |
| 5.2 | `logging_config.py` | ✅ DONE | Console (dev) / JSON (`RAVEN_ENV=production`) |
| 5.3 | Replace print/logging | ✅ DONE | app, indexer, nodes, tools, watcher pakai structlog |
| 5.4 | Narrow exceptions | ✅ DONE | `(UnicodeDecodeError, OSError, ValueError, KeyError)` di indexer |
| 5.5 | Streaming file hash | ✅ DONE | `_file_hash` chunked 1 MB |
| 5.6 | Graph iteration counter | ❌ NOT DONE | `nodes.py` log `trim_messages_failed` + `tool_failed`, **tidak ada** counter `agent_iteration` |
| 6-7.1 | Test deps | ✅ DONE | pytest, asyncio, cov, httpx, ruff, mypy |
| 6-7.2 | Test structure | ⚠️ PARTIAL | Ada: conftest, test_config, test_indexer, test_api, test_graph. **Missing: `test_vectorstore.py`, `test_watcher.py`** |
| 6-7.4 | 15+ tests | ⚠️ PARTIAL | **16 tests collected**, tapi **3 FAILED** (lihat di bawah) |
| 6-7.5 | pytest config | ✅ DONE | `asyncio_mode=auto`, `testpaths`, `--strict-markers` |
| 6-7.6 | Run + coverage ≥40% | ❌ BLOCKED | 3 test merah, coverage belum diukur |
| 8.1 | ruff + mypy config | ✅ DONE | ruff rules `+RUF`, mypy gradual |
| 8.2 | ruff fix | ✅ DONE | `ruff check raven/ tests/` → **All checks passed** |
| 8.3 | mypy critical | ⚠️ PARTIAL | `raven/` core clean. **2 error di `raven/desktop/_server.py`** (kode bonus, bukan scope sprint) |
| 8.4 | pre-commit hook | ❌ NOT DONE | Tidak ada `.pre-commit-config.yaml` (opsional) |
| 9.1 | README.md | ❌ NOT DONE | **Tidak ada `README.md`** di repo |
| 9.2 | Health check enhanced | ⚠️ PARTIAL | `api`+`chroma`+`graph` checks ada. **Missing: `version` field + `sessions_db` check** |
| 9.3 | `__version__` | ❌ NOT DONE | `raven/__init__.py` kosong; `pyproject` masih `0.1.0` |
| 10 | Integration + tag v0.2.0 | ❌ NOT DONE | Belum di-commit, belum di-tag, version `0.1.0` |

**Tally:** ✅ 22 • ⚠️ 4 • ❌ 7 dari ~33 sub-task.
**Estimasi sprint:** ~**80%** done. Day 1-5 hampir tuntas; Day 6-10 yang menggantung.

---

## 🔴 Blocker / Bug Aktif

### 1. 3 test indexer FAILED — test isolation bug (BUG NYATA, bukan env)

```
FAILED tests/test_indexer.py::test_indexer_txt_file       - assert 0 > 0
FAILED tests/test_indexer.py::test_indexer_skip_unchanged - assert 0 > 0
FAILED tests/test_indexer.py::test_indexer_directory      - assert 0 >= 2
```

**Akar masalah:** `FileIndexer` simpan state hash di **`data/indexed/index_state.json`** (production path, dari `INDEXED_DIR = BASE_DIR/data/indexed`). Fixture `_isolated_indexer` cuma isolasi `CHROMA_PERSIST_DIR` + `WATCH_PATHS`, **tidak isolasi `INDEXED_DIR`**. Pytest pakai ulang nama tmp dir antar run (`pytest-1`, `pytest-2`, …), jadi file fixture punya konten + path identik → hash-nya match entry lama → `index_file` return `0` ("unchanged") → assert gagal.

Bukti: `data/indexed/index_state.json` sudah berisi key `.../pytest-of-maxzcv/pytest-1/test_indexer_*/watch/sample.txt`.

Test **lulus di run pertama, merah di run berikutnya** — flaky. Bonus: indexer production juga nge-"polusi" repo dgn nge-index file user lain (`kasir-in`, `agricloud`, dst.).

**Fix (pilih satu):**
- Isolasi `INDEXED_DIR` di fixture: monkeypatch `raven.rag.indexer.INDEXED_DIR` (dan `FileIndexer._state_file`) ke `tmp_path`, ATAU
- Hapus `data/indexed/index_state.json` sebelum tiap run (rapuh), ATAU
- Buat `_state_file` configurable lewat `FileIndexer(__init__)` arg dan kasih `tmp_path` di test.

### 2. Leaked key masih hidup di git history (Day 1.3)
`git log --all -p -- .env.example | grep sk-ZvPat` → 4 hit. Commit `b91f06f` masih bawa key + IP private. **Rotate key dulu**, lalu `git filter-repo --path .env.example --invert-paths --force` + force push. Manual handoff.

---

## ✅ Yang sudah beres sejak audit Day 1-3

Semua "action item" dari `SPRINT1_DAY1-3_AUDIT.md` sudah dikerjakan kecuali history rewrite:
- `.gitignore` lengkap + `data/sessions.db*` un-tracked ✅
- `LOG_LEVEL` di `config.py` + `.env.example` ✅
- Symlink check di `_validate_path` ✅
- `recursion_limit=25` (cara yang benar, invoke-time) ✅
- `/stats` punya `session_count` ✅
- Day 4 streaming + run_in_executor tuntas ✅
- Day 5 logging tuntas (kecuali iteration counter) ✅

---

## 🎁 Bonus scope (di luar Sprint 1 — kemungkinan Sprint 2+)

Sudah dikerjakan tapi bukan bagian breakdown Sprint 1:
- **Web UI** — `raven/api/static/` + endpoint `GET /` (single-file chat UI ala Jarvis)
- **Session browser** — endpoint `/sessions` + `/session/{id}/history`
- **Desktop shells** — `raven/desktop/` (pywebview + PySide6/Qt), `scripts/raven-desktop.sh`, `build-exe.ps1`, `windows-service.ps1`
- **Daemon / auto-index** — `lifespan` watcher + `INDEX_ON_STARTUP`, `scripts/index_linux.sh` (timer 30 menit)
- **RAG hardening** — `bge-m3`, sanitisasi `<document>`, `MAX_CONVERSATION_TOKENS` trimming, `RAG_CONTEXT_CHAR_BUDGET`

⚠️ Kode desktop ini yang bikin mypy error (2). Bukan blocker sprint, tapi kalau mau `mypy raven/` bersih, perlu fix `_server.py` atau exclude `raven/desktop/` dari mypy.

---

## 🎯 Sisa kerjaan biar Sprint 1 tutup (v0.2.0)

| # | Task | Prioritas | Effort |
|---|------|-----------|--------|
| 1 | Rotate leaked key + git history rewrite (handoff) | 🔴 CRITICAL | 15 mnt |
| 2 | Fix test isolation (`INDEXED_DIR`) → 16/16 hijau | 🔴 HIGH | 15 mnt |
| 3 | Tambah `test_vectorstore.py` + `test_watcher.py` | 🟡 MED | 30 mnt |
| 4 | Tulis `README.md` | 🟡 MED | 45 mnt |
| 5 | `__version__ = "0.2.0"` + bump `pyproject` | 🟢 LOW | 2 mnt |
| 6 | `/health` tambah `version` + `sessions_db` check | 🟢 LOW | 10 mnt |
| 7 | (opsional) iteration counter di `nodes.py` | 🟢 LOW | 5 mnt |
| 8 | Ukur coverage (`pytest --cov`) ≥40% | 🟢 LOW | 5 mnt |
| 9 | Commit semua + tag `v0.2.0` | 🟢 LOW | 5 mnt |

---

## Kesimpulan

Working tree sudah **~80% Sprint 1** + bonus scope yang lumayan jauh (UI, desktop, daemon). **Day 1-5 praktis selesai.** Yang nahan kelarnya sprint: **3 test merah (bug isolation nyata)**, **README belum ada**, **versi belum di-bump/tag**, dan **history rewrite** (security). Estimasi ~1.5-2 jam buat tutup ke v0.2.0.

---

## Update sesi 16 Jun 2026 (sore) — verifikasi live + fitur baru

Di luar scope sprint formal, sesi ini menambah/memverifikasi:

### ✅ UI terverifikasi end-to-end (live, LM Studio)
`GET /` 200, `/health` ok (api+chroma+graph). Chat streaming beneran: `retrieval → token×N → done`; jawaban benar; embeddings live 200; restore history & `/sessions` & `/stats` jalan. Concern "streaming belum diuji" → **tutup**. (UI masih CDN-dependent → belum offline-ready; belum di-commit.)

### ✅ Indexing — vault & kebersihan
- 17 entry sampah (`/tmp/pytest-*`, `raven-dbg`) dibersihkan dari `index_state.json`.
- **4 vault Obsidian** ke-index: Raven-Vault (15 chunk), AgriCloud-Vault (247), KAM SD (25), data thinkpad/Airis (1).
- Total index **~17.550 chunk** dari ~2.67K file.

### ✅ Hardening exclude indexer (`raven/rag/indexer.py`)
- `EXCLUDE_DIRS` + toolchain/cache: `snap`, `go`, `pkg`, `.cache`, `.cargo`, `.gradle`, `.m2`, `.npm`, `.obsidian`, dst.
- Guard **file rahasia** (`_looks_secret`): `auth.txt`, `*.pem`, `*.key`, `id_rsa`, `*secret*`, `*credential*`, `.env`, `.netrc` → diblok di `is_excluded` + `index_file`. Mencegah `~/vpn/auth.txt` (password VPN plaintext) ke-embed. Setelah hardening, **0 file berguna tersisa** belum ke-index.

### ✅ Fitur baru: agent bisa mencatat sendiri (`save_note`)
- Tool `save_note(title, content, tags, folder)` di `tools.py` → tulis markdown (frontmatter ala vault) ke `NOTES_DIR`, auto-index → searchable.
- `NOTES_DIR` baru di `config.py`/`.env`/`.env.example`, default `data/notes`, di-`.env` diarahkan ke `Raven-Vault/Notes`.
- System prompt (`nodes.py`) diajari kapan mencatat.
- **Terbukti**: dipanggil langsung ✅, lewat agent ✅ (model auto-call, file muncul di vault), search-back ✅. Artefak tes sudah dibersihkan.

**Catatan:** `ruff` clean di semua file. **Belum ada yang di-commit** — sekarang ada ~11 file modified + `bruno/`, `tests/`, `raven/desktop/`, `raven/api/static/`, `logging_config.py`, `scripts/`, `sprints/` untracked.
