# AgentEval — Product Requirements Document

## Vision

AgentEval is an open-source SDK and dashboard that helps AI engineers
understand *why* their AI agents fail — not just that they failed.
Rather than stopping at execution traces and surface-level metrics, it
performs evidence-based diagnosis: identifying the specific node, the
specific evidence, and the specific confidence behind a failure, so
teams can fix the actual cause instead of guessing from a transcript.

## Problem Statement

Current observability tools — LangSmith, Langfuse, Phoenix — capture
execution traces and compute metrics well. But when a metric drops or a
conversation fails, they still leave the developer to manually inspect
the trace, read through prompts and outputs node by node, and guess at
which part of the pipeline actually caused the failure. That manual
diagnosis step doesn't scale as agents get more complex, and it's the
step none of the existing tools automate. AgentEval is built specifically
to automate that diagnosis — turning "this conversation scored low" into
"this node caused it, here's the evidence, and here's what to change."

## Target Users

- **AI engineers** building and maintaining production agent systems
- **LLM engineers** iterating on prompts, retrieval, and tool design
- **ML engineers** who need measurable, reproducible evaluation of agent
  behavior rather than anecdotal spot-checks
- **Startups building AI agents** who need to debug reliability issues
  without a dedicated observability team
- **Researchers** evaluating agent workflows who need a standardized way
  to compare approaches and attribute failures

## 1. What this is

AgentEval is a library + dashboard that plugs into an existing AI agent
(built with LangGraph, LangChain, or similar) and answers one question
developers currently answer by manually reading transcripts:

> **"Why did my agent fail, which node caused it, and what should I change?"**

It is not a chatbot, not a new agent framework, and not a general-purpose
observability platform. It is diagnostic infrastructure that sits on top
of an agent that already exists.

## 2. Positioning — why this exists when LangSmith/Langfuse/Phoenix exist

Tools like LangSmith, Langfuse, and Arize Phoenix solve **trace capture
and browsing at production scale**. That is a solved problem built by
funded teams, and this project does not attempt to compete with it.

What none of them do well: **causal root-cause reasoning across a
multi-agent pipeline.** They tell you a metric dropped. They do not tell
you which upstream node caused it, with evidence and a confidence level,
propagated through a graph of agent nodes, with a concrete recommendation
attached.

**That gap is the entire reason this project exists.** Every feature
below should be justified against this positioning. If a feature doesn't
serve root-cause reasoning, benchmarking, or the minimum dashboard needed
to demo it, it does not belong in this build.

Practical implication: the trace SDK should be able to **ingest
OpenTelemetry/OpenInference-format traces** (the format LangSmith/Phoenix
already emit) in addition to its own native instrumentation. This lets
AgentEval sit on top of traces a team already has, rather than forcing
them to switch tracing tools — a much stronger integration story than a
competing, incompatible SDK.

## 3. Explicit non-goals (do not build these — v1 scope discipline)

- Dataset builder / human-review-and-approve workflow for training data
- QLoRA / DPO fine-tuning pipeline
- CI/CD (GitHub Actions) integration — mention as future work only
- Plugin adapters for CrewAI, AutoGen, LlamaIndex — LangGraph/LangChain
  only for v1
- Five benchmark packs — ship **one** (RAG benchmark) well
- Real-time production monitoring, alerting, log search across
  thousands of live sessions — this is what LangSmith/Phoenix already do

If a coding agent building this finds itself starting any of the above,
stop and re-read the positioning section.

## 4. Architecture overview

