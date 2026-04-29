"""
Main RAG pipeline — wires retriever → reranker → generator with
full Langfuse tracing and cost accounting.

Usage:
    from app.rag.pipeline import run_query
    result = run_query("What is our CAC reduction target?")
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.config import get_settings
from app.observability.cost import compute_cost
from app.observability.tracer import RAGTrace
from app.rag.generator import generate
from app.rag.reranker import rerank
from app.rag.retriever import retrieve

settings = get_settings()


@dataclass
class QueryResult:
    answer: str
    contexts: list[str]          # text of reranked chunks
    sources: list[str]           # filenames
    trace_id: str
    metrics: dict                # latency breakdown, cost, tokens


def run_query(
    query: str,
    session_id: str | None = None,
    model: str | None = None,
) -> QueryResult:
    """
    End-to-end RAG pipeline with observability.

    Latency budget (typical on CPU):
        retrieval  ~20–80 ms   (ChromaDB ANN)
        reranking  ~100–300 ms (cross-encoder)
        generation ~400–1200 ms (Groq network)
    """
    sid = session_id or str(uuid.uuid4())
    trace = RAGTrace(query=query, session_id=sid)

    # ── 1. Retrieval ──────────────────────────────────────────────────────────
    with trace.span_retrieval(top_k=settings.retrieval_top_k):
        raw_chunks = retrieve(query, top_k=settings.retrieval_top_k)

    # ── 2. Reranking ──────────────────────────────────────────────────────────
    with trace.span_reranking(top_n=settings.rerank_top_n):
        ranked_chunks = rerank(query, raw_chunks, top_n=settings.rerank_top_n)

    # ── 3. Generation ─────────────────────────────────────────────────────────
    active_model = model or settings.groq_model
    with trace.span_generation(model=active_model):
        gen = generate(query, ranked_chunks, model=active_model)
        trace.metrics.prompt_tokens     = gen.prompt_tokens
        trace.metrics.completion_tokens = gen.completion_tokens

    # ── 4. Cost ───────────────────────────────────────────────────────────────
    trace.metrics.cost_usd = compute_cost(
        model=active_model,
        prompt_tokens=gen.prompt_tokens,
        completion_tokens=gen.completion_tokens,
    )

    # ── 5. Close trace ────────────────────────────────────────────────────────
    contexts = [c["text"] for c in ranked_chunks]
    trace.finalise(answer=gen.answer, contexts=contexts)

    return QueryResult(
        answer=gen.answer,
        contexts=contexts,
        sources=list({c["source"] for c in ranked_chunks}),
        trace_id=trace.trace_id,
        metrics={
            "retrieval_latency_ms":  round(trace.metrics.retrieval.latency_ms, 2),
            "reranking_latency_ms":  round(trace.metrics.reranking.latency_ms, 2),
            "generation_latency_ms": round(trace.metrics.generation.latency_ms, 2),
            "total_latency_ms":      round(trace.metrics.total_latency_ms, 2),
            "prompt_tokens":         gen.prompt_tokens,
            "completion_tokens":     gen.completion_tokens,
            "cost_usd":              trace.metrics.cost_usd,
            "model":                 active_model,
            "num_chunks_retrieved":  len(raw_chunks),
            "num_chunks_used":       len(ranked_chunks),
        },
    )
