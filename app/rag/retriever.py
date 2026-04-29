"""
ChromaDB retriever with sentence-transformer embeddings.
Hybrid search = dense vector search (ANN) over the same collection.
BM25 upgrade path: swap get_collection() for a BM25Retriever and merge scores.
"""

from __future__ import annotations

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from app.config import get_settings

settings = get_settings()

# Singleton — loaded once at import time
_embed_fn = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2",   # 80 MB, fast, good quality
    device="cpu",
)

_chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)


def get_collection() -> chromadb.Collection:
    return _chroma_client.get_or_create_collection(
        name=settings.chroma_collection,
        embedding_function=_embed_fn,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    """
    Return top-k chunks with their distances and metadata.

    Each result dict:
        {
            "id":       str,
            "text":     str,
            "source":   str,
            "distance": float,   # cosine distance (lower = closer)
        }
    """
    k = top_k or settings.retrieval_top_k
    collection = get_collection()

    if collection.count() == 0:
        raise RuntimeError(
            "Vector store is empty. Run `python scripts/ingest.py` first."
        )

    results = collection.query(
        query_texts=[query],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append(
            {
                "id":       meta.get("chunk_id", ""),
                "text":     doc,
                "source":   meta.get("source", "unknown"),
                "distance": round(dist, 4),
            }
        )
    return chunks
