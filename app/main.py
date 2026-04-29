"""
RAG Observatory — FastAPI backend.

Endpoints:
    POST /query        Run a RAG query (traced + costed)
    GET  /health       Liveness probe
    GET  /metrics      Aggregate p50/p95 from last N traces (Langfuse API)
"""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.rag.pipeline import QueryResult, run_query

app = FastAPI(
    title="RAG Observatory",
    description="Production RAG with Langfuse observability, cross-encoder reranking, and CI eval gates.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    model: Optional[str] = None   # override default model


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    trace_id: str
    metrics: dict


class HealthResponse(BaseModel):
    status: str
    vector_store: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        from app.rag.retriever import get_collection
        col = get_collection()
        vs_status = f"ok ({col.count()} chunks)"
    except Exception as e:
        vs_status = f"error: {e}"

    return HealthResponse(status="ok", vector_store=vs_status)


@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest) -> QueryResponse:
    if not req.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty.")

    try:
        result: QueryResult = run_query(
            query=req.query,
            session_id=req.session_id,
            model=req.model,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    return QueryResponse(
        answer=result.answer,
        sources=result.sources,
        trace_id=result.trace_id,
        metrics=result.metrics,
    )


@app.get("/")
def root():
    return {
        "project": "RAG Observatory",
        "docs": "/docs",
        "health": "/health",
    }
