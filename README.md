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
3. **Evidence-Based Failure Attribution Engine**: Dependency-aware failure propagation logic to identify the earliest likely failure origin or simultaneous **co-originator failures** (e.g. sibling retrievers failing independently). This is attribution, not counterfactual causal inference.
4. **Recommendation Engine**: Generates action-oriented recommendations based on failures and extracted evidence (e.g. increasing retriever chunk overlap, renaming tool args).
5. **Multi-User Support**: Strict SQL-level data boundaries between users, resolved via the `X-API-Key` HTTP header and verified for zero leakage.
6. **Observability Dashboard**: A React frontend containing:
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

### Diagnostic Results
- **Validated benchmark run**: On `examples/fixtures/test_cases.yaml`, the regenerated benchmark report showed **71.1% accuracy**, **67.2% macro-F1**, **74.2% balanced accuracy**, and **68.9% top-k accuracy**.
- **Ablation result**: In the same report, `v2_full` outperformed `v2_no_causal_origin` on accuracy, macro-F1, and balanced accuracy.
- **Who&When adapter**: The repository includes a structured adapter for `Kevin355/Who_and_When`, but no fresh Who&When dataset run was executed in this validation pass, so no numeric result is claimed here.
- **Validation status**: The current codebase passed `51` tests and skipped `2` in the workspace test run.

### Multi-User Scope Constraints
- **In-Scope**: API-key HTTP headers, SHA-256 hashed keys in SQL, and query isolation scoping on traces and session links.
- **Out-of-Scope**: Password authentication, OAuth flow, token expiration, user management UI, and rate limiting per user.

### Known Architectural Limitations
- **Fan-In Chains**: The multi-agent meta-graph assumes single-parent chains at session boundaries.
- **Recommendations Scoping**: Recommendations are computed per-session based on node-level taxonomy only.
- **Framework integration**: Automatic hooks exist for LangGraph/LangChain callbacks; other frameworks require manual SDK tracing wrappers.
- **Benchmark scope**: Reported numbers come from stored fixtures and selected adapter subsets, not from a broad external benchmark suite.
- **Causal scope**: The root-cause engine is evidence-based attribution, not intervention-based causal inference.
- **Calibration scope**: Confidence metrics reflect the calibrated subset when calibration labels are available, so coverage should be checked alongside ECE and Brier score.

---

## Verified Test Artifacts

- **Full test suite**: `51 passed, 2 skipped`
- **Benchmark report**: Regenerated successfully from `examples/fixtures/test_cases.yaml`
- **Calibration workflow**: Code path exists and is covered by tests, but no real calibration dataset was executed in this validation pass
- **Who&When**: Adapter is implemented and test-covered, but no fresh dataset run was executed in this validation pass
