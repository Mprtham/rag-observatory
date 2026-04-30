"""
Ingestion script — chunks docs/ markdown files and loads into ChromaDB.
Uses ChromaDB's built-in ONNX embedding (no PyTorch required).

Usage:
    python scripts/ingest.py             # ingest docs/ directory
    python scripts/ingest.py --reset     # wipe collection first
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from app.config import get_settings

settings = get_settings()

DOCS_DIR   = Path(__file__).parent.parent / "docs"
CHUNK_SIZE = 400    # words
OVERLAP    = 50     # words


# ── Chunking ──────────────────────────────────────────────────────────────────

def split_into_chunks(text: str, chunk_words: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_words
        chunks.append(" ".join(words[start:end]))
        start += chunk_words - overlap
    return [c.strip() for c in chunks if len(c.strip()) > 50]


def load_markdown_file(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    text = re.sub(r"#{1,6}\s+", "", raw)
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks = split_into_chunks(text)
    return [
        {"text": chunk, "source": path.name, "chunk_id": f"{path.stem}_{i}"}
        for i, chunk in enumerate(chunks)
    ]


# ── ChromaDB ─────────────────────────────────────────────────────────────────

def get_collection(reset: bool = False) -> chromadb.Collection:
    embed_fn = DefaultEmbeddingFunction()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

    if reset:
        try:
            client.delete_collection(settings.chroma_collection)
            print(f"Deleted existing collection '{settings.chroma_collection}'.")
        except Exception:
            pass

    return client.get_or_create_collection(
        name=settings.chroma_collection,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )


def ingest(reset: bool = False) -> None:
    if not DOCS_DIR.exists():
        print(f"ERROR: docs/ directory not found at {DOCS_DIR}")
        sys.exit(1)

    md_files = list(DOCS_DIR.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {DOCS_DIR}")
        sys.exit(1)

    print(f"Found {len(md_files)} document(s): {[f.name for f in md_files]}")

    collection = get_collection(reset=reset)
    existing_ids = set(collection.get()["ids"])

    total_chunks = 0
    skipped = 0

    for path in md_files:
        chunks = load_markdown_file(path)
        print(f"  {path.name}: {len(chunks)} chunks")
        new_chunks = [c for c in chunks if c["chunk_id"] not in existing_ids]
        skipped += len(chunks) - len(new_chunks)

        if not new_chunks:
            continue

        collection.add(
            ids=[c["chunk_id"] for c in new_chunks],
            documents=[c["text"] for c in new_chunks],
            metadatas=[{"source": c["source"], "chunk_id": c["chunk_id"]} for c in new_chunks],
        )
        total_chunks += len(new_chunks)

    print(f"\n✅ Ingestion complete.")
    print(f"   Chunks added:   {total_chunks}")
    print(f"   Chunks skipped: {skipped} (already in collection)")
    print(f"   Total in store: {collection.count()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    ingest(reset=args.reset)
