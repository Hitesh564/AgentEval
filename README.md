# AgentEval

AgentEval is an evaluation and failure-attribution platform for AI agent workflows. It captures traces, scores node-level behavior, propagates failures through the execution graph, and surfaces evidence for where a workflow broke and why that failure spread.

It is designed to work in two modes:

- Local development with SQLite
- Hosted deployment with PostgreSQL or Supabase behind a FastAPI backend

## Overview

```mermaid
flowchart LR
    A["Agent / LangGraph workflow"] --> B["AgentEval SDK"]
    B --> C["Local mode: SQLite + local dashboard"]
    B --> D["Hosted mode: HTTPS ingestion API"]
    D --> E["FastAPI backend"]
    E --> F["PostgreSQL / Supabase"]
    F --> G["Dashboard"]
```

In hosted mode, the client never needs direct database credentials. The backend authenticates API keys, assigns the user identity, and writes traces server-side.

## What AgentEval Does

- Captures agent traces across single-agent and multi-agent workflows
- Scores node behavior with measurable health signals
- Propagates failure evidence across the execution graph
- Ranks likely root-cause nodes with supporting evidence
- Stores traces, cache results, and session links in SQL-backed storage
- Serves a dashboard for sessions, trace detail, benchmark comparisons, and causal chains

## Repository Layout

```text
agenteval/
|-- sdk/         # Storage, tracing, hosted client, schema, DB config
|-- eval/        # Metric evaluation, caching, and health scoring
|-- root_cause/  # Failure propagation and attribution
|-- recommend/   # Remediation suggestions
|-- benchmark/   # Benchmark CLI and report generation
|-- adapters/    # Dataset adapters such as Who&When
`-- server/      # FastAPI backend
```

## Installation

### 1. Install dependencies

```powershell
pip install -r requirements.txt
pip install -e .
```

### 2. Configure environment

Copy the template and set your values:

```powershell
copy .env.example .env
```

Important variables:

- `AGENTEVAL_DATABASE_URL`
- `AGENTEVAL_CORS_ORIGINS`
- `AGENTEVAL_API_URL`
- `AGENTEVAL_API_KEY`
- `AGENTEVAL_ADMIN_BOOTSTRAP_KEY`
- `GEMINI_API_KEY` or `OPENAI_API_KEY`
- `AGENTEVAL_MODEL`
- `AGENTEVAL_MAX_COST_USD_PER_RUN`
- `AGENTEVAL_MAX_TOKENS_PER_CALL`

## Database

AgentEval keeps the storage model simple:

- Local development: SQLite
- Production: PostgreSQL or Supabase
- ORM: SQLAlchemy
- Migrations: Alembic

### Local development

```powershell
AGENTEVAL_DATABASE_URL=sqlite:///./agenteval.db
alembic upgrade head
```

### Production

```powershell
AGENTEVAL_DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DATABASE
alembic upgrade head
```

If you are using an older `postgres://` URL, the application normalizes it internally to PostgreSQL.

## API Keys

AgentEval uses hashed API keys for authenticated ingestion.

### Create a key locally

```powershell
python scripts/generate_api_key.py --user-id alice --database-url sqlite:///./agenteval.db
```

### Create a key against PostgreSQL / Supabase

```powershell
python scripts/generate_api_key.py --user-id alice --database-url postgresql+psycopg2://USER:PASSWORD@HOST:5432/DATABASE
```

The plaintext key is shown once and only the SHA-256 hash is stored in the database.

### Hosted bootstrap

The hosted backend also exposes a bootstrap endpoint for creating API keys against the configured production database. The bootstrap token is controlled by `AGENTEVAL_ADMIN_BOOTSTRAP_KEY`.

## SDK Usage

### Local tracing

```python
from agenteval import AgentEvalCallbackHandler

handler = AgentEvalCallbackHandler(
    session_id="session_123",
    db_path="sqlite:///./agenteval.db",
)
```

### Hosted tracing

```python
from agenteval import AgentEvalCallbackHandler

handler = AgentEvalCallbackHandler(
    session_id="session_123",
    api_url="https://your-agent-eval-api.example.com",
    api_key="your-agent-eval-api-key",
)
```

### Hosted HTTP client

```python
from agenteval import AgentEvalClient

client = AgentEvalClient(
    api_url="https://your-agent-eval-api.example.com",
    api_key="your-agent-eval-api-key",
)
```

The client sends completed trace nodes to `POST /api/v1/traces` and can also batch nodes through `POST /api/v1/traces/batch`.

## Example Workflow

### Run a local pipeline

```powershell
python examples/simple_rag_agent.py --calibration
```

### Run the hosted LangGraph example

```powershell
python examples/langgraph_hosted_example.py
```

### Evaluate the Who&When adapter

```powershell
python -m agenteval.adapters.who_when_adapter --cases 15 --mode replay
```

## Backend Server

Start the backend locally:

```powershell
python -m uvicorn agenteval.server.main:app --port 8000
```

For Railway or a similar platform:

```powershell
alembic upgrade head
uvicorn agenteval.server.main:app --host 0.0.0.0 --port $PORT
```

Production environment variables should include:

- `AGENTEVAL_DATABASE_URL`
- `AGENTEVAL_CORS_ORIGINS`
- `AGENTEVAL_MODEL`
- `GEMINI_API_KEY` or `OPENAI_API_KEY`
- `AGENTEVAL_API_URL`
- `AGENTEVAL_ADMIN_BOOTSTRAP_KEY`
- `AGENTEVAL_MAX_COST_USD_PER_RUN`
- `AGENTEVAL_MAX_TOKENS_PER_CALL`

## Dashboard

```powershell
cd dashboard
npm install
npm run dev -- --port 5173
```

For deployment, set the frontend API base URL with `VITE_API_BASE_URL`. Do not hardcode localhost into production builds.

Example:

```text
VITE_API_BASE_URL=https://your-agent-eval-api.example.com
```

## CORS

Production CORS is origin-based and driven by `AGENTEVAL_CORS_ORIGINS`.

Example:

```text
AGENTEVAL_CORS_ORIGINS=https://your-dashboard.vercel.app
```

For local development, the template includes:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

## Validation

Current benchmark snapshots captured in this repository:

### Internal benchmark

- Accuracy: `73.3%`
- Macro-F1: `69.8%`
- Balanced accuracy: `76.2%`

### Full official Who&When

- Agent accuracy: `40.8%`
- Step accuracy: `14.7%`
- Exact match: `14.7%`
- Macro-F1: `0.353`
- Balanced accuracy: `0.351`
- Top-k accuracy: `40.8%`

## Security Notes

- Database credentials stay server-side
- Clients authenticate with API keys
- API keys are stored hashed, not in plaintext
- Production CORS is restricted to configured origins
- `.env` files and local databases are ignored by git
- `.env.example` contains placeholders only

## Limitations

AgentEval is intentionally conservative:

- It depends on the quality of the trace that the agent emits
- Root-cause attribution is evidence-based, not a guarantee of ground truth
- Offline benchmark performance can differ from real-world workflows
- Hosted deployments still need correct environment variables and database migrations

## License

See [`LICENSE`](LICENSE).
