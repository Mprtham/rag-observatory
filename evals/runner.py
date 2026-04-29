"""
RAGAS evaluation runner.

Runs the full eval dataset through the RAG pipeline, scores each answer
with RAGAS metrics, and optionally uploads scores to Langfuse.

Usage:
    python evals/runner.py                  # run all, print results
    python evals/runner.py --upload         # also push scores to Langfuse
    python evals/runner.py --sample 3       # quick smoke test on 3 samples
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from datasets import Dataset
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_recall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

# Make sure project root is on the path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.rag.pipeline import run_query

settings = get_settings()

DATASET_PATH = Path(__file__).parent / "dataset.json"
RESULTS_PATH = Path(__file__).parent / "eval_results.json"


def build_ragas_llm():
    """Wrap Groq in RAGAS-compatible LLM interface."""
    llm = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
    )
    return LangchainLLMWrapper(llm)


def build_ragas_embeddings():
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return LangchainEmbeddingsWrapper(embeddings)


def run_eval(
    samples: int | None = None,
    upload_to_langfuse: bool = False,
) -> dict:
    """Run evaluation and return metric scores."""
    print("Loading eval dataset...")
    raw = json.loads(DATASET_PATH.read_text())
    if samples:
        raw = raw[:samples]

    questions, answers, contexts, ground_truths, trace_ids = [], [], [], [], []

    print(f"Running {len(raw)} queries through RAG pipeline...")
    for i, item in enumerate(raw, 1):
        q = item["question"]
        gt = item["ground_truth"]
        print(f"  [{i}/{len(raw)}] {q[:60]}...")

        result = run_query(q)

        questions.append(q)
        answers.append(result.answer)
        contexts.append(result.contexts)
        ground_truths.append(gt)
        trace_ids.append(result.trace_id)

    # ── RAGAS evaluation ──────────────────────────────────────────────────────
    print("\nScoring with RAGAS...")
    ragas_llm   = build_ragas_llm()
    ragas_embed = build_ragas_embeddings()

    dataset = Dataset.from_dict({
        "question":   questions,
        "answer":     answers,
        "contexts":   contexts,
        "ground_truth": ground_truths,
    })

    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_recall],
        llm=ragas_llm,
        embeddings=ragas_embed,
        raise_exceptions=False,
    )

    scores = {
        "faithfulness":     float(result["faithfulness"]),
        "answer_relevancy": float(result["answer_relevancy"]),
        "context_recall":   float(result["context_recall"]),
        "num_samples":      len(raw),
    }

    # ── Per-sample scores ─────────────────────────────────────────────────────
    df = result.to_pandas()
    per_sample = df[["question", "faithfulness", "answer_relevancy", "context_recall"]].to_dict("records")

    # ── Optional Langfuse upload ──────────────────────────────────────────────
    if upload_to_langfuse:
        print("Uploading scores to Langfuse...")
        from app.observability.tracer import _client as langfuse
        for i, (trace_id, row) in enumerate(zip(trace_ids, per_sample)):
            for metric_name in ["faithfulness", "answer_relevancy", "context_recall"]:
                val = row.get(metric_name)
                if val is not None:
                    langfuse.score(
                        trace_id=trace_id,
                        name=metric_name,
                        value=float(val),
                        comment="ragas-eval",
                    )
        langfuse.flush()

    # ── Save results ──────────────────────────────────────────────────────────
    output = {"aggregate": scores, "per_sample": per_sample}
    RESULTS_PATH.write_text(json.dumps(output, indent=2))
    print(f"\nResults saved to {RESULTS_PATH}")

    return scores


def print_report(scores: dict) -> None:
    print("\n" + "=" * 50)
    print("EVAL REPORT")
    print("=" * 50)
    print(f"  Faithfulness:      {scores['faithfulness']:.3f}  (gate: {settings.faithfulness_threshold})")
    print(f"  Answer Relevancy:  {scores['answer_relevancy']:.3f}  (gate: {settings.answer_relevancy_threshold})")
    print(f"  Context Recall:    {scores['context_recall']:.3f}")
    print(f"  Samples:           {scores['num_samples']}")
    print("=" * 50)

    passed = (
        scores["faithfulness"]     >= settings.faithfulness_threshold
        and scores["answer_relevancy"] >= settings.answer_relevancy_threshold
    )
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"  Quality gate: {status}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", action="store_true", help="Upload scores to Langfuse")
    parser.add_argument("--sample", type=int, default=None, help="Run only N samples")
    args = parser.parse_args()

    scores = run_eval(samples=args.sample, upload_to_langfuse=args.upload)
    print_report(scores)
