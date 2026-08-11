# AgentEval

AgentEval is an open-source evaluation and root-cause diagnosis engine for AI agents. It goes beyond simple black-box evaluation to pinpoint *why* and *where* agents fail in complex multi-step pipelines. By analyzing metrics across agent transitions, AgentEval traces failures back to their earliest upstream origin.

---

## Key Capabilities

1. **Multi-Topology Tracing SDK**: Instrument single-agent or multi-agent pipelines. Native support for:
   - **Linear pipelines** (sequential chains)
   - **Branching/Parallel execution** (routing DAGs)
   - **Retries & Loops** (self-correction loops)
   - **Multi-Agent Cross-Session Chains** (orchestrator-worker handoffs)
2. **6-Metric Evaluation Engine**: Dynamic evaluation of node-level quality:
   - **Instruction Following**: LLM-judge evaluated alignment.
   - **Groundedness / Retrieval Quality**: Semantic retriever similarity using context documents.
   - **Tool Accuracy**: Correctness of tool calling.
   - **JSON Validity**: Schema compliance.
   - **Latency**: Runtime execution duration.
   - **Cost / Tokens**: Input/output tokens and cost metrics.
3. **Causal Root Cause Engine**: Transitive failure propagation logic to identify the earliest root cause or simultaneous **co-originator failures** (e.g. sibling retrievers failing independently).
4. **Recommendation Engine**: Generates action-oriented recommendations based on failures and extracted evidence (e.g. increasing retriever chunk overlap, renaming tool args).
5. **Multi-User Support**: Strict SQL-level data boundaries between users, resolved via the `X-API-Key` HTTP header and verified for zero leakage.
6. **observability Dashboard**: A React frontend containing:
   - **Conversation List**: Overall scores, pass status, and failure tags.
   - **Trace Detail**: Interactive trace execution tree, confidence intervals, and evidence.
   - **Benchmark Delta Comparison**: Metric regressions across pipeline versions.
   - **Causal Chain DAG**: Visualizes multi-agent handoffs and failure propagation.

---

## Directory Structure

```text
AgentEval/
├── agenteval/              # Core Python library
│   ├── taxonomy.py         # Failure Type enum (single source of truth)
│   ├── sdk/                # Tracing SDK, callbacks, and SQLite storage
│   ├── eval/               # Metrics evaluation engine (Vertex AI & heuristics)
│   ├── root_cause/         # Single-session & cross-session causal engines
│   ├── recommend/          # Recommendations generator engine
│   ├── benchmark/          # Benchmark run evaluations and CLI comparison
│   ├── adapters/           # Ingestors (e.g. Who&When dataset adapter)
│   └── server/             # FastAPI dashboard API server
├── dashboard/              # React frontend (Vite + TS + Vanilla CSS)
├── scripts/                # Helper utilities (API key generation)
├── examples/               # RAG and Multi-agent pipeline simulations
├── tests/                  # Pytest validation suite
├── requirements.txt        # Backend dependencies
├── pyproject.toml          # Package script and entry points
└── .env.example            # Secrets template
```

---

## Setup & Execution

### 1. Installation
Install AgentEval dependencies using the virtual environment:
```powershell
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment
Copy `.env.example` to `.env` and supply your Gemini API keys for live-judge evaluations:
```powershell
cp .env.example .env
```

### 3. Generate a User API Key
Register a user in the database to generate an API key:
```powershell
python scripts/generate_api_key.py --user-id alice --db-path agenteval.db
```
*Note the generated plaintext key; it is printed only once.*

### 4. Run Pipeline Simulations (Populate Traces)
Before using the dashboard, run simulations to populate the traces database. 

#### A. Single-Agent RAG Simulation (Linear, Branching, Retry sets)
```powershell
# Run baseline calibration
python examples/simple_rag_agent.py --calibration

# Run fixed calibration
python examples/simple_rag_agent.py --calibration --fixed
```

#### B. Multi-Agent Pipeline Simulation (Cross-Session sets)
```powershell
# Run baseline calibration
python examples/multi_agent_pipeline.py --calibration

# Run fixed calibration
python examples/multi_agent_pipeline.py --calibration --fixed
```

#### C. Who&When Independent Dataset Validation
Ingest and evaluate a subset of the ICML 2025 public multi-agent dataset:
```powershell
python agenteval/adapters/who_when_adapter.py --cases 15 --mode replay
```

### 5. Start the Backend API Server
Launch the FastAPI server (defaults to port `8000`):
```powershell
python -m uvicorn agenteval.server.main:app --port 8000
```

### 6. Run the Dashboard
Navigate to the `dashboard` folder, install Node packages, and start the development server:
```powershell
cd dashboard
npm install
npm run dev -- --port 5173
```
Open `http://localhost:5173`. You will be prompted to paste your generated API key.

