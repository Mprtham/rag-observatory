"""
Groq LLM generator with citation enforcement.

System prompt forces the model to:
  1. Answer only from provided context.
  2. Cite source filenames inline [source].
  3. Say "I don't know" when context is insufficient.

Returns both the answer text and raw usage stats for cost tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from groq import Groq
from app.config import get_settings

settings = get_settings()
_client = Groq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """You are a precise analytics knowledge assistant.

Rules:
1. Answer ONLY using the provided context passages.
2. Cite the source of each claim inline as [source_name].
3. If the context does not contain enough information, respond exactly:
   "I don't have enough information in the knowledge base to answer this."
4. Be concise. Prefer bullet points for lists of facts.
5. Never fabricate metrics, names, or definitions."""


@dataclass
class GenerationResult:
    answer: str
    prompt_tokens: int
    completion_tokens: int
    model: str


def build_context_block(chunks: list[dict]) -> str:
    """Format retrieved chunks into the context section of the prompt."""
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[{c['source']}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def generate(
    query: str,
    chunks: list[dict],
    model: str | None = None,
) -> GenerationResult:
    """Call Groq and return the answer + token usage."""
    active_model = model or settings.groq_model
    context_block = build_context_block(chunks)

    user_message = f"""Context passages:
{context_block}

---
Question: {query}"""

    response = _client.chat.completions.create(
        model=active_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.1,     # low temp → factual, consistent
        max_tokens=1024,
    )

    choice = response.choices[0]
    usage  = response.usage

    return GenerationResult(
        answer=choice.message.content.strip(),
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        model=active_model,
    )
