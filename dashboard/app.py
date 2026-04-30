"""
RAG Observatory — Streamlit observability dashboard.

Pulls trace metadata from Langfuse, computes latency percentiles and
cost aggregates, and renders them with Plotly.

Your unique angle as a data analyst: this is the dashboard NOBODY else
puts in their portfolio because most AI engineers don't think to build it.

Run:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from langfuse import Langfuse

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import get_settings

settings = get_settings()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RAG Observatory",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Langfuse client ───────────────────────────────────────────────────────────
@st.cache_resource
def get_langfuse():
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )

langfuse = get_langfuse()


# ── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)   # refresh every 60 s
def fetch_traces(limit: int = 200) -> pd.DataFrame:
    """Pull recent traces from Langfuse and flatten to DataFrame."""
    try:
        traces = langfuse.get_traces(limit=limit)
        rows = []
        for t in traces.data:
            meta = t.metadata or {}
            rows.append({
                "trace_id":              t.id,
                "timestamp":             t.timestamp,
                "total_latency_ms":      meta.get("total_latency_ms"),
                "retrieval_latency_ms":  meta.get("retrieval_latency_ms"),
                "reranking_latency_ms":  meta.get("reranking_latency_ms"),
                "generation_latency_ms": meta.get("generation_latency_ms"),
                "prompt_tokens":         meta.get("prompt_tokens"),
                "completion_tokens":     meta.get("completion_tokens"),
                "cost_usd":              meta.get("cost_usd"),
                "model":                 meta.get("model", "unknown"),
                "num_contexts":          meta.get("num_contexts"),
            })
        df_out = pd.DataFrame(rows)
        if df_out.empty or "total_latency_ms" not in df_out.columns:
            return pd.DataFrame()
        return df_out.dropna(subset=["total_latency_ms"])
    except Exception as e:
        st.error(f"Failed to fetch traces: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def fetch_scores(limit: int = 500) -> pd.DataFrame:
    """Pull RAGAS quality scores from Langfuse."""
    try:
        scores = langfuse.get_scores(limit=limit)
        rows = [
            {
                "trace_id": s.trace_id,
                "metric":   s.name,
                "value":    s.value,
                "timestamp": s.created_at,
            }
            for s in scores.data
        ]
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Failed to fetch scores: {e}")
        return pd.DataFrame()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔭 RAG Observatory")
    st.markdown("Live observability dashboard for your production RAG system.")
    st.divider()

    trace_limit = st.slider("Traces to load", 50, 500, 200, step=50)
    st.caption(f"Langfuse host: `{settings.langfuse_host}`")

    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("**Quality Gates**")
    st.metric("Faithfulness gate", f"≥ {settings.faithfulness_threshold}")
    st.metric("Relevancy gate",    f"≥ {settings.answer_relevancy_threshold}")


# ── Load data ─────────────────────────────────────────────────────────────────
df = fetch_traces(limit=trace_limit)
scores_df = fetch_scores(limit=trace_limit * 3)

if df.empty:
    st.warning("No traces found. Run some queries first: `POST /query`")
    st.stop()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp")

# ── Top KPI row ───────────────────────────────────────────────────────────────
st.header("Performance Overview")

col1, col2, col3, col4, col5 = st.columns(5)

p50 = df["total_latency_ms"].quantile(0.50)
p95 = df["total_latency_ms"].quantile(0.95)
total_cost = df["cost_usd"].sum()
avg_cost = df["cost_usd"].mean()
query_count = len(df)

col1.metric("Queries", f"{query_count:,}")
col2.metric("p50 Latency", f"{p50:.0f} ms")
col3.metric("p95 Latency", f"{p95:.0f} ms",
            delta=f"{p95 - p50:.0f} ms tail", delta_color="inverse")
col4.metric("Total Cost", f"${total_cost:.4f}")
col5.metric("Avg Cost/Query", f"${avg_cost:.6f}")

st.divider()

# ── Latency budget breakdown ──────────────────────────────────────────────────
st.subheader("📊 Latency Budget (stacked by pipeline stage)")

latency_cols = ["retrieval_latency_ms", "reranking_latency_ms", "generation_latency_ms"]
latency_labels = {"retrieval_latency_ms": "Retrieval", "reranking_latency_ms": "Reranking", "generation_latency_ms": "Generation"}

df_latency = df[["timestamp"] + latency_cols].copy()
df_latency_melted = df_latency.melt(
    id_vars="timestamp",
    value_vars=latency_cols,
    var_name="stage",
    value_name="latency_ms",
)
df_latency_melted["stage"] = df_latency_melted["stage"].map(latency_labels)

fig_latency = px.bar(
    df_latency_melted,
    x="timestamp",
    y="latency_ms",
    color="stage",
    title="End-to-end latency breakdown over time",
    labels={"latency_ms": "Latency (ms)", "timestamp": "Time", "stage": "Stage"},
    color_discrete_map={"Retrieval": "#636EFA", "Reranking": "#EF553B", "Generation": "#00CC96"},
    barmode="stack",
)
fig_latency.update_layout(height=350, margin=dict(t=40, b=20))
st.plotly_chart(fig_latency, use_container_width=True)


# ── Latency percentiles ───────────────────────────────────────────────────────
st.subheader("⏱️ Latency Percentiles by Stage")

pct_data = []
for col, label in latency_labels.items():
    s = df[col].dropna()
    pct_data.append({
        "Stage": label,
        "p50 (ms)": round(s.quantile(0.50), 1),
        "p75 (ms)": round(s.quantile(0.75), 1),
        "p90 (ms)": round(s.quantile(0.90), 1),
        "p95 (ms)": round(s.quantile(0.95), 1),
        "p99 (ms)": round(s.quantile(0.99), 1),
    })

st.dataframe(
    pd.DataFrame(pct_data).set_index("Stage"),
    use_container_width=True,
)

st.divider()

# ── Cost over time ────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("💰 Cost Over Time")
    df_cost = df[["timestamp", "cost_usd"]].copy()
    df_cost["cumulative_cost"] = df_cost["cost_usd"].cumsum()

    fig_cost = make_subplots(specs=[[{"secondary_y": True}]])
    fig_cost.add_trace(
        go.Bar(x=df_cost["timestamp"], y=df_cost["cost_usd"], name="Per-query cost", marker_color="#636EFA"),
        secondary_y=False,
    )
    fig_cost.add_trace(
        go.Scatter(x=df_cost["timestamp"], y=df_cost["cumulative_cost"], name="Cumulative", line=dict(color="#EF553B", width=2)),
        secondary_y=True,
    )
    fig_cost.update_layout(height=300, title="Query cost (USD)", margin=dict(t=40, b=20))
    fig_cost.update_yaxes(title_text="Per-query $", secondary_y=False)
    fig_cost.update_yaxes(title_text="Cumulative $", secondary_y=True)
    st.plotly_chart(fig_cost, use_container_width=True)

with col_b:
    st.subheader("🔤 Token Distribution")
    fig_tokens = go.Figure()
    fig_tokens.add_trace(go.Box(y=df["prompt_tokens"].dropna(), name="Prompt tokens", marker_color="#636EFA"))
    fig_tokens.add_trace(go.Box(y=df["completion_tokens"].dropna(), name="Completion tokens", marker_color="#00CC96"))
    fig_tokens.update_layout(height=300, title="Token counts per query", margin=dict(t=40, b=20))
    st.plotly_chart(fig_tokens, use_container_width=True)

st.divider()

# ── Quality scores ────────────────────────────────────────────────────────────
st.subheader("✅ RAGAS Quality Scores")

if scores_df.empty:
    st.info("No quality scores yet. Run `python evals/runner.py --upload` to populate.")
else:
    scores_df["timestamp"] = pd.to_datetime(scores_df["timestamp"])
    metrics_present = scores_df["metric"].unique().tolist()

    fig_scores = px.box(
        scores_df,
        x="metric",
        y="value",
        color="metric",
        points="all",
        title="RAGAS metric distribution",
        labels={"value": "Score (0–1)", "metric": "Metric"},
    )
    # Add gate lines
    fig_scores.add_hline(
        y=settings.faithfulness_threshold, line_dash="dash", line_color="red",
        annotation_text=f"Faithfulness gate ({settings.faithfulness_threshold})",
    )
    fig_scores.add_hline(
        y=settings.answer_relevancy_threshold, line_dash="dot", line_color="orange",
        annotation_text=f"Relevancy gate ({settings.answer_relevancy_threshold})",
    )
    fig_scores.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig_scores, use_container_width=True)

    # Score trend over time
    for metric in metrics_present:
        m_df = scores_df[scores_df["metric"] == metric].sort_values("timestamp")
        if len(m_df) > 1:
            fig_trend = px.line(
                m_df, x="timestamp", y="value",
                title=f"{metric} over time",
                markers=True,
            )
            threshold = (
                settings.faithfulness_threshold if "faithfulness" in metric
                else settings.answer_relevancy_threshold if "relevancy" in metric
                else None
            )
            if threshold:
                fig_trend.add_hline(y=threshold, line_dash="dash", line_color="red")
            fig_trend.update_layout(height=250)
            st.plotly_chart(fig_trend, use_container_width=True)

st.divider()

# ── Raw trace table ───────────────────────────────────────────────────────────
with st.expander("🗃️ Raw trace data"):
    display_cols = ["timestamp", "model", "total_latency_ms", "retrieval_latency_ms",
                    "reranking_latency_ms", "generation_latency_ms",
                    "prompt_tokens", "completion_tokens", "cost_usd"]
    st.dataframe(
        df[display_cols].sort_values("timestamp", ascending=False),
        use_container_width=True,
    )

st.caption(f"Data refreshes every 60 s | Langfuse: {settings.langfuse_host}")