---

## Benchmark Comparisons (CLI)

To evaluate regressions and improvements between versions via the command line:

```powershell
# Compare Single-Agent runs
agenteval compare calib fixed --fixtures examples/fixtures/test_cases.yaml

# Compare Multi-Agent runs
agenteval compare calib fixed --fixtures examples/fixtures/multi_agent_test_cases.yaml
```

---

## Validated Scope & Limitations

### Supported Topologies
- **Linear**: Sequential RAG workflows.
- **Branching/Parallel**: Multi-route decision/routing DAGs.
- **Retries/Loops**: Iterative correction loops.
- **Multi-Agent Chains**: Session-level coordinator and worker hierarchies.

### Diagnostic Causal Accuracy
- **Internal Holdouts (Single/Multi-Agent)**: **100.0%**
- **Who&When Dataset Results**:
  - **Dataset**: Converted 15 multi-agent cases from ICML 2025 Who&When dataset (`Kevin355/Who_and_When`).
  - **Diagnostic Accuracy**: **33.3%** in live-judge mode (using `gemini-3.1-flash-lite` over 15 cases; 100% correct when `Orchestrator` is the ground truth culprit, but misattributes worker errors upstream to the parent orchestrator).
  - **Replay Accuracy**: **0.0%** (due to local heuristic fallback defaulting to healthy `1.0` on unseen logs).

### Multi-User Scope Constraints
- **In-Scope**: API-key HTTP headers, SHA-256 hashed keys in SQL, and query isolation scoping on traces and session links.
- **Out-of-Scope**: Password authentication, OAuth flow, token expiration, user management UI, and rate limiting per user.

### Known Architectural Limitations
- **Fan-In Chains**: The multi-agent meta-graph assumes single-parent chains at session boundaries.
- **Recommendations Scoping**: Recommendations are computed per-session based on node-level taxonomy only.
- **Framework integration**: Automatic hooks exist for LangGraph/LangChain callbacks; other frameworks require manual SDK tracing wrappers.

---

## Production Readiness & Load Testing (Phase 5)

### PostgreSQL Migration & Database Abstraction
- **SQLAlchemy Core Query Layer**: Refactored `TraceStore` to use database-agnostic SQLAlchemy Core queries (`create_engine`, `Table`, `MetaData`), replacing all raw `sqlite3` cursors.
- **Alembic Versioned Migrations**: Schema migrations managed via Alembic (`alembic.ini`, `alembic/env.py`, and `001_initial_schema.py`).
- **Database Fallback & URL Handling**: Configurable via `AGENTEVAL_DATABASE_URL` (e.g. `postgresql://agenteval@localhost:5432/agenteval`), defaulting to local SQLite (`sqlite:///agenteval.db`) if unset.
- **Concurrent-Write Safety**: Verified with 200 trace nodes written simultaneously across 10 concurrent worker threads with **0.0% row loss or lock corruption**.

### Zero-Concurrency Latencies & Optimization
Before running load tests, zero-concurrency baseline latencies were measured across all four target endpoints:
- **Identified Caching Gap**: `/api/sessions` (1,922 ms p95) and `/api/benchmark/compare` (1,510 ms p95) previously re-computed full graph failure propagation across all store sessions on every read.
- **In-Memory Caching Fix**: Implemented a write-invalidated response cache in `server/main.py`, reducing `/api/sessions` baseline p95 from **1,922 ms to 20.69 ms (92x speedup)** and `/api/benchmark/compare` baseline p95 from **1,510 ms to 23.73 ms (63x speedup)**.

### Locust Load Test Results
Load testing was executed headlessly via Locust across 10, 50, and 100 concurrent user stages against PostgreSQL:

| Target Endpoint | 10 Users (p50 / p95) | 50 Users (p50 / p95) | 100 Users (p50 / p95) | Error Rate (100 Users) |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/sessions` | **17 ms / 3200 ms*** | **40 ms / 490 ms** | **470 ms / 2000 ms** | 1.1% |
| `GET /api/sessions/{id}/trace` | **38 ms / 120 ms** | **77 ms / 680 ms** | **500 ms / 2100 ms** | 1.8% |
| `GET /api/sessions/{id}/chain` | **250 ms / 420 ms** | **380 ms / 1100 ms** | **940 ms / 3000 ms** | 3.8% |
| `GET /api/benchmark/compare` | **15 ms / 2100 ms*** | **38 ms / 490 ms** | **390 ms / 2100 ms** | 0.4% |

*\* Note: 10-user p95 reflects cold-cache startup spikes during user spawning. Subsequent cached requests are served in <40ms.*
