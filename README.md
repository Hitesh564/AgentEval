# AgentEval

AgentEval is an open-source evaluation and evidence-based failure-attribution engine for AI agents. It combines trace instrumentation, node-level evaluation, and cross-session diagnosis to show *where* a pipeline failed and *why* that failure likely propagated. In the validated repository workflow, AgentEval supports controlled benchmark evaluation, baseline comparison, ablation analysis, calibration tooling, and an external Who&When adapter.

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
- **Internal benchmark**: On the controlled `examples/fixtures/test_cases.yaml` benchmark, the regenerated report showed **71.1% accuracy** with **95% bootstrap CI: 58.9% to 83.4%**, **67.2% macro-F1** with **95% CI: 54.1% to 82.0%**, and **74.2% balanced accuracy** with **95% CI: 60.8% to 83.5%**.
- **Ablation result**: In the same report, `v2_full` outperformed `v2_no_causal_origin` on accuracy, macro-F1, and balanced accuracy.
- **External Who&When validation**: The adapter was executed on **15 cases** from `Kevin355/Who_and_When` and produced **20.0% agent accuracy**, **0.0% step accuracy**, **6.7% exact match**, **0.143 macro-F1**, **0.111 balanced accuracy**, and **20.0% top-k agent accuracy**.
- **Calibration validation**: A benchmark-derived calibration dataset with **90 examples** was exported from stored traces. Threshold calibration on a **63/27** calibration/holdout split produced **threshold = 1.0**, **holdout F1 = 0.800**, **holdout ROC-AUC = 0.898**, and **holdout PR-AUC = 0.982**. Confidence calibration remains pending because that exported dataset does not include labeled confidence targets.
- **Validation status**: The current codebase passed **53** tests and skipped **2** in the workspace test run.

### Multi-User Scope Constraints
- **In-Scope**: API-key HTTP headers, SHA-256 hashed keys in SQL, and query isolation scoping on traces and session links.
- **Out-of-Scope**: Password authentication, OAuth flow, token expiration, user management UI, and rate limiting per user.

### Known Architectural Limitations
- **Fan-In Chains**: The multi-agent meta-graph assumes single-parent chains at session boundaries.
- **Recommendations Scoping**: Recommendations are computed per-session based on node-level taxonomy only.
- **Framework integration**: Automatic hooks exist for LangGraph/LangChain callbacks; other frameworks require manual SDK tracing wrappers.
- **Benchmark scope**: Reported numbers come from stored fixtures and selected adapter subsets, not from a broad external benchmark suite.
- **Causal scope**: The root-cause engine is evidence-based attribution, not intervention-based causal inference.
- **Calibration scope**: Threshold calibration is validated on a benchmark-derived split, but confidence calibration is still pending because the exported dataset has no labeled confidence targets.

---

## Verified Test Artifacts

- **Full test suite**: `53 passed, 2 skipped`
- **Benchmark report**: Regenerated successfully from `examples/fixtures/test_cases.yaml`
- **Calibration workflow**: Threshold calibration was executed on a benchmark-derived labeled export and holdout metrics were reported
- **Who&When**: The adapter was executed on 15 cases and produced real external-validation metrics
