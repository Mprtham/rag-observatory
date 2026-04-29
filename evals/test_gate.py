"""
CI quality gate — pytest.

Fails the build if RAGAS scores are below thresholds defined in .env.
Runs a 3-sample smoke test by default (fast; full eval in nightly CI).

Run locally:
    pytest evals/test_gate.py -v

Run in CI (full dataset):
    EVAL_FULL=1 pytest evals/test_gate.py -v
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings

settings = get_settings()

RESULTS_PATH = Path(__file__).parent / "eval_results.json"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def eval_scores():
    """Run evaluation once per pytest session."""
    from evals.runner import run_eval

    full = os.getenv("EVAL_FULL", "0") == "1"
    sample_n = None if full else 3

    scores = run_eval(
        samples=sample_n,
        upload_to_langfuse=True,   # always upload CI scores
    )
    return scores


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_faithfulness_above_threshold(eval_scores):
    """Answer must be grounded in retrieved context."""
    score = eval_scores["faithfulness"]
    threshold = settings.faithfulness_threshold
    assert score >= threshold, (
        f"Faithfulness {score:.3f} below threshold {threshold}. "
        f"Model is hallucinating — check system prompt and context length."
    )


def test_answer_relevancy_above_threshold(eval_scores):
    """Answer must address the question asked."""
    score = eval_scores["answer_relevancy"]
    threshold = settings.answer_relevancy_threshold
    assert score >= threshold, (
        f"Answer relevancy {score:.3f} below threshold {threshold}. "
        f"Retrieval or reranking may be returning off-topic chunks."
    )


def test_context_recall_acceptable(eval_scores):
    """Context recall sanity check (soft gate — warn only)."""
    score = eval_scores["context_recall"]
    if score < 0.70:
        pytest.warns(
            UserWarning,
            match=f"Context recall {score:.3f} is below 0.70 — consider increasing retrieval_top_k.",
        )


def test_no_sample_catastrophic_failure():
    """
    Check per-sample results for any score of 0.0 (complete failure).
    A single catastrophic answer is a red flag even if aggregate is OK.
    """
    if not RESULTS_PATH.exists():
        pytest.skip("No eval_results.json found. Run runner.py first.")

    data = json.loads(RESULTS_PATH.read_text())
    per_sample = data.get("per_sample", [])

    catastrophic = [
        r for r in per_sample
        if r.get("faithfulness", 1.0) == 0.0
        or r.get("answer_relevancy", 1.0) == 0.0
    ]
    assert not catastrophic, (
        f"{len(catastrophic)} sample(s) scored 0.0 on at least one metric:\n"
        + "\n".join(r["question"] for r in catastrophic)
    )
