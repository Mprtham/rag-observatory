"""
Cross-encoder reranker.

Takes the top-k dense-retrieved chunks and re-scores them with a
cross-encoder model (query + chunk fed jointly → single relevance score).
This catches cases where the bi-encoder embedding missed semantic overlap.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  - ~70 MB, fast on CPU, solid precision on passage retrieval.
"""

from __future__ import annotations

from sentence_transformers import CrossEncoder

_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)


def rerank(query: str, chunks: list[dict], top_n: int) -> list[dict]:
    """
    Rerank `chunks` by cross-encoder score and return top_n.

    Each chunk dict must have a "text" key.
    Output dicts gain a "rerank_score" key (higher = more relevant).
    """
    if not chunks:
        return []

    pairs = [(query, c["text"]) for c in chunks]
    scores = _model.predict(pairs)          # returns numpy array

    ranked = sorted(
        zip(chunks, scores.tolist()),
        key=lambda x: x[1],
        reverse=True,
    )

    result = []
    for chunk, score in ranked[:top_n]:
        result.append({**chunk, "rerank_score": round(float(score), 4)})

    return result
