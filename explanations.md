# Thought Process and Design Choices

## 0. Project Architecture

User
 ↓
Chat Interface
 ↓
LLM (Agent / Orchestrator)
 ↓ decides
 ├─ SQL retrieval (SQLite)
 ├─ Financial analysis functions
 ├─ Visualization functions
 ↓
Results (text + dashboard)

-

[User Question]
        ↓
[Intent + Task Planning Node]
        ↓
[SQL Retrieval Node]
        ↓
[Financial Analysis Node]
        ↓
[Visualization Decision Node]
        ↓
[Response Composer]

-

User question
   ↓
Planner (LLM → JSON plan)
   ↓
Plan validation (Pydantic)
   ↓
Data retrieval (SQLite)
   ↓
Financial computations
   ↓
Visualization (if useful)
   ↓
LLM explanation

## 0bis. Project Plan

This plan assumes:

- You already have a SQLite DB
- You want a ChatGPT-like UX
- You want open-source LLMs
- You want deterministic financial analysis

### PHASE 0 — Ground truth (½ day)
🎯 Goal: Make sure your data is not the unknown.

Tasks

1. Inspect your SQLite DB:
	- Tables
	- Columns
	- Date formats
	- Metric names
2. Decide:
	- Canonical metric names (e.g. revenue, ebitda)
	- Time column (date, period_end, etc.)
3. Deliverable: A 1-page schema reference (even a README is fine).

👉 Nothing AI-related yet.

### PHASE 1 — Deterministic backend (1 day)
🎯 Goal: Have a rock-solid analytics engine without any LLM.

Tasks

1. Write SQL access functions
	- No dynamic SQL
	- One function per use case

2. Write financial tools
	- YoY growth
	- Rolling averages
	- Margins

3. Write visualization functions
	- Line chart
	- Bar chart

4. Deliverable: A Python script where:
	- df = load_revenue_timeseries()
	- df2 = yoy_growth(df)
	- plot(df2)


👉 If this is broken, the agent will be broken.

### PHASE 2 — Minimal chat UI (½ day)
🎯 Goal: User can ask a question and see something happen.

Tasks

1. Build a Streamlit chat


2. Hard-code:
	- One query
	- One metric
	- One plot

3. Deliverable
- User types:
	- “Show revenue over time”
- And sees:
	- A chart
	- A placeholder text

👉 Still no LLM.

### PHASE 3 — LLM as planner (1 day)

🎯 Goal: LLM converts questions → structured plan.

Tasks

1. Choose LLM runtime:
	- Ollama + Mistral 7B

2. Write planner system prompt

3. Enforce JSON-only output

4. Validate with Pydantic

5. Deliverable
	- plan = planner("Is revenue growing?")
	- assert plan.metrics == ["revenue"]


👉 The LLM does not touch the DB yet.

### PHASE 4 — Agent controller (1 day)

🎯 Goal: Wire plan → execution.

Tasks

1. Create AgentController

2. Map:

	- plan.metrics → SQL loader
	- plan.analysis → Python functions
	- plan.visualization → plotting

3. Add failure handling:

	- Invalid plan → retry
	- Missing metric → graceful message

4. Deliverable
	- User question → correct data pipeline.

### PHASE 5 — Explanation LLM (½ day)

🎯 Goal: Results explained clearly, not magically.

Tasks

1. Write explainer prompt

2. Pass only computed summaries

3. Forbid new numbers

4. Deliverable
	- Text explanation that matches charts.

### PHASE 6 — UX polish (½ day)
🎯 Goal: Feels like one integrated assistant.

Tasks

1. Streaming responses

2. Loading indicators

3. Clear errors:
	- “This question requires data not available”

4. Deliverable
	- Smooth chat experience.

### PHASE 7 — Guardrails & evaluation (½–1 day)

🎯 Goal: Prevent embarrassing failures.

Tasks

1. Reject:

	- SQL injection attempts
	- Role overrides

2. Log:
	- User question
	- Plan
	- Actions

3. Test with:
	- Ambiguous questions
	- Bad inputs

4. Deliverable
	- Agent behaves predictably.

#### Final MVP checklist (what you can demo)

✅ User types free-form financial questions

