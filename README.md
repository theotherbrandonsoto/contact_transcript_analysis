# 🎫 Transcript Analysis

A production-style support ticket intelligence pipeline — demonstrating automated data ingestion, Claude-powered taxonomy labeling, a multi-layer dbt pipeline, a DuckDB warehouse, and a live Streamlit dashboard with an AI analytics agent.

**Author:** theotherbrandonsoto | [GitHub](https://github.com/theotherbrandonsoto) | [LinkedIn](https://www.linkedin.com/in/hirebrandonsoto/)

> **Part of a connected portfolio.** The customer universe in this project (user IDs, plan types, churn status) is drawn from the same data model as [metrics-store](https://github.com/theotherbrandonsoto/metrics-store), simulating what a real multi-system analytics environment looks like.


---

## 🧠 What is Transcript Analysis?

Support tickets are one of the richest — and most underused — signals in a SaaS business. Every ticket is a customer telling you exactly where your product is failing them.

This project builds a lightweight version of what tools like unitQ do at scale: ingest raw support contacts, apply a structured taxonomy using an AI classifier, and surface the patterns that matter most to product and customer success teams.

The result is a system that turns a pile of support tickets into a prioritized product gap report — automatically.

---

## 🏗️ Architecture

```
generate_tickets.py   (synthetic ticket generation, linked to metrics-store customers)
        ↓
data/support_tickets.csv   (raw ticket data)
        ↓
analyze.py            (Claude API — taxonomy validation + product gap narrative)
        ↓
data/transcript_analysis.duckdb   (raw_support_tickets + product_gap_narrative)
        ↓
dbt staging layer     stg_support_tickets     — clean types, validate labels
dbt marts layer       fct_support_tickets     — derived churn risk + sentiment flags
dbt insights layer    support_insights        — aggregated metrics by category & month
        ↓
Streamlit             dashboard.py            — live dashboard + AI chat agent
```

---

## 🏷️ Taxonomy Design

Tickets are classified across three levels. The taxonomy is hardcoded — ensuring consistency across runs and reflecting how real CS ops teams actually work.

| Primary | Secondary Examples | Tertiary Examples |
|---|---|---|
| **Billing** | Duplicate Charge, Failed Payment, Refund Request | Subscription Upgrade Flow, Payment Method Update |
| **Online Ordering** | Page Not Loading, Menu Not Updating, Order Not Received | Checkout Flow, POS Sync |
| **Marketing / SEO** | Google Listing Issue, Website Not Updating | GMB Sync, SEO Ranking Drop |
| **Product / Feature** | Feature Not Working, Performance Issue, Integration Issue | Dashboard, Notifications |
| **Account Access** | Login Issue, Permissions Error, Account Locked | SSO Failure, 2FA Problem |
| **Onboarding** | Setup Confusion, Integration Help, Go-Live Issue | POS Connection, Domain Setup |

---

## 📐 dbt Layer Design

| Layer | Model | Purpose |
|---|---|---|
| Staging | `stg_support_tickets` | Cleans types, validates accepted label values |
| Marts | `fct_support_tickets` | One row per ticket with churn risk + sentiment flags |
| Insights | `support_insights` | Aggregated metrics by category, plan type, and month |

---

## 🤖 Claude Integration

Claude is used in two places:

**1. Taxonomy Validation (`analyze.py`)**
Each ticket body is sent to Claude in batches. Claude confirms or corrects the primary/secondary label, assigns sentiment, scores urgency (1–3), and writes a one-line summary. The taxonomy is passed as a strict constraint so Claude cannot freelance new categories.

**2. Product Gap Narrative (`analyze.py`)**
After labeling, Claude receives the aggregated ticket volume by category alongside the churn breakdown. It generates a 4–6 sentence strategic narrative identifying the top product gaps and highest-priority interventions — written in the voice of a senior operator presenting to a VP.

**3. Analytics Agent (`dashboard.py`)**
The Streamlit dashboard includes a natural language chat agent with full awareness of the current data context. Example questions:
- *"Which category has the highest churn signal rate?"*
- *"What should the product team prioritize this quarter?"*
- *"Are Basic plan customers more frustrated than Premium?"*
- *"Which issues are most likely to cause a customer to cancel?"*

---

## 📊 Dashboard Features

- **KPI cards** — total tickets, churn risk signals, negative sentiment %, high urgency, escalations
- **Volume by primary category** — horizontal bar chart
- **Sentiment distribution** — donut chart
- **Churn risk by category** — identifies which product areas drive the most at-risk behavior
- **Monthly trend** — line chart by category over time
- **Secondary breakdown** — grouped bar chart drilling into sub-categories
- **AI product gap narrative** — Claude's strategic summary, always current
- **Ticket explorer** — filterable table of all raw tickets

---

## 🛠️ Tech Stack

| Tool | Role |
|---|---|
| **Python** | Ticket generation, Claude labeling pipeline, dashboard |
| **Claude API** | Taxonomy validation, narrative generation, chat agent |
| **dbt Core** | Three-layer data transformation pipeline |
| **DuckDB** | Local analytical warehouse |
| **Streamlit** | Business intelligence dashboard |
| **Plotly** | Interactive charts |
| **pandas** | Data manipulation |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- An [Anthropic account](https://console.anthropic.com) with an API key

### 1. Clone the repo

```bash
git clone https://github.com/theotherbrandonsoto/transcript-analysis.git
cd transcript-analysis
```

### 2. Set up virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Add credentials

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

### 4. Generate ticket data

```bash
python scripts/generate_tickets.py
```

### 5. Run Claude analysis pipeline

```bash
python scripts/analyze.py
```

This will validate all ticket labels and generate the product gap narrative. Takes ~2–3 minutes for 660 tickets.

### 6. Run the dbt pipeline

```bash
cd dbt_project
dbt run
dbt test
cd ..
```

### 7. Launch the dashboard

```bash
streamlit run scripts/dashboard.py
```

Open `http://localhost:8501` in your browser.

---

## 📁 Project Structure

```
transcript-analysis/
├── data/
│   ├── support_tickets.csv          ← Generated ticket data (gitignored)
│   └── transcript_analysis.duckdb  ← DuckDB warehouse (gitignored)
├── dbt_project/
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_support_tickets.sql
│   │   │   └── schema.yml
│   │   ├── marts/
│   │   │   ├── fct_support_tickets.sql
│   │   │   └── schema.yml
│   │   └── insights/
│   │       ├── support_insights.sql
│   │       └── schema.yml
│   ├── profiles.yml
│   └── dbt_project.yml
├── scripts/
│   ├── generate_tickets.py          ← Synthetic ticket generation
│   ├── analyze.py                   ← Claude labeling + narrative pipeline
│   └── dashboard.py                 ← Streamlit dashboard + AI agent
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🧪 Data Quality Tests

dbt tests run automatically across the pipeline:

- **Uniqueness** — `ticket_id` is unique across all models
- **Not null** — key columns are never empty
- **Accepted values** — `primary_label` and `sentiment` only contain valid taxonomy values

Run at any time:

```bash
cd dbt_project
dbt test
```

---

## 💡 Why This Project?

Most analytics projects stop at a dashboard. This one is designed to reflect what a real customer strategy function actually needs:

- **Taxonomy as code** — business classification logic lives in version-controlled Python, not in a spreadsheet or a vendor tool
- **AI-augmented, not AI-dependent** — Claude validates and enriches labels, but the taxonomy and data model are fully human-designed and auditable
- **Retention-first framing** — every metric is connected back to churn risk, not just ticket volume
- **Actionable output** — the product gap narrative is something a VP of CS or CPO would actually read and act on
- **Connected data model** — customer IDs link directly to the [metrics-store](https://github.com/theotherbrandonsoto/metrics-store) project, demonstrating how real multi-system analytics environments work

---

*Synthetic ticket data generated programmatically. Customer universe drawn from the metrics-store project data model.*