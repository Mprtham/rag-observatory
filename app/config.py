from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Groq ─────────────────────────────────────────────────────────────────
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"
    groq_model_premium: str = "llama-3.3-70b-versatile"

    # ── Langfuse ─────────────────────────────────────────────────────────────
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str = "https://cloud.langfuse.com"

    # ── ChromaDB ─────────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "knowledge_base"

    # ── RAG ──────────────────────────────────────────────────────────────────
    retrieval_top_k: int = 10
    rerank_top_n: int = 3

    # ── Quality gates ─────────────────────────────────────────────────────────
    faithfulness_threshold: float = 0.80
    answer_relevancy_threshold: float = 0.75

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
