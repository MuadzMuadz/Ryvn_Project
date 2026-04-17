"""Index local files into the vector store."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import List

from raven.config import INDEXED_EXTENSIONS, INDEXED_DIR
from raven.rag.vectorstore import VectorStore


def _read_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        import pypdf
        reader = pypdf.PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext == ".docx":
        import docx2txt
        return docx2txt.process(str(path))
    else:
        return path.read_text(errors="ignore")


def _chunk(text: str, size: int = 512, overlap: int = 64) -> List[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i: i + size])
        if chunk:
            chunks.append(chunk)
        i += size - overlap
    return chunks


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


class FileIndexer:
    def __init__(self, store: VectorStore | None = None):
        self.store = store or VectorStore()
        INDEXED_DIR.mkdir(parents=True, exist_ok=True)
        self._state_file = INDEXED_DIR / "index_state.json"
        self._state: dict = self._load_state()

    def _load_state(self) -> dict:
        if self._state_file.exists():
            return json.loads(self._state_file.read_text())
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

        file_hash = _file_hash(path)
        key = str(path)

        if self._state.get(key) == file_hash:
            return 0  # unchanged

        # remove old chunks
        self.store.delete_by_source(key)

        try:
            text = _read_text(path)
        except Exception:
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
            if path.is_file() and path.suffix.lower() in INDEXED_EXTENSIONS:
                total += self.index_file(path)
        return total

    def remove_file(self, path: str | Path) -> None:
        key = str(Path(path).resolve())
        self.store.delete_by_source(key)
        self._state.pop(key, None)
        self._save_state()
