"""Index local files into the vector store."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from raven.config import INDEXED_DIR, INDEXED_EXTENSIONS
from raven.logging_config import get_logger
from raven.rag.vectorstore import VectorStore

logger = get_logger("raven.indexer")

EXCLUDE_DIRS = {
    # VCS / Python envs / build artifacts
    ".git", ".venv", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache",
    "venv", "env", "site-packages", "dist", "build", "target", "vendor", "egg-info",
    # Toolchain / package caches & SDKs (noise, not knowledge — and can hold secrets)
    "snap", "go", "pkg", ".cache", ".local", ".cargo", ".rustup", ".gradle",
    ".m2", ".npm", ".pub-cache", ".nuget", "Cache", "Caches", ".obsidian",
}


# Filenames that typically hold secrets — never embed these into the vector store,
# even when their extension is in INDEXED_EXTENSIONS (e.g. auth.txt, credentials.json).
SECRET_NAMES = {
    "auth.txt", "credentials.txt", "credentials.json", "secrets.txt", "secrets.json",
    "password.txt", "passwords.txt", "token.txt", ".env", ".netrc", ".pgpass",
}
SECRET_SUFFIXES = (".key", ".pem", ".pfx", ".p12", ".keystore")
SECRET_STEMS = ("id_rsa", "id_ed25519", "id_dsa")


def _looks_secret(path: Path) -> bool:
    name = path.name.lower()
    return (
        name in SECRET_NAMES
        or name.endswith(SECRET_SUFFIXES)
        or path.stem.lower() in SECRET_STEMS
        or "secret" in name
        or "credential" in name
    )


def is_excluded(path: str | Path) -> bool:
    """True if the file should be skipped by indexing: any path component is hidden
    (dot-prefixed) or a known heavy/junk dir (virtualenvs, node_modules, build
    artifacts, toolchain caches, ...), or the filename looks like a secret. Single
    source of truth for what indexing skips, shared by the API, the directory
    indexer, and the watcher."""
    p = Path(path)
    if _looks_secret(p):
        return True
    return any(part.startswith(".") or part in EXCLUDE_DIRS for part in p.parts)


def _read_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        import pypdf

        reader = pypdf.PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext == ".docx":
        import docx2txt

        return docx2txt.process(str(path))  # type: ignore[no-any-return]
    else:
        return path.read_text(errors="ignore")


def _chunk(text: str, size: int = 512, overlap: int = 64) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + size])
        if chunk:
            chunks.append(chunk)
        i += size - overlap
    return chunks


def _file_hash(path: Path, chunk_size: int = 1 << 20) -> str:
    """SHA-256 hash, streamed chunk-by-chunk to avoid OOM on large files."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while blob := f.read(chunk_size):
            h.update(blob)
    return h.hexdigest()[:16]


class FileIndexer:
    def __init__(self, store: VectorStore | None = None):
        self.store = store or VectorStore()
        INDEXED_DIR.mkdir(parents=True, exist_ok=True)
        self._state_file = INDEXED_DIR / "index_state.json"
        self._state: dict = self._load_state()

    def _load_state(self) -> dict:
        if self._state_file.exists():
            return json.loads(self._state_file.read_text())  # type: ignore[no-any-return]
        return {}

    def _save_state(self) -> None:
        self._state_file.write_text(json.dumps(self._state, indent=2))

    def index_file(self, path: Path) -> int:
        """Index a single file. Returns number of chunks added."""
        path = Path(path).resolve()
        if path.suffix.lower() not in INDEXED_EXTENSIONS:
            return 0
        if not path.is_file():
            return 0
        if _looks_secret(path):
            logger.warning("index_file_skipped_secret", path=str(path))
            return 0

        file_hash = _file_hash(path)
        key = str(path)

        if self._state.get(key) == file_hash:
            return 0  # unchanged

        # remove old chunks
        self.store.delete_by_source(key)

        try:
            text = _read_text(path)
        except (UnicodeDecodeError, OSError, ValueError, KeyError) as e:
            logger.warning(
                "index_file_failed", path=str(path), error=str(e), error_type=type(e).__name__
            )
            return 0

        chunks = _chunk(text)
        docs = [
            {
                "id": f"{file_hash}-{i}",
                "text": chunk,
                "metadata": {
                    "source": key,
                    "filename": path.name,
                    "ext": path.suffix,
                    "chunk": i,
                    "indexed_at": int(time.time()),
                },
            }
            for i, chunk in enumerate(chunks)
        ]
        self.store.add(docs)
        self._state[key] = file_hash
        self._save_state()
        return len(docs)

    def index_directory(self, directory: str | Path, recursive: bool = True) -> int:
        directory = Path(directory)
        total = 0
        pattern = "**/*" if recursive else "*"
        for path in directory.glob(pattern):
            if not path.is_file() or path.suffix.lower() not in INDEXED_EXTENSIONS:
                continue
            if is_excluded(path):
                continue
            total += self.index_file(path)
        return total

    def remove_file(self, path: str | Path) -> None:
        key = str(Path(path).resolve())
        self.store.delete_by_source(key)
        self._state.pop(key, None)
        self._save_state()