```
Developer's agent (LangGraph / LangChain)
            │
            ▼
      Trace SDK  ─────────────► (optional) OTel/OpenInference importer
            │
            ▼
   Evaluation Engine
   ├─ Instruction following
   ├─ Tool-calling accuracy
   ├─ Groundedness (claim-level)
   ├─ JSON validity
   ├─ Cost / token usage
   └─ Latency
            │
            ▼
   Root Cause Engine
   ├─ Evidence collection (per-node measurable signals)
   ├─ Failure taxonomy (tagging)
   ├─ Confidence estimation (calibrated, not guessed)
   └─ Causal chain / health propagation across the node graph
            │
            ▼
   Recommendation Engine
   └─ Evidence-driven suggestions (narrow, pattern-based v1)
            │
            ▼
   Benchmark & Regression Engine
   └─ Version A vs B comparison, per-metric deltas, overall confidence
            │
            ▼
   Dashboard (thin observability layer)
   ├─ Conversation list (pass/fail, score, failure tag)
   ├─ Trace detail view (node sequence + health scores = causal chain UI)
   └─ Benchmark/regression report page
```

## 5. Developer workflow

The end-to-end journey a developer goes through when adopting AgentEval:

1. **Install SDK** — add the AgentEval package to an existing project.
2. **Instrument agent** — register the callback handler against the
   existing LangGraph/LangChain agent (or wrap calls manually, per 6.1).
3. **Run agent** — the developer runs their agent as they normally would,
   in testing or production.
4. **Automatic trace capture** — every node, tool call, and retrieval is
   logged with no additional developer effort.
5. **Evaluation** — traces are scored against the v1 metric set (6.2).
6. **Root cause analysis** — failing traces are diagnosed down to a
   specific node, with evidence and a calibrated confidence (6.3).
7. **Recommendations** — evidence-driven, targeted suggestions are
   generated for each diagnosed failure (6.4).
8. **Benchmark comparison** — once a fix is made, the developer reruns
   the benchmark to see a per-metric regression report before shipping
   the change (6.5).

## 6. Component specs

### 6.1 Trace SDK

**Goal:** capture everything needed for evaluation with near-zero
integration cost.

- Primary path: a callback handler registered with LangGraph/LangChain's
  existing callback system (`on_tool_start`, `on_tool_end`,
  `on_llm_start`, `on_llm_end`, node-transition events). This captures
  tool calls, arguments, return values, latencies, and node sequence
  automatically — the developer does not manually declare their tools.
- Secondary path: a manual logging API (`trace()` context manager +
  `log_tool_calls()` / `log_retrieval()`) for hand-rolled agents with no
  framework callback system.
- Tertiary path (stretch): an importer that accepts OpenTelemetry /
  OpenInference-formatted traces so teams already using LangSmith/Phoenix
  can point AgentEval at existing trace exports instead of
  re-instrumenting.
- Data captured per node: node name, inputs, outputs, tool calls +
  args/results, retrieved documents (with similarity scores if
  available), latency, token counts, timestamps.
- Storage: traces persist to a local store (SQLite for v1 is fine) keyed
  by session ID, with a schema that the Evaluation Engine consumes
  directly — see Appendix A for the trace schema.

### 6.2 Evaluation Engine

Runs per-trace, either synchronously after a run or in batch over a set
of session IDs.

Metrics (v1 set — do not expand without reason):
- **Instruction following** — LLM-judge score against the original
  instruction/system prompt.
- **Tool-calling accuracy** — did the agent call the correct tool with
  correct arguments, checked against either a labeled expected-tool set
  (benchmark mode) or a heuristic plausibility check (production mode).
- **Groundedness** — decompose the final answer into individual claims,
  check each claim against retrieved evidence, report supported/total as
  a real fraction. This must be claim-level, not a single holistic LLM
  score — the fraction is what feeds the Explainability requirement in
  6.3.
- **JSON validity** — schema/parse check where structured output is
  expected. Deterministic, not LLM-judged.
- **Cost / token usage** — pulled directly from trace data, no
  estimation needed.
- **Latency** — per node and total, pulled directly from trace data.

### 6.3 Root Cause Engine

This is the differentiator. Three sub-requirements, all mandatory:

**(a) Evidence collection — must use measurable signals, not vibes.**
For each node, collect a real, computable number wherever one exists:
- Retriever: actual cosine similarity between query and retrieved
  chunks (not an LLM guess).
