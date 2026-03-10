"""
dashboard.py

Streamlit dashboard for the Transcript Analysis project.
Connects to the DuckDB warehouse built by analyze.py + dbt.

Features:
  - KPI summary cards
  - Ticket volume by primary / secondary category
  - Churn risk signal breakdown
  - Sentiment distribution
  - Monthly trend chart
  - AI-generated product gap narrative (from Claude, stored in DuckDB)
  - Interactive ticket explorer

Usage:
    streamlit run scripts/dashboard.py
"""

import os
import duckdb
import pandas as pd
import streamlit as st
import plotly.express as px
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data/transcript_analysis.duckdb"

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Transcript Analysis | Owner.com",
    page_icon="🎫",
    layout="wide",
)

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data():
    con = duckdb.connect(DB_PATH, read_only=True)
    fct = con.execute("SELECT * FROM fct_support_tickets").df()
    insights = con.execute("SELECT * FROM support_insights").df()
    try:
        narrative_row = con.execute(
            "SELECT narrative FROM product_gap_narrative ORDER BY generated_at DESC LIMIT 1"
        ).fetchone()
        narrative = narrative_row[0] if narrative_row else None
    except Exception:
        narrative = None
    con.close()
    return fct, insights, narrative


fct, insights, narrative = load_data()

# ── Sidebar filters ────────────────────────────────────────────────────────────
st.sidebar.title("🔍 Filters")

plan_options = ["All"] + sorted(fct["plan_type"].dropna().unique().tolist())
selected_plan = st.sidebar.selectbox("Plan Type", plan_options)

primary_options = ["All"] + sorted(fct["primary_label"].dropna().unique().tolist())
selected_primary = st.sidebar.selectbox("Primary Category", primary_options)

churn_filter = st.sidebar.radio("Customer Status", ["All", "Churned Only", "Active Only"])

# Apply filters
filtered = fct.copy()
if selected_plan != "All":
    filtered = filtered[filtered["plan_type"] == selected_plan]
if selected_primary != "All":
    filtered = filtered[filtered["primary_label"] == selected_primary]
if churn_filter == "Churned Only":
    filtered = filtered[filtered["is_churned"] == True]
elif churn_filter == "Active Only":
    filtered = filtered[filtered["is_churned"] == False]

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🎫 Transcript Analysis")
st.caption("Support ticket intelligence powered by Claude · Built on the modern data stack")
st.divider()

# ── KPI Cards ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

total = len(filtered)
churn_signals = filtered["is_churn_risk_signal"].sum()
negative = filtered["is_negative_sentiment"].sum()
high_urgency = filtered["is_high_urgency"].sum()
escalated = (filtered["status"] == "Escalated").sum()

col1.metric("Total Tickets", f"{total:,}")
col2.metric("Churn Risk Signals", f"{int(churn_signals):,}",
            help="Tickets from churned customers with negative sentiment")
col3.metric("Negative Sentiment", f"{int(negative):,}",
            delta=f"{round(100*negative/total if total else 0, 1)}%",
            delta_color="inverse")
col4.metric("High Urgency", f"{int(high_urgency):,}")
col5.metric("Escalated", f"{int(escalated):,}")

st.divider()

# ── Product Gap Narrative ──────────────────────────────────────────────────────
st.subheader("🧠 AI Product Gap Narrative")
if narrative:
    st.info(narrative)
else:
    st.warning("No narrative found. Run `python scripts/analyze.py` to generate one.")

st.divider()

# ── Charts Row 1 ──────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Volume by Primary Category")
    vol = (
        filtered.groupby("primary_label")
        .size()
        .reset_index(name="tickets")
        .sort_values("tickets", ascending=True)
    )
    fig = px.bar(
        vol, x="tickets", y="primary_label", orientation="h",
        color="tickets", color_continuous_scale="Blues",
        labels={"primary_label": "", "tickets": "Tickets"},
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(l=0))
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("😤 Sentiment Distribution")
    sent = (
        filtered.groupby("sentiment")
        .size()
        .reset_index(name="count")
    )
    sentiment_colors = {
        "Positive": "#22c55e",
        "Neutral": "#94a3b8",
        "Frustrated": "#f97316",
        "Angry": "#ef4444",
    }
    fig2 = px.pie(
        sent, names="sentiment", values="count",
        color="sentiment", color_discrete_map=sentiment_colors,
        hole=0.4,
    )
    fig2.update_traces(textposition="inside", textinfo="percent+label")
    fig2.update_layout(showlegend=False, margin=dict(t=0, b=0))
    st.plotly_chart(fig2, use_container_width=True)

