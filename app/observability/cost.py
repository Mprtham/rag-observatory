"""Token cost calculator for Groq models."""

# Groq pricing as of 2025 (USD per token)
GROQ_PRICING: dict[str, dict[str, float]] = {
    "llama-3.1-8b-instant": {
        "input":  0.05 / 1_000_000,
        "output": 0.08 / 1_000_000,
    },
    "llama-3.1-70b-versatile": {
        "input":  0.59 / 1_000_000,
        "output": 0.79 / 1_000_000,
    },
    "llama-3.3-70b-versatile": {
        "input":  0.59 / 1_000_000,
        "output": 0.79 / 1_000_000,
    },
    "mixtral-8x7b-32768": {
        "input":  0.24 / 1_000_000,
        "output": 0.24 / 1_000_000,
    },
}


def compute_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return USD cost for a single Groq call."""
    pricing = GROQ_PRICING.get(model, GROQ_PRICING["llama-3.1-8b-instant"])
    return (prompt_tokens * pricing["input"]) + (completion_tokens * pricing["output"])


def format_cost(cost_usd: float) -> str:
    """Human-readable cost string."""
    if cost_usd < 0.001:
        return f"${cost_usd * 1000:.4f}m"   # milli-dollars
    return f"${cost_usd:.6f}"
