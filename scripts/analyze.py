"""
analyze.py

Loads support_tickets.csv into DuckDB and uses the Claude API to:
  1. Validate / re-confirm taxonomy labels on each ticket
  2. Generate a strategic "Product Gap Narrative" summary across all tickets

The results are written to the DuckDB warehouse for downstream dbt modeling
and Streamlit dashboard consumption.

Usage:
    python scripts/analyze.py
"""

import os
import json
import time
import duckdb
import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
DB_PATH = "data/transcript_analysis.duckdb"
CSV_PATH = "data/support_tickets.csv"
BATCH_SIZE = 20  # tickets per Claude call to stay well within token limits

# Hardcoded taxonomy — the source of truth for all labeling
TAXONOMY = {
    "Billing": [
        "Duplicate Charge", "Failed Payment", "Refund Request", "Invoice Question"
    ],
    "Online Ordering": [
        "Page Not Loading", "Menu Not Updating", "Order Not Received", "Ordering Disabled"
    ],
    "Marketing / SEO": [
        "Google Listing Issue", "Website Not Updating", "SEO Performance", "Campaign Not Running"
    ],
    "Product / Feature": [
        "Feature Not Working", "Feature Request", "Performance Issue", "Integration Issue"
    ],
    "Account Access": [
        "Login Issue", "Permissions Error", "Account Locked", "Account Setup"
    ],
    "Onboarding": [
        "Setup Confusion", "Integration Help", "Training Request", "Go-Live Issue"
    ],
}

SENTIMENT_OPTIONS = ["Positive", "Neutral", "Frustrated", "Angry"]


def load_tickets(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    print(f"📥 Loaded {len(df)} tickets from {csv_path}")
    return df


def build_label_prompt(tickets: list[dict]) -> str:
    taxonomy_str = json.dumps(TAXONOMY, indent=2)
    tickets_str = "\n".join(
        f"- ticket_id: {t['ticket_id']} | body: {t['ticket_body']}"
        for t in tickets
    )
    return f"""You are a customer support analyst. Your job is to validate taxonomy labels for support tickets at a restaurant SaaS company.

TAXONOMY (use only these values):
{taxonomy_str}

SENTIMENT OPTIONS: {SENTIMENT_OPTIONS}

For each ticket below, return ONLY a JSON array (no markdown, no preamble) where each object has:
- ticket_id
- primary_label (must match a key in the taxonomy)
- secondary_label (must match a value under that primary)
- sentiment (must be one of the sentiment options)
- urgency (integer 1-3: 1=low, 2=medium, 3=high)
- one_line_summary (10 words or fewer describing the issue)

TICKETS:
{tickets_str}

Respond with only the JSON array."""


def validate_labels_with_claude(df: pd.DataFrame, client: Anthropic) -> pd.DataFrame:
    """Send tickets to Claude in batches to validate/enrich labels."""
    records = df.to_dict(orient="records")
    enriched = []

    total_batches = (len(records) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\n🤖 Sending {len(records)} tickets to Claude in {total_batches} batches...")

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        print(f"  Batch {batch_num}/{total_batches} ({len(batch)} tickets)...")

        prompt = build_label_prompt(batch)

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown fences if present
            raw = raw.replace("```json", "").replace("```", "").strip()
            validated = json.loads(raw)
            enriched.extend(validated)
        except Exception as e:
            print(f"  ⚠️  Batch {batch_num} failed: {e}. Using original labels.")
            for t in batch:
                enriched.append({
                    "ticket_id": t["ticket_id"],
                    "primary_label": t["primary_label"],
                    "secondary_label": t["secondary_label"],
                    "sentiment": t["sentiment"],
                    "urgency": 2,
                    "one_line_summary": "Label validation unavailable",
                })

        time.sleep(0.3)  # be polite to the API

    enriched_df = pd.DataFrame(enriched)
    # Merge validated labels back onto original dataframe
    df = df.drop(columns=["primary_label", "secondary_label", "sentiment"], errors="ignore")
    df = df.merge(enriched_df, on="ticket_id", how="left")
    print(f"✅ Claude validation complete — {len(enriched_df)} tickets enriched")
    return df


def generate_product_gap_narrative(df: pd.DataFrame, client: Anthropic) -> str:
    """Ask Claude to write a strategic product gap narrative from aggregated ticket data."""
    summary = (
        df.groupby(["primary_label", "secondary_label"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(20)
        .to_string(index=False)
    )

    churn_breakdown = (
        df[df["is_churned"] == True]
        .groupby("primary_label")
        .size()
        .reset_index(name="churned_tickets")
        .sort_values("churned_tickets", ascending=False)
        .to_string(index=False)
    )

    prompt = f"""You are a Head of Customer Strategy at a restaurant SaaS company. 
You have just reviewed this month's support ticket analysis.

TOP TICKET CATEGORIES (by volume):
{summary}

TICKET VOLUME FROM CHURNED CUSTOMERS (by category):
{churn_breakdown}

Write a concise strategic narrative (4-6 sentences) that:
1. Identifies the top 2-3 product gaps driving the most friction
2. Calls out which issues correlate most with churn risk
3. Recommends the highest-priority intervention for the product and CS teams

Write in the voice of a senior operator presenting to a VP. Be direct and specific."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    narrative = response.content[0].text.strip()
    print("\n📝 Product gap narrative generated")
    return narrative


def write_to_duckdb(df: pd.DataFrame, narrative: str, db_path: str):
    """Write enriched tickets and narrative to DuckDB."""
    con = duckdb.connect(db_path)

    # Raw enriched tickets table
    con.execute("DROP TABLE IF EXISTS raw_support_tickets")
    con.execute("CREATE TABLE raw_support_tickets AS SELECT * FROM df")

    # Narrative table
    con.execute("DROP TABLE IF EXISTS product_gap_narrative")
    con.execute("""
        CREATE TABLE product_gap_narrative (
            generated_at TIMESTAMP,
            narrative TEXT
        )
    """)
    con.execute(
        "INSERT INTO product_gap_narrative VALUES (CURRENT_TIMESTAMP, ?)",
        [narrative]
    )

    ticket_count = con.execute("SELECT COUNT(*) FROM raw_support_tickets").fetchone()[0]
    print(f"\n💾 Wrote {ticket_count} tickets to {db_path}")
    con.close()


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")

    client = Anthropic(api_key=api_key)

    df = load_tickets(CSV_PATH)
    df = validate_labels_with_claude(df, client)
    narrative = generate_product_gap_narrative(df, client)
    write_to_duckdb(df, narrative, DB_PATH)

    print("\n🎉 Analysis complete. Run `dbt run` to build the marts layer.")
    print(f"\n--- PRODUCT GAP NARRATIVE ---\n{narrative}\n")


if __name__ == "__main__":
    main()
