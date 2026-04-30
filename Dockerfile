FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/lists/*

# Lean deps only — no PyTorch, no sentence-transformers
COPY requirements-render.txt .
RUN pip install --no-cache-dir -r requirements-render.txt

COPY . .

EXPOSE 8000

# Ingest knowledge base then start API
CMD ["sh", "-c", "python scripts/ingest.py --reset && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
