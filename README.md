# AgentEval

AgentEval is an evaluation and failure-attribution system for AI agent pipelines. It instruments agent traces, scores node-level behavior, propagates failures through the execution graph, and surfaces evidence for where a workflow broke and why that failure likely spread.

The project is designed as a practical observability layer for agent systems rather than a causal-reasoning research prototype. It supports local development with SQLite, production deployments with PostgreSQL or Supabase, and a dashboard for inspecting traces, regressions, and root-cause evidence.

---

## What It Does

- Captures agent traces across single-agent and multi-agent workflows
- Scores node behavior using a small set of measurable health signals
- Propagates failure evidence across the execution graph
- Ranks likely root-cause nodes with supporting evidence
- Stores traces, cache results, and session links in SQL-backed storage
- Exposes a dashboard for reviewing sessions and benchmark results

---

## Core Architecture

```text
Client / Agent SDK
    -> Tracer and callbacks
    -> SQL storage layer
    -> Evaluation engine
    -> Root-cause engine
    -> Recommendation engine
    -> Dashboard API
    -> React dashboard
```

### Main Components

- `agenteval/sdk/`
  - Tracing helpers, SQL storage, schema, and database configuration
- `agenteval/eval/`
  - Metric evaluation, confidence calibration, and health scoring
- `agenteval/root_cause/`
  - Failure propagation and root-cause ranking
- `agenteval/recommend/`
  - Action-oriented recommendations from detected failures
- `agenteval/benchmark/`
  - Benchmark runner, metrics, and markdown report generation
- `agenteval/adapters/`
  - Dataset adapters such as Who&When
- `agenteval/server/`
  - FastAPI backend for the dashboard
- `dashboard/`
  - React frontend for trace and benchmark review

---

## Evaluation Model

AgentEval currently focuses on measurable signals that are easy to audit:

- Instruction following
- Retrieval and groundedness evidence
- Tool selection and tool-argument quality
- JSON / schema validity
- Latency
- Cost and token usage
- Semantic response quality

The root-cause engine uses these signals to compute node health, adjust health through graph dependencies, and rank candidate failure origins. The system also carries deterministic node-health evidence so the final attribution can be inspected without hiding the underlying measurements.

---

## Repository Layout

```text
AgentEval/
|-- agenteval/          # Core Python package
|   |-- sdk/            # Storage, tracing, schema, and DB config
|   |-- eval/           # Metric evaluators and calibration
|   |-- root_cause/     # Failure propagation and attribution
|   |-- recommend/      # Recovery and remediation suggestions
|   |-- benchmark/      # Benchmark CLI and report generation
|   |-- adapters/       # Dataset adapters
|   `-- server/         # FastAPI backend
|-- dashboard/          # React dashboard
|-- examples/           # Demo pipelines and fixtures
|-- scripts/            # Utility scripts such as API key generation
|-- tests/              # Pytest regression suite
|-- artifacts/          # Saved benchmark and validation outputs
|-- alembic/            # Database migrations
`-- .env.example        # Environment template
```

---

## Quick Start

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment

Copy `.env.example` to `.env` and set the required values:

```powershell
copy .env.example .env
```

Recommended environment variables:

- `AGENTEVAL_DATABASE_URL`
- `GEMINI_API_KEY` or `OPENAI_API_KEY`
- `AGENTEVAL_MODEL`
- `AGENTEVAL_MAX_COST_USD_PER_RUN`
- `AGENTEVAL_MAX_TOKENS_PER_CALL`

### 3. Set Up the Database

AgentEval uses SQLAlchemy with SQLite for local development and PostgreSQL for production.

- Local default: `sqlite:///./agenteval.db`
- Supabase / PostgreSQL: `postgresql+psycopg2://...`

Initialize the schema with Alembic:

```powershell
alembic upgrade head
```

For a fresh local setup, SQLite works out of the box. For production, always set `AGENTEVAL_DATABASE_URL` before starting the app.

### 4. Generate a Dashboard API Key

Create a user key for dashboard access:

```powershell
python scripts/generate_api_key.py --user-id alice --db-path agenteval.db
```

The script prints the plaintext API key once. Store it securely and paste it into the dashboard when prompted.

### 5. Run a Pipeline Demo

Single-agent example:

```powershell
python examples/simple_rag_agent.py --calibration
```

Multi-agent example:

```powershell
python examples/multi_agent_pipeline.py --calibration
```

Who&When adapter:

```powershell
python agenteval/adapters/who_when_adapter.py --cases 15 --mode replay
```

### 6. Start the Backend

```powershell
python -m uvicorn agenteval.server.main:app --port 8000
```

For deployment on a platform such as Railway or Render, set `AGENTEVAL_DATABASE_URL`, run `alembic upgrade head`, and expose the app on the platform port.

### 7. Start the Dashboard

```powershell
cd dashboard
npm install
npm run dev -- --port 5173
```

Open `http://localhost:5173` and sign in with the generated API key.

---

## Benchmarking

Run the benchmark CLI against stored traces and fixtures:

```powershell
agenteval benchmark --fixtures examples/fixtures/test_cases.yaml --output reports/benchmark_report.md
```

The benchmark report includes:

- Accuracy
- Macro-F1
- Balanced accuracy
- Bootstrap confidence intervals
- Ablation comparisons
- Calibration summaries

---

## Validated Results

The repository currently includes validated artifacts from the local workspace:

- **Internal benchmark** on `examples/fixtures/test_cases.yaml`
  - `73.3%` accuracy
  - `69.8%` macro-F1
  - `76.2%` balanced accuracy
  - bootstrap confidence intervals included in the saved report

- **Audited 15-case Who&When subset**
  - `60.0%` agent-level accuracy on the 15-case Who&When evaluation
  - `6.7%` step accuracy
  - `6.7%` exact match
  - `0.402` macro-F1
  - `0.422` balanced accuracy
  - `60.0%` top-k agent accuracy

- **Full official Who&When validation**
  - `184` total cases
  - `40.8%` agent accuracy
  - `14.7%` step accuracy
  - `14.7%` exact match
  - `0.353` macro-F1
  - `0.351` balanced accuracy
  - `40.8%` top-k agent accuracy

- **Current test status**
  - `68 passed, 2 skipped`

Saved reports and artifacts live under `artifacts/` and `reports/`.

---

## Known Limits

AgentEval is intentionally practical, but it still has a few scope boundaries:

- Root-cause attribution is evidence-based ranking, not intervention-based causal inference
- The multi-agent graph model is strongest when the trace structure is explicit and well-formed
- Recommendations are session-local and derived from observed node failures
- Confidence calibration is useful for ranking support, but it is not a guarantee of correctness
- External benchmarks can drift from the internal validation set, so results should be interpreted in context

---

## Notes for Production

- Use PostgreSQL or Supabase for deployed environments
- Keep `AGENTEVAL_DATABASE_URL` set in production
- Run `alembic upgrade head` before deploying a new database
- Keep the dashboard API key separate from LLM provider keys
- Respect the cost guards if live LLM evaluation is enabled

---

## Files Worth Checking

- `agenteval/sdk/database.py`
- `agenteval/sdk/storage.py`
- `agenteval/eval/metrics.py`
- `agenteval/root_cause/engine.py`
- `agenteval/benchmark/cli.py`
- `agenteval/adapters/who_when_adapter.py`
- `tests/`

