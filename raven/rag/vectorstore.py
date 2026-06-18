"""Qdrant vector store with API-based embeddings."""

from __future__ import annotations

import time
import uuid

from openai import OpenAI
from qdrant_client import QdrantClient, models

from raven.config import (
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    EMBEDDING_MODEL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_URL,
)
from raven.logging_config import get_logger

logger = get_logger("raven.vectorstore")

EMBED_BATCH_SIZE = 32
EMBED_MAX_RETRIES = 5
EMBED_RETRY_DELAY = 3
UPSERT_BATCH_SIZE = 64

# Namespace for deriving deterministic Qdrant point IDs (UUIDs) from chunk string
# ids, so re-indexing the same chunk upserts in place instead of duplicating.
_ID_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


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
        if QDRANT_URL == ":memory:":
            self._client = QdrantClient(location=":memory:")
        else:
            # Generous timeout: remote upserts of 1024-dim batches over the network
            # blow past the 5s default and raise WriteTimeout.
            self._client = QdrantClient(
                url=QDRANT_URL, api_key=QDRANT_API_KEY or None, timeout=60
            )
        self._embedder = APIEmbedder()
        self._collection = QDRANT_COLLECTION

    def _exists(self) -> bool:
        return self._client.collection_exists(self._collection)

    def _ensure_collection(self, dim: int) -> None:
        """Create the collection (cosine) on first write, sized to the embedding
        dimension, with a keyword index on `source` for fast delete-by-source."""
        if self._exists():
            return
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
        # Payload index speeds up delete-by-source on server Qdrant; it's a no-op
        # (and warns) on the in-memory client used in tests, so skip it there.
        if QDRANT_URL != ":memory:":
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name="source",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

    def add(self, docs: list[dict]) -> None:
        if not docs:
            return
        texts = [d["text"] for d in docs]
        embeddings = self._embedder.embed(texts)
        self._ensure_collection(len(embeddings[0]))
        points = [
            models.PointStruct(
                id=str(uuid.uuid5(_ID_NAMESPACE, d["id"])),
                vector=emb,
                payload={**d.get("metadata", {}), "text": d["text"]},
            )
            for d, emb in zip(docs, embeddings, strict=True)
        ]
        # Upsert in small batches so a large file doesn't produce one oversized
        # request that times out against the remote server.
        for i in range(0, len(points), UPSERT_BATCH_SIZE):
            self._client.upsert(
                collection_name=self._collection,
                points=points[i : i + UPSERT_BATCH_SIZE],
            )

    def query(self, text: str, n_results: int = 5) -> list[dict]:
        if not self._exists():
            return []
        embedding = self._embedder.embed([text])[0]
        hits = self._client.query_points(
            collection_name=self._collection,
            query=embedding,
            limit=n_results,
            with_payload=True,
        ).points
        out = []
        for h in hits:
            payload = dict(h.payload or {})
            text_val = payload.pop("text", "")
            out.append({"text": text_val, "metadata": payload, "score": h.score})
        return out

    def delete_by_source(self, source: str) -> None:
        if not self._exists():
            return
        self._client.delete(
            collection_name=self._collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source", match=models.MatchValue(value=source)
                        )
                    ]
                )
            ),
        )

    def count(self) -> int:
        if not self._exists():
            return 0
        return self._client.count(collection_name=self._collection).count


_instance: VectorStore | None = None


def get_store() -> VectorStore:
    global _instance
    if _instance is None:
        _instance = VectorStore()
    return _instance