- Groundedness: claim-support ratio from 6.2, not a holistic score.
- Tool selection: compare chosen tool's embedding/description similarity
  to the query against alternative tools' similarity, to detect
  ambiguous tool descriptions.
- Only fall back to an LLM-judge score where no deterministic signal
  exists (e.g., "was the plan logically sound").

**(b) Confidence estimation — must be calibrated, not asserted.**
Do not ship a bare "84% confidence" number without backing it. Two
acceptable approaches, pick one for v1:
1. Derive confidence from the measurable evidence itself (e.g., how far
   the retriever's similarity score sits below a learned/observed
   healthy baseline) — a mathematical function of real signal, not a
   model's self-report.
2. If using an LLM-judge confidence score, validate it against a
   hand-labeled holdout set (minimum ~100-150 examples) and report the
   actual calibration ("when the model said >80% confident, it was
   right X% of the time") in the project writeup. Ship the honest
   calibration number, even if it's mediocre — that is more credible
   than an unvalidated confidence figure.

**(c) Causal chain / health propagation across the graph.**
- Each node gets a health score derived from its own evidence (6.3a).
- Propagation logic must handle the general case: agent graphs branch,
  loop, and run nodes in parallel — not just a straight line. The
  attribution question is: "did this node fail independently, or did it
  inherit a failure from an upstream node?" A defensible v1 heuristic:
  a node's *adjusted* health score = its raw health score, penalized if
  and only if its raw inputs (from upstream nodes) already scored below
  a threshold — this at least distinguishes "this node made things worse
  on its own" from "this node was already fed bad input." A more
  rigorous version (stretch goal, not required for v1) tests
  counterfactuals: would fixing the upstream node's output plausibly fix
  this node's output.
- Root cause = the earliest node in the chain whose *raw* (non-inherited)
  health score drops below threshold.

### 6.4 Recommendation Engine

Keep this narrow and evidence-driven, not an open-ended suggestion
generator.

- Input: the specific evidence collected in 6.3a (not just the failure
  tag).
- Output: a small, targeted set of suggestions tied to what the evidence
  actually shows. Examples:
  - Low similarity across all retrieved docs → suggest top-k increase,
    embedding model change, or chunk-overlap increase.
  - High similarity on docs but claim-support still low → suggest the
    generator prompt is ignoring context, not a retrieval problem.
  - Tool ambiguity detected (chosen tool and an alternative have similar
    description-embedding scores) → suggest renaming tools or adding
    usage examples, not "fix retrieval."
- Each recommendation carries an expected-impact label (high/medium/low)
  based on how large the gap between observed and healthy-baseline
  evidence is.
- Do not implement this as a static `if failure_type == X: suggest Y`
  switch statement — the mapping should be a function of the evidence
  values collected, so two different retrieval failures with different
  underlying evidence can get different suggestions.

### 6.5 Benchmark & Regression Engine

- One benchmark pack for v1: **RAG benchmark** (a fixed set of
  query/expected-answer/expected-evidence tuples for evaluating a
  retrieval-augmented agent). Ship this one well; do not build the other
  four packs mentioned in early planning.
- CLI entry point: `agenteval compare <version_a> <version_b>` — no
  CI/CD wiring for v1, just a command that runs both versions through
  the benchmark and evaluation engine and prints/renders a report.
- Report must show **per-metric deltas**, not just an aggregate score:
  instruction-following, hallucination rate, tool-calling accuracy,
  retrieval quality, latency — each with a directional delta — plus an
  overall verdict and a confidence figure (calibrated per 6.3b, not
  invented).

### 6.6 Dashboard (observability layer)

Deliberately thin — two to three screens, not a LangSmith clone.

- **Screen 1 — Conversation list.** Every traced session, with overall
  score, pass/fail, and failure tag (if failed) at a glance. Filterable
  by tag and date.
- **Screen 2 — Trace detail / causal chain view.** Click into any
  session: node sequence top to bottom (or as a graph, for branching
  agents), each node showing its health score, its raw evidence, and
  whether it's flagged as root cause. This is the causal-chain concept
  rendered as a real UI — it should visually make clear which node is
  the origin of a failure and how it propagated.
- **Screen 3 — Benchmark/regression report.** Version A vs B, per-metric
  delta table, overall verdict, confidence.
- Explicitly out of scope for the dashboard: live/streaming monitoring,
  alerting, cross-session log search at scale. If a user wants that,
  point them at LangSmith/Langfuse — say so in the product's own docs,
  it reinforces the positioning in section 2.

## 7. Failure taxonomy

A standardized set of root-cause categories, used consistently across
the Root Cause Engine, the dashboard, benchmarking, and the
Recommendation Engine, so a failure tagged in one place means the same
thing everywhere in the platform:

- **Retrieval failure** — retrieved documents have low relevance to the
  query (measured via similarity score, per 6.3a).
- **Tool selection failure** — the wrong tool was chosen, or tool
  descriptions were ambiguous enough to cause misselection.
- **Planning failure** — the planner produced a flawed or incomplete
  plan that downstream nodes could not recover from.
- **Reasoning failure** — the agent had correct inputs but drew an
  incorrect conclusion or took an illogical step.
- **Grounding failure** — the final answer contains claims unsupported
  by retrieved evidence (claim-support ratio below threshold, per 6.2).
- **Output formatting failure** — structurally invalid output (e.g.
  malformed JSON) where a valid schema was expected.
- **Latency failure** — a node or the overall run exceeded an acceptable
  time budget, independent of correctness.

Every root-cause determination in section 6.3 must resolve to one of
these categories, and every recommendation in 6.4 is keyed off this same
taxonomy — this is what keeps the dashboard, benchmark reports, and
recommendations consistent with each other.

## 8. Data schema (Appendix A)

Minimum fields per trace, per node — a coding agent should use this as
the baseline for the trace store's schema, extending only if a specific
metric in 6.2 requires a field not listed here:

```
session_id: string
node_id: string
node_type: string          # planner | retriever | generator | critic | tool | custom
timestamp_start: datetime
timestamp_end: datetime
inputs: json
outputs: json
tool_name: string | null
tool_args: json | null
tool_result: json | null
retrieved_docs: [{ text, similarity_score }] | null
tokens_in: int
tokens_out: int
cost_usd: float
parent_node_ids: [string]   # supports branching/parallel graphs, not just a line
```

## 9. Build phases (in order — do not reorder)

1. Trace SDK (LangGraph/LangChain callback path) + trace schema/storage.
2. Evaluation Engine — all six v1 metrics, with groundedness built
   claim-level from the start (it's a dependency for explainability and
   root cause evidence, not an add-on).
3. Root Cause Engine — evidence collection first, then health scores,
   then causal-chain propagation, then confidence calibration.
4. Recommendation Engine — narrow, evidence-driven.
5. Benchmark & Regression Engine — RAG benchmark pack + `compare` CLI.
6. Dashboard — three screens, reusing data already produced by steps 2-5.
7. (Stretch, only if time remains) OpenTelemetry/OpenInference trace
   importer; confidence-calibration validation report against a
   hand-labeled holdout.

## 10. Success criteria for the write-up / demo

- A real end-to-end demo: an agent with an injected/observed failure,
  showing conversation list → drill into failure → causal chain with
  root cause and confidence → recommendation → fix applied → regression
  report showing the specific metrics that improved.
- An honest calibration statement for whatever confidence method was
  used (per 6.3b) — this is a stronger signal in an interview than a
  number with no validation behind it.
- A clear one-paragraph positioning statement (see section 2) ready to
  say out loud: this is not a LangSmith competitor, it is a causal
  diagnosis layer that can sit on top of existing traces.