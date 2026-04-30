"""
Cross-encoder reranker — lazy-loaded, memory-aware.

Set DISABLE_RERANKER=true (env var) to skip PyTorch/CrossEncoder entirely.
Fallback: return top_n chunks sorted by ChromaDB cosine similarity score.
This keeps the API alive on memory-constrained hosts (e.g. Render free tier).

Full reranking (DISABLE_RERANKER unset or false):
  Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  ~120 MB on disk, solid precision on passage retrieval.
"""

from __future__ import annotations

import os

_model = None  # lazy — only load when first call arrives


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder  # noqa: PLC0415
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
    return _model


def rerank(query: str, chunks: list[dict], top_n: int) -> list[dict]:
    """
    Rerank chunks by relevance and return top_n.

    When DISABLE_RERANKER=true: sorts by ChromaDB cosine score (no PyTorch).
    When enabled: uses cross-encoder model for precise reranking.
    """
    if not chunks:
        return []

    if os.getenv("DISABLE_RERANKER", "false").lower() == "true":
        # Lightweight fallback — ChromaDB already returns cosine similarity
        sorted_chunks = sorted(chunks, key=lambda c: c.get("score", 0.0), reverse=True)
        return [
            {**c, "rerank_score": round(float(c.get("score", 0.0)), 4)}
            for c in sorted_chunks[:top_n]
        ]

    model = _get_model()
    pairs = [(query, c["text"]) for c in chunks]
    scores = model.predict(pairs)

    ranked = sorted(
        zip(chunks, scores.tolist()),
        key=lambda x: x[1],
        reverse=True,
    )

    return [
        {**chunk, "rerank_score": round(float(score), 4)}
        for chunk, score in ranked[:top_n]
    ]
