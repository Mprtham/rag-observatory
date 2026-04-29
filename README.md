# 🔭 RAG Observatory

**Production RAG with full observability, cross-encoder reranking, RAGAS eval suite, and CI quality gates.**

> Built to show the 70% of production AI work nobody puts in their portfolio: monitoring, evaluation, and regression prevention.

---

## Architecture

```
User Query
    │
    ▼
FastAPI  (/query)
    │
    ├─► ChromaDB retrieval       ← dense vector ANN (all-MiniLM-L6-v2)
    │       [span: retrieval]
    │
    ├─► Cross-encoder reranker   ← ms-marco-MiniLM-L-6-v2
    │       [span: reranking]
    │
    ├─► Groq LLM generation      ← citation-enforced system prompt
    │       [span: generation]
    │
    └─► Langfuse trace           ← latency budget + cost + token usage
            │
            └─► Streamlit dashboard  ← p50/p95, cost over time, quality trends
                        │
                        └─► RAGAS eval CI  ← GitHub Actions quality gate
```

---

## What Makes This Different

| Feature | Tutorial RAG | RAG Observatory |
|---------|-------------|-----------------|
| Vector search | ✅ | ✅ |
| Cross-encoder reranking | ❌ | ✅ |
| Citation enforcement | ❌ | ✅ |
| Langfuse tracing | ❌ | ✅ (per-span latency) |
| Cost tracking | ❌ | ✅ (USD per query) |
| RAGAS eval suite | ❌ | ✅ (faithfulness, relevancy, recall) |
| CI quality gate | ❌ | ✅ (blocks merge on regression) |
| Observability dashboard | ❌ | ✅ (Plotly p50/p95 breakdown) |
| Docker Compose | ❌ | ✅ |

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/rag-observatory
cd rag-observatory
cp .env.example .env
# Fill in GROQ_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY
```

Get keys:
- **Groq:** https://console.groq.com (free tier)
- **Langfuse:** https://cloud.langfuse.com (free tier → Settings → API Keys)

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Ingest knowledge base

```bash
python scripts/ingest.py
# → loads docs/ markdown files into ChromaDB
# → output: "Ingestion complete. 47 chunks added."
```

### 4. Start the API

```bash
uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

### 5. Run a query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What statistical test should I use for A/B testing conversion rates?"}'
```

Response includes `trace_id`, `metrics` (latency breakdown, cost, tokens), and `sources`.

### 6. Run the observability dashboard

```bash
streamlit run dashboard/app.py
# → http://localhost:8501
```

### 7. Run the eval suite

```bash
# Smoke test (3 samples, ~2 min)
pytest evals/test_gate.py -v

# Full eval (10 samples, ~10 min) + upload scores to Langfuse
EVAL_FULL=1 python evals/runner.py --upload
```

---

## Docker Compose

```bash
docker compose up --build
# API:       http://localhost:8000
# Dashboard: http://localhost:8501
```

---

## Project Structure

```
rag-observatory/
├── app/
│   ├── config.py               # Pydantic settings (env vars)
│   ├── main.py                 # FastAPI endpoints
│   ├── rag/
│   │   ├── retriever.py        # ChromaDB ANN retrieval
│   │   ├── reranker.py         # Cross-encoder reranking
│   │   ├── generator.py        # Groq LLM + citation prompt
│   │   └── pipeline.py         # Orchestration (retrieve→rerank→generate)
│   └── observability/
│       ├── tracer.py           # Langfuse trace/span wrapper
│       └── cost.py             # Token cost calculator
├── dashboard/
│   └── app.py                  # Streamlit + Plotly dashboard
├── evals/
│   ├── dataset.json            # 10 Q&A pairs
│   ├── runner.py               # RAGAS eval runner
│   └── test_gate.py            # Pytest CI quality gate
├── scripts/
│   └── ingest.py               # Doc chunking + ChromaDB ingestion
├── docs/                       # Sample knowledge base (markdown)
├── .github/workflows/
│   └── eval_gate.yml           # CI: smoke (PRs) + full (main/nightly)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Metrics Tracked (per query)

| Metric | Where visible |
|--------|--------------|
| Retrieval latency (ms) | Langfuse span + dashboard |
| Reranking latency (ms) | Langfuse span + dashboard |
| Generation latency (ms) | Langfuse span + dashboard |
| Total latency (ms) | Langfuse trace + dashboard |
| p50 / p95 latency | Dashboard (computed over N traces) |
| Prompt tokens | Langfuse usage + dashboard |
| Completion tokens | Langfuse usage + dashboard |
| Cost (USD) | Langfuse metadata + dashboard |
| Faithfulness score | Langfuse score (after eval run) |
| Answer relevancy | Langfuse score (after eval run) |
| Context recall | Langfuse score (after eval run) |

---

## CI Quality Gate Behaviour

| Event | Gate type | Samples | Blocks merge? |
|-------|-----------|---------|---------------|
| Pull request | Smoke | 3 | ✅ Yes |
| Push to main | Full | 10 | ✅ Yes |
| Nightly schedule | Full | 10 | ❌ Alerts only |

Thresholds (configurable via `.env`):
- `FAITHFULNESS_THRESHOLD=0.80`
- `ANSWER_RELEVANCY_THRESHOLD=0.75`

---

## Stack

- **Backend:** FastAPI + Uvicorn
- **Vector store:** ChromaDB (local, persistent)
- **Embeddings:** `all-MiniLM-L6-v2` (sentence-transformers, offline)
- **Reranker:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (offline)
- **LLM:** Groq (`llama-3.1-8b-instant`)
- **Observability:** Langfuse Cloud
- **Evals:** RAGAS + pytest
- **Dashboard:** Streamlit + Plotly
- **CI:** GitHub Actions
- **Containers:** Docker + Docker Compose

---

## Extending This Project

- **Swap ChromaDB for Qdrant** — production-ready, supports filtering, Docker image available
- **Add BM25 hybrid retrieval** — merge BM25 scores with dense scores for better recall on keyword queries
- **Add prompt versioning** — track which system prompt version each trace used via Langfuse metadata
- **Add A/B model comparison** — route 50% of traffic to `llama-3.3-70b-versatile`, compare quality and cost
- **Swap to a fine-tuned model** — drop in a custom model endpoint and compare eval scores vs baseline

---

## Author

Prathamesh Mishra — [linkedin.com/in/prathameshmishra07](https://linkedin.com/in/prathameshmishra07) · [github.com/Mprtham](https://github.com/Mprtham)
