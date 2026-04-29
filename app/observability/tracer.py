"""
Langfuse tracer — thin wrapper around the Langfuse SDK.

Each RAG query creates one Trace with three child Spans:
    trace
    ├── retrieval   (ChromaDB lookup)
    ├── reranking   (cross-encoder)
    └── generation  (Groq LLM call)

The trace carries top-level usage (cost, total latency) so Langfuse's
cost dashboard works out of the box.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from langfuse import Langfuse

from app.config import get_settings

settings = get_settings()

_client = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host,
)


@dataclass
class SpanMetrics:
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceMetrics:
    retrieval: SpanMetrics = field(default_factory=SpanMetrics)
    reranking: SpanMetrics = field(default_factory=SpanMetrics)
    generation: SpanMetrics = field(default_factory=SpanMetrics)
    total_latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""


class RAGTrace:
    """Context-manager-friendly trace object for one RAG query."""

    def __init__(self, query: str, session_id: str | None = None):
        self._query = query
        self._t0 = time.perf_counter()
        self.metrics = TraceMetrics()

        self._trace = _client.trace(
            name="rag-query",
            input={"query": query},
            session_id=session_id,
            tags=["rag", "production"],
        )

    # ── Span helpers ─────────────────────────────────────────────────────────

    @contextmanager
    def span_retrieval(self, top_k: int) -> Generator[None, None, None]:
        span = self._trace.span(
            name="retrieval",
            input={"query": self._query, "top_k": top_k},
        )
        t0 = time.perf_counter()
        try:
            yield
        finally:
            latency = (time.perf_counter() - t0) * 1000
            self.metrics.retrieval.latency_ms = latency
            span.end(
                metadata={"latency_ms": round(latency, 2)},
            )

    @contextmanager
    def span_reranking(self, top_n: int) -> Generator[None, None, None]:
        span = self._trace.span(
            name="reranking",
            input={"top_n": top_n},
        )
        t0 = time.perf_counter()
        try:
            yield
        finally:
            latency = (time.perf_counter() - t0) * 1000
            self.metrics.reranking.latency_ms = latency
            span.end(metadata={"latency_ms": round(latency, 2)})

    @contextmanager
    def span_generation(self, model: str) -> Generator[None, None, None]:
        span = self._trace.span(
            name="generation",
            input={"model": model},
        )
        t0 = time.perf_counter()
        try:
            yield
        finally:
            latency = (time.perf_counter() - t0) * 1000
            self.metrics.generation.latency_ms = latency
            self.metrics.model = model
            span.end(
                metadata={"latency_ms": round(latency, 2)},
                usage={
                    "input": self.metrics.prompt_tokens,
                    "output": self.metrics.completion_tokens,
                    "unit": "TOKENS",
                },
            )

    # ── Close ────────────────────────────────────────────────────────────────

    def finalise(self, answer: str, contexts: list[str]) -> None:
        """Call after all spans are closed. Writes top-level trace metadata."""
        self.metrics.total_latency_ms = (time.perf_counter() - self._t0) * 1000

        self._trace.update(
            output={"answer": answer},
            metadata={
                "total_latency_ms": round(self.metrics.total_latency_ms, 2),
                "retrieval_latency_ms": round(self.metrics.retrieval.latency_ms, 2),
                "reranking_latency_ms": round(self.metrics.reranking.latency_ms, 2),
                "generation_latency_ms": round(self.metrics.generation.latency_ms, 2),
                "prompt_tokens": self.metrics.prompt_tokens,
                "completion_tokens": self.metrics.completion_tokens,
                "cost_usd": round(self.metrics.cost_usd, 8),
                "model": self.metrics.model,
                "num_contexts": len(contexts),
            },
            usage={
                "input": self.metrics.prompt_tokens,
                "output": self.metrics.completion_tokens,
                "unit": "TOKENS",
            },
        )
        _client.flush()

    def score(self, name: str, value: float, comment: str = "") -> None:
        """Attach a quality score (faithfulness, relevancy, etc.)."""
        self._trace.score(name=name, value=value, comment=comment)
        _client.flush()

    @property
    def trace_id(self) -> str:
        return self._trace.id


def flush() -> None:
    """Force-flush all pending Langfuse events (useful in tests/scripts)."""
    _client.flush()