# ── Charts Row 2 ──────────────────────────────────────────────────────────────
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("⚠️ Churn Risk by Category")
    risk = (
        filtered[filtered["is_churn_risk_signal"] == True]
        .groupby("primary_label")
        .size()
        .reset_index(name="churn_signals")
        .sort_values("churn_signals", ascending=True)
    )
    if not risk.empty:
        fig3 = px.bar(
            risk, x="churn_signals", y="primary_label", orientation="h",
            color="churn_signals", color_continuous_scale="Reds",
            labels={"primary_label": "", "churn_signals": "Churn Risk Signals"},
        )
        fig3.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(l=0))
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No churn risk signals in current filter.")

with col_right2:
    st.subheader("📈 Monthly Ticket Trend")
    trend = (
        filtered.groupby(["ticket_month", "primary_label"])
        .size()
        .reset_index(name="tickets")
    )
    trend["ticket_month"] = pd.to_datetime(trend["ticket_month"])
    if not trend.empty:
        fig4 = px.line(
            trend, x="ticket_month", y="tickets", color="primary_label",
            labels={"ticket_month": "Month", "tickets": "Tickets", "primary_label": "Category"},
        )
        fig4.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No trend data available.")

st.divider()

# ── Secondary breakdown heatmap ────────────────────────────────────────────────
st.subheader("🔍 Secondary Category Breakdown")
secondary_vol = (
    filtered.groupby(["primary_label", "secondary_label"])
    .size()
    .reset_index(name="tickets")
    .sort_values(["primary_label", "tickets"], ascending=[True, False])
)
fig5 = px.bar(
    secondary_vol, x="secondary_label", y="tickets",
    color="primary_label", barmode="group",
    labels={"secondary_label": "Secondary Category", "tickets": "Tickets", "primary_label": "Primary"},
)
fig5.update_layout(xaxis_tickangle=-30, legend_title="Primary Category")
st.plotly_chart(fig5, use_container_width=True)

# Build a compact data context for Claude
def build_data_context():
    top_categories = (
        filtered.groupby(["primary_label", "secondary_label"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(10)
        .to_string(index=False)
    )
    churn_by_cat = (
        filtered[filtered["is_churned"] == True]
        .groupby("primary_label")
        .size()
        .reset_index(name="churned_tickets")
        .to_string(index=False)
    )
    sentiment_dist = (
        filtered.groupby("sentiment")
        .size()
        .reset_index(name="count")
        .to_string(index=False)
    )
    return f"""
CURRENT FILTER: Plan={selected_plan}, Primary={selected_primary}, Churn={churn_filter}
TOTAL TICKETS: {total}
CHURN RISK SIGNALS: {int(churn_signals)}
NEGATIVE SENTIMENT TICKETS: {int(negative)}
HIGH URGENCY TICKETS: {int(high_urgency)}

TOP TICKET CATEGORIES:
{top_categories}

TICKETS FROM CHURNED CUSTOMERS BY CATEGORY:
{churn_by_cat}

SENTIMENT DISTRIBUTION:
{sentiment_dist}

PRODUCT GAP NARRATIVE:
{narrative or 'Not available'}
"""

st.divider()

# ── Ticket Explorer ────────────────────────────────────────────────────────────
st.subheader("🗂 Ticket Explorer")
cols_to_show = [
    "ticket_id", "user_id", "plan_type", "primary_label",
    "secondary_label", "tertiary_label", "sentiment", "urgency",
    "status", "is_churned", "one_line_summary", "created_at"
]
available_cols = [c for c in cols_to_show if c in filtered.columns]
st.dataframe(
    filtered[available_cols].sort_values("created_at", ascending=False).head(100),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ── AI Chat Agent ──────────────────────────────────────────────────────────────
st.subheader("💬 Ask the Analytics Agent")
st.caption("Ask questions about your support ticket data in plain English.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("e.g. Which category is most correlated with churn?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("ANTHROPIC_API_KEY not set in .env")
    else:
        client = Anthropic(api_key=api_key)
        system = f"""You are a customer strategy analytics agent for a restaurant SaaS company.
You have access to the following support ticket data:

{build_data_context()}

Answer questions concisely and analytically. Reference specific numbers when possible.
Always tie insights back to customer retention and product improvement opportunities."""

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ]

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=600,
                    system=system,
                    messages=history,
                )
                answer = response.content[0].text
                st.write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})