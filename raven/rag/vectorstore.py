"""Local ChromaDB vector store with API-based embeddings (bge-m3)."""
from __future__ import annotations

from pathlib import Path
from typing import List

import chromadb
from chromadb.config import Settings
from openai import OpenAI

from raven.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION, EMBEDDING_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL


EMBED_BATCH_SIZE = 32
EMBED_MAX_RETRIES = 5
EMBED_RETRY_DELAY = 3  # seconds


class APIEmbedder:
    def __init__(self):
        self._client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
        )

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        import time
        for attempt in range(EMBED_MAX_RETRIES):
            try:
                response = self._client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                if "429" in str(e) or "overload" in str(e).lower():
                    wait = EMBED_RETRY_DELAY * (2 ** attempt)
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError(f"Embedding failed after {EMBED_MAX_RETRIES} retries")

    def embed(self, texts: list[str]) -> list[list[float]]:
        import time
        results = []
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i: i + EMBED_BATCH_SIZE]
            results.extend(self._embed_batch(batch))
            if i + EMBED_BATCH_SIZE < len(texts):
                time.sleep(0.5)
        return results


class VectorStore:
    def __init__(self):
        Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        self._embedder = APIEmbedder()
        self._collection = self._client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, docs: List[dict]) -> None:
        if not docs:
            return
        ids = [d["id"] for d in docs]
        texts = [d["text"] for d in docs]
        metas = [d.get("metadata", {}) for d in docs]
        embeddings = self._embedder.embed(texts)
        self._collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metas,
        )

    def query(self, text: str, n_results: int = 5) -> List[dict]:
        embedding = self._embedder.embed([text])[0]
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        out = []
        for i, doc in enumerate(results["documents"][0]):
            out.append({
                "text": doc,
                "metadata": results["metadatas"][0][i],
                "score": 1 - results["distances"][0][i],
            })
        return out

    def delete_by_source(self, source: str) -> None:
        results = self._collection.get(where={"source": source})
        if results["ids"]:
            self._collection.delete(ids=results["ids"])

    def count(self) -> int:
        return self._collection.count()


_instance: VectorStore | None = None

def get_store() -> VectorStore:
    global _instance
    if _instance is None:
        _instance = VectorStore()
    return _instance
