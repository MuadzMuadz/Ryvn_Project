"""Local ChromaDB vector store with API-based embeddings."""

from __future__ import annotations

import time
from pathlib import Path

import chromadb
from chromadb.config import Settings
from openai import OpenAI

from raven.config import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    EMBEDDING_MODEL,
)
from raven.logging_config import get_logger

logger = get_logger("raven.vectorstore")

EMBED_BATCH_SIZE = 32
EMBED_MAX_RETRIES = 5
EMBED_RETRY_DELAY = 3


class APIEmbedder:
    def __init__(self):
        self._client = OpenAI(api_key=EMBEDDING_API_KEY, base_url=EMBEDDING_BASE_URL)

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        for attempt in range(EMBED_MAX_RETRIES):
            try:
                response = self._client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                msg = str(e)
                if "429" in msg or "overload" in msg.lower():
                    wait = EMBED_RETRY_DELAY * (2**attempt)
                    logger.warning(
                        "embed_rate_limited",
                        attempt=attempt + 1,
                        max_retries=EMBED_MAX_RETRIES,
                        wait_s=wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error("embed_failed", error=str(e))
                    raise
        raise RuntimeError(f"Embedding failed after {EMBED_MAX_RETRIES} retries")

    def embed(self, texts: list[str]) -> list[list[float]]:
        results = []
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i : i + EMBED_BATCH_SIZE]
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

    def add(self, docs: list[dict]) -> None:
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

    def query(self, text: str, n_results: int = 5) -> list[dict]:
        embedding = self._embedder.embed([text])[0]
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        out = []
        for i, doc in enumerate(results["documents"][0]):
            out.append(
                {
                    "text": doc,
                    "metadata": results["metadatas"][0][i],
                    "score": 1 - results["distances"][0][i],
                }
            )
        return out

    def delete_by_source(self, source: str) -> None:
        results = self._collection.get(where={"source": source})
        if results["ids"]:
            self._collection.delete(ids=results["ids"])

    def count(self) -> int:
        return self._collection.count()  # type: ignore[no-any-return]


_instance: VectorStore | None = None


def get_store() -> VectorStore:
    global _instance
    if _instance is None:
        _instance = VectorStore()
    return _instance