✅ Agent chooses metrics and analysis

✅ Data pulled from SQLite

✅ Charts shown when useful

✅ Explanation matches data

✅ No paid APIs


## 1. Database Format Choice: SQLite for storage

We selected SQLite as our primary database because the project data is structured, relational, and requires frequent querying and aggregation. SQLite offers SQL support, indexing, and schema enforcement while remaining lightweight and file-based, making it ideal for a self-contained AI agent. CSV files are used only as an ingestion format, while Polars is employed for high-performance analytical processing after data retrieval.

## 1.1. Why a 3-table structure over a 1-table one?

Question to ChatGPT: **I was wondering, and need you to shine a light on that question, if it wasn't advisable to keep just one big db and each time a query is to be done to just extract it with polars (or to be more precise, let the agent do it). Would it be counterproductive?**

Answer from ChatGPT:

Ah, this is a classic tradeoff in data engineering, and it’s worth really unpacking. I’ll break it down clearly so you can see the pros and cons of “one big table + Polars queries” versus a normalized relational model.

1. One big table + Polars queries (your current setup)
	- Pros:
		- Simplicity: Only one table to maintain — easy to reload from CSV, no foreign keys, no joins.
		- Truthful data: You never risk losing columns or misaligning rows.
		- Flexible: Agent or Python scripts can slice and dice whatever they want without predefined structure.
		- Fast in-memory processing: Polars is very efficient with large datasets; even 28k rows × 85 columns is tiny for Polars.

	- Cons:
		- Redundancy & size: Every query that needs “company info + financial info + ratios” pulls unnecessary columns, which can get heavy as the dataset grows.
		- Query complexity: You may end up writing the same filtering, grouping, and transformations over and over — more chance of mistakes.
		- No enforced constraints: If a “company ID” gets mis-entered, the DB does not prevent inconsistencies because there are no relational constraints.
		- Agent integration: A generative agent will have to load and filter large tables repeatedly — fine for small datasets, but may get slower if you scale to millions of rows.
Derived metrics: Ratios or sector averages would need to be recomputed on-the-fly each time rather than stored for reuse.

2. Normalized relational DB
Split into companies, financials, ratios (and maybe benchmarks later)
Enforce primary/foreign keys
Each table is smaller and more focused

	- Pros:
		- Cleaner queries: “Give me all financials for company X in year Y” → simple JOIN.
		- Consistency: Foreign keys prevent mistakes, no duplicated data.
		- Efficiency: Only pull what you need — smaller tables = faster reads.
		- Extensible: Can add new derived tables or APIs without touching the raw CSV.

	- Cons:
		- Slightly more complex: Need to maintain multiple tables.
		- Initial setup time: Must normalize and migrate the data.

3. Verdict / Engineering intuition
For your current dataset size (~28k rows), keeping one big table is technically fine. Polars can handle this easily in memory, and an agent could work with it.
However, if the project will grow (more years, more companies, multiple CSVs, API enrichment), normalizing the database is better. Why?
It avoids repeated computation (ratios, benchmarks).
It enforces relational integrity, which is crucial for automated tools.
It makes agent reasoning easier because the structure is predictable.

✅ Rule of thumb: Small datasets → one table is okay.
Growing / multi-source datasets → normalize.

💡 In practice for your project:
You can keep the big financial_records table as the raw source, so you have a truthful master copy.
Then build normalized tables (companies, financials, ratios) on top for querying and agent tools.
This gives you the best of both worlds:
Immutable raw data
Efficient and structured working tables

## Step 2 — Build modular tools for the LLM

- Database tools: read/query financials, ratios, and companies
- API tools: fetch benchmarking data from Yahoo Finance, OECD, etc.
- Processing tools: compute statistics, detect anomalies, calculate additional ratios
- Visualization tools: static/interactive plots
- Report generation tools: dashboards, PDFs, summaries

## Step 3 — Integrate AI insights

- Use GPT or HuggingFace models to interpret financial data
- Generate human-like, consultant-style explanations
- Benchmark against industry/sector averages

## Step 4 — Build agent interface

- Optional: Streamlit/Dash for uploading files and viewing analysis
- Connect all tools for automated financial analysis
