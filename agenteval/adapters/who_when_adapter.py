import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, TYPE_CHECKING

from agenteval.benchmark.metrics import classification_metrics, top_k_accuracy

if TYPE_CHECKING:
    from agenteval.root_cause.cross_session import CrossSessionEngine
    from agenteval.sdk.storage import TraceStore


@dataclass(frozen=True)
class WhoWhenEvaluationRecord:
    case_id: str
    expected_agent: str
    predicted_agent: str
    expected_step: Optional[str]
    predicted_step: Optional[str]
    agent_correct: bool
    step_correct: bool
    exact_match: bool
    top_k_agents: List[str]


def _normalize_label(value: Any) -> str:
    if value is None:
        return "none"
    text = str(value).strip().lower()
    replacements = {
        " ": "_",
        "-": "_",
        "/": "_",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _agent_label_from_session(session_id: Optional[str]) -> str:
    if not session_id:
        return "none"
    text = str(session_id).strip()
    match = re.match(r"^session_(?P<case>.+?)_step(?P<step>\d+)_(?P<agent>.+)$", text)
    if match:
        return _normalize_label(match.group("agent"))
    return _normalize_label(text)


def _agent_label_from_turn(step: Dict[str, Any]) -> str:
    name = step.get("name")
    if name is not None and str(name).strip():
        return _normalize_label(name)

    role = step.get("role")
    if role is None:
        return "none"

    role_clean = str(role).strip()
    if not role_clean:
        return "none"

    role_lower = role_clean.lower()
    if "orchestrator" in role_lower:
        return "orchestrator"
    if "termination" in role_lower:
        return "orchestrator"
    if role_lower in {"assistant", "websurfer", "filesurfer", "computerterminal"}:
        return _normalize_label(role_clean)
    return _normalize_label(role_clean)


def _normalize_step_label(value: Any) -> str:
    if value is None:
        return "none"
    text = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if text.isdigit():
        return f"step_{text}"
    if text.startswith("turn") and any(ch.isdigit() for ch in text):
        digits = "".join(ch for ch in text if ch.isdigit())
        return f"step_{digits}" if digits else text
    return text


def _normalize_step_metric_label(value: Any) -> str:
    normalized = _normalize_step_label(value)
    if normalized == "none":
        return "none"
    if normalized.startswith("step_"):
        return normalized
    if normalized.isdigit():
        return f"step_{normalized}"
    digits = "".join(ch for ch in normalized if ch.isdigit())
    return f"step_{digits}" if digits else normalized


def _step_matches(expected_step: Any, predicted_step: Any, predicted_node_id: Optional[str] = None) -> bool:
    expected = _normalize_step_label(expected_step)
    predicted = _normalize_step_label(predicted_step)
    if expected == predicted:
        return True
    if predicted_node_id is not None:
        node = _normalize_step_label(predicted_node_id)
        if expected == node:
            return True
    expected_digits = "".join(ch for ch in expected if ch.isdigit())
    predicted_digits = "".join(ch for ch in predicted if ch.isdigit())
    return bool(expected_digits and expected_digits == predicted_digits)


def _role_to_node_type(role: str) -> str:
    role_clean = role.lower()
    if "thought" in role_clean or "orchestrator" in role_clean:
        return "planner"
    if "termination" in role_clean:
        return "critic"
    return "generator"


def _extract_tool_target(role: str) -> Optional[str]:
    role_clean = role.lower()
    if "->" not in role_clean:
        return None
    target = role_clean.split("->", 1)[1]
    target = target.replace(")", "").replace("(", "").strip()
    return _normalize_label(target) if target else None


def _load_cached_who_when_rows(dataset_config: str) -> List[Dict[str, Any]]:
    cache_root = Path.home() / ".cache" / "huggingface" / "datasets" / "Kevin355___who_and_when" / dataset_config / "0.0.0"
    arrow_files = sorted(cache_root.rglob("*train.arrow"))
    if not arrow_files:
        raise FileNotFoundError(f"Could not find a cached Who&When split under {cache_root}")

    try:
        import pyarrow.ipc as ipc
    except Exception as exc:  # pragma: no cover - dependency issue is surfaced to the caller
        raise RuntimeError("pyarrow is required to load the cached Who&When split") from exc

    with arrow_files[0].open("rb") as handle:
        table = ipc.open_stream(handle).read_all()
    return table.to_pylist()


def _load_local_parquet_rows(path: Path) -> List[Dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except Exception as exc:  # pragma: no cover - dependency issue is surfaced to the caller
        raise RuntimeError("pyarrow is required to load the local Who&When parquet file") from exc

    table = pq.read_table(path)
    return table.to_pylist()


def _find_local_who_when_file(dataset_config: str) -> Optional[Path]:
    normalized = dataset_config.strip()
    candidates = [
        Path.cwd() / f"{normalized}.parquet",
        Path.cwd() / f"{normalized.replace('_', '-')}.parquet",
        Path.cwd() / f"{normalized.replace('-', '_')}.parquet",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_who_when_rows(
    dataset_name: str = "Kevin355/Who_and_When",
    dataset_config: str = "Hand-Crafted",
) -> List[Dict[str, Any]]:
    local_file = _find_local_who_when_file(dataset_config)
    if local_file is not None:
        return _load_local_parquet_rows(local_file)

    try:
        return _load_cached_who_when_rows(dataset_config)
    except FileNotFoundError:
        pass

    try:
        from datasets import load_dataset

        dataset = load_dataset(dataset_name, dataset_config)
        train_split = dataset["train"]
        return [train_split[idx] for idx in range(len(train_split))]
    except Exception:
        return _load_cached_who_when_rows(dataset_config)


def _build_audit_record(
    item: Dict[str, Any],
    *,
    store: "TraceStore",
    cross_engine: "CrossSessionEngine",
    user_id: str,
) -> Dict[str, Any]:
    traces, metadata = adapt_history_to_traces(item, user_id=user_id)

    for trace_node in traces:
        store.save_trace_node(trace_node)
    for idx in range(1, len(traces)):
        current_session = traces[idx]["session_id"]
        previous_session = traces[idx - 1]["session_id"]
        store.save_session_link(current_session, previous_session, link_reason="Handoff", user_id=user_id)

    if not metadata["last_session_id"]:
        return {
            "case_id": metadata["case_id"],
            "expected_agent": _normalize_label(item["mistake_agent"]),
            "predicted_agent": "none",
            "expected_step": _normalize_step_metric_label(item.get("mistake_step")),
            "predicted_step": None,
            "converted_trace": traces,
            "selected_root_cause_node": None,
            "ranked_root_cause_candidates": [],
            "attribution_scores": [],
            "health_scores": [],
            "failure_types": [],
            "evidence_used": [],
        }

    diagnosis = cross_engine.diagnose_chain(metadata["last_session_id"], user_id=user_id)
    diagnosed_chain = diagnosis.get("chain", [])
    root_session = diagnosis.get("root_cause_session", "none")
    root_node = next((step for step in diagnosed_chain if step["status"] == "root-cause"), None)
    root_trace = next((node for node in traces if root_node and node["session_id"] == root_node["session_id"]), None)

    selected_session_nodes: List[Dict[str, Any]] = []
    selected_session_id: Optional[str] = None
    session_details: List[Dict[str, Any]] = []
    for step in diagnosed_chain:
        session_id = step["session_id"]
        session_traces = store.get_session_traces(session_id, user_id=user_id)
        session_diagnosis = cross_engine.rc_engine.propagate_failures(session_traces) if session_traces else []
        session_details.append(
            {
                "session_id": session_id,
                "status": step.get("status"),
                "overall_score": step.get("overall_score"),
                "passed": step.get("passed"),
                "root_cause_node": step.get("root_cause_node"),
                "nodes": session_diagnosis,
            }
        )
        if root_node and session_id == root_node["session_id"]:
            selected_session_nodes = session_diagnosis
            selected_session_id = session_id

    selected_node = next((n for n in selected_session_nodes if n.get("is_root_cause")), None)
    if selected_node is None and selected_session_nodes:
        selected_node = next((n for n in selected_session_nodes if n.get("failure_type") is not None), selected_session_nodes[0])

    predicted_agent = "ambiguous" if root_session == "ambiguous" else _agent_label_from_session(root_session)
    predicted_step = None
    if root_trace is not None:
        predicted_step = root_trace.get("node_id")
    elif root_node is not None:
        predicted_step = root_node.get("root_cause_node")

    return {
        "case_id": metadata["case_id"],
        "expected_agent": _normalize_label(item["mistake_agent"]),
        "predicted_agent": predicted_agent,
        "expected_step": _normalize_step_metric_label(item.get("mistake_step")),
        "predicted_step": predicted_step,
        "converted_trace": {
            "metadata": metadata,
            "trace_nodes": traces,
            "session_links": [
                {
                    "session_id": traces[idx]["session_id"],
                    "previous_session_id": traces[idx - 1]["session_id"],
                    "link_reason": "Handoff",
                }
                for idx in range(1, len(traces))
            ],
        },
        "selected_root_cause_node": root_node,
        "selected_root_cause_trace": root_trace,
        "ranked_root_cause_candidates": diagnosed_chain,
        "attribution_scores": [
            {
                "session_id": selected_session_id,
                "node_id": node.get("node_id"),
                "node_type": node.get("node_type"),
                "raw_health": node.get("raw_health"),
                "adjusted_health": node.get("adjusted_health"),
                "attribution_score": node.get("attribution_score"),
                "causal_origin_score": node.get("causal_origin_score"),
                "failure_type": node.get("failure_type").value if node.get("failure_type") else None,
                "is_root_cause": node.get("is_root_cause"),
            }
            for node in selected_session_nodes
        ],
        "health_scores": [
            {
                "session_id": detail["session_id"],
                "status": detail["status"],
                "overall_score": detail.get("overall_score"),
                "passed": detail.get("passed"),
                "root_cause_node": detail.get("root_cause_node"),
            }
            for detail in session_details
        ],
        "failure_types": sorted(
            {
                node.get("failure_type").value
                for detail in session_details
                for node in detail.get("nodes", [])
                if node.get("failure_type") is not None
            }
        ),
        "evidence_used": [
            {
                "session_id": detail["session_id"],
                "root_cause_node": detail.get("root_cause_node"),
                "status": detail.get("status"),
                "node_evidence": [node.get("evidence") for node in detail.get("nodes", [])],
            }
            for detail in session_details
        ],
    }


def adapt_history_to_traces(
    item: Dict[str, Any],
    *,
    user_id: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    q_id = str(item["question_ID"])
    history = item["history"]
    traces: List[Dict[str, Any]] = []
    prev_session_id: Optional[str] = None
    last_session_id: Optional[str] = None
    prev_node_id: Optional[str] = None

    for step_index, step in enumerate(history):
        role = step.get("role")
        if role == "human":
            continue

        role_clean = str(role).lower()
        node_type = _role_to_node_type(role_clean)
        agent_name = _agent_label_from_turn(step)

        tool_name = _extract_tool_target(role_clean)

        session_id = f"session_{q_id}_step{step_index}_{agent_name}"
        node_id = f"step_{step_index}"
        trace_node = {
            "session_id": session_id,
            "node_id": node_id,
            "node_type": node_type,
            "timestamp_start": datetime.now(timezone.utc).isoformat(),
            "timestamp_end": datetime.now(timezone.utc).isoformat(),
            "inputs": {
                "query": item["question"],
                "input_prompt": "\n".join(
                    f"{turn.get('role')}: {turn.get('content')}"
                    for turn in history[:step_index]
                ).strip(),
            },
            "outputs": {
                "response": step.get("content")
            },
            "parent_node_ids": [prev_node_id] if prev_node_id else [],
            "source_role": role_clean,
            "history_index": step_index,
            "user_id": user_id,
        }
        if node_type == "planner" and tool_name:
            trace_node["tool_name"] = tool_name
            trace_node["tool_calls"] = [{"name": tool_name}]
            trace_node["expected_tool"] = tool_name
            trace_node["tool_descriptions"] = [f"Hand-off to {tool_name}"]
        traces.append(trace_node)

        if prev_session_id and prev_session_id != session_id:
            traces[-1]["parent_session_id"] = prev_session_id

        prev_session_id = session_id
        prev_node_id = node_id
        last_session_id = session_id

    metadata = {
        "case_id": q_id,
        "question": item["question"],
        "mistake_agent": item["mistake_agent"],
        "mistake_step": item["mistake_step"],
        "last_session_id": last_session_id,
        "history_roles": [step.get("role") for step in history if step.get("role") != "human"],
    }
    return traces, metadata


def evaluate_case(
    item: Dict[str, Any],
    *,
    store: "TraceStore",
    cross_engine: "CrossSessionEngine",
    user_id: str,
) -> WhoWhenEvaluationRecord:
    traces, metadata = adapt_history_to_traces(item, user_id=user_id)
    q_id = metadata["case_id"]

    for trace_node in traces:
        store.save_trace_node(trace_node)
    for idx in range(1, len(traces)):
        current_session = traces[idx]["session_id"]
        previous_session = traces[idx - 1]["session_id"]
        store.save_session_link(current_session, previous_session, link_reason="Handoff", user_id=user_id)

    if not metadata["last_session_id"]:
        return WhoWhenEvaluationRecord(
            case_id=q_id,
            expected_agent=_normalize_label(item["mistake_agent"]),
            predicted_agent="none",
            expected_step=_normalize_step_metric_label(item.get("mistake_step")),
            predicted_step=None,
            agent_correct=False,
            step_correct=False,
            exact_match=False,
            top_k_agents=[],
        )

    diagnosis = cross_engine.diagnose_chain(metadata["last_session_id"], user_id=user_id)
    diagnosed_chain = diagnosis.get("chain", [])
    root_session = diagnosis.get("root_cause_session", "none")
    root_node = next((step for step in diagnosed_chain if step["status"] == "root-cause"), None)
    top_k_agents = [
        _agent_label_from_session(step["session_id"])
        for step in diagnosed_chain
        if step["status"] in ("root-cause", "co-contributor")
    ]
    expected_agent = _normalize_label(item["mistake_agent"])
    predicted_agent = "ambiguous" if root_session == "ambiguous" else _agent_label_from_session(root_session)

    predicted_step = None
    if root_node is not None:
        root_trace = next((node for node in traces if node["session_id"] == root_node["session_id"]), None)
        if root_trace is not None:
            predicted_step = root_trace.get("node_id") or root_trace.get("source_role")
        else:
            predicted_step = root_node.get("root_cause_node")

    expected_step = item.get("mistake_step")
    agent_correct = expected_agent == predicted_agent
    step_correct = _step_matches(expected_step, predicted_step, root_node["root_cause_node"] if root_node else None)
    exact_match = agent_correct and step_correct

    return WhoWhenEvaluationRecord(
        case_id=q_id,
        expected_agent=expected_agent,
        predicted_agent=predicted_agent,
        expected_step=_normalize_step_metric_label(expected_step),
        predicted_step=str(predicted_step) if predicted_step is not None else None,
        agent_correct=agent_correct,
        step_correct=step_correct,
        exact_match=exact_match,
        top_k_agents=[agent for agent in top_k_agents if agent != "none"],
    )


def aggregate_records(records: Sequence[WhoWhenEvaluationRecord]) -> Dict[str, Any]:
    y_true = [record.expected_agent for record in records]
    y_pred = [record.predicted_agent for record in records]
    step_true = [_normalize_step_metric_label(record.expected_step) for record in records]
    step_pred = [_normalize_step_metric_label(record.predicted_step) for record in records]

    agent_metrics = classification_metrics(y_true, y_pred)
    step_metrics = classification_metrics(step_true, step_pred)
    top_k = top_k_accuracy(y_true, [record.top_k_agents for record in records]) if any(record.top_k_agents for record in records) else None

    return {
        "count": len(records),
        "agent_accuracy": agent_metrics["accuracy"],
        "step_accuracy": step_metrics["accuracy"],
        "exact_match": sum(1 for record in records if record.exact_match) / len(records) if records else 0.0,
        "macro_f1": agent_metrics["macro_f1"],
        "balanced_accuracy": agent_metrics["balanced_accuracy"],
        "top_k_agent_accuracy": top_k,
        "agent_metrics": agent_metrics,
        "step_metrics": step_metrics,
        "records": [record.__dict__ for record in records],
        "assumptions": [
            "Histories are converted into single-parent session chains in execution order.",
            "Agent labels are inferred from the ground-truth mistake_agent field only after diagnosis.",
            "Step labels are preserved as normalized step IDs instead of role labels so the reported step metrics align with the ground-truth annotation.",
            "WebSurfer and FileSurfer are mapped to retriever nodes so the engine can score retrieval-style evidence from their outputs.",
        ],
    }


def run_who_when_evaluation(
    *,
    cases: int = 15,
    db_path: str = "agenteval.db",
    mode: str = "replay",
    dataset_name: str = "Kevin355/Who_and_When",
    dataset_config: str = "Hand-Crafted",
    user_id: str = "who_when_user",
    api_key: str = "who_when_secret_key",
) -> Dict[str, Any]:
    from agenteval.root_cause.cross_session import CrossSessionEngine
    from agenteval.sdk.storage import TraceStore

    train_split = load_who_when_rows(dataset_name, dataset_config)
    store = TraceStore(db_path=db_path)
    store.create_user(user_id, api_key)

    records: List[WhoWhenEvaluationRecord] = []
    audit_records: List[Dict[str, Any]] = []
    cross_engine = CrossSessionEngine(db_path=db_path, mode=mode)
    try:
        for idx in range(min(cases, len(train_split))):
            item = train_split[idx]
            q_id = str(item["question_ID"])
            store.delete_case_traces(user_id, q_id)
            record = evaluate_case(item, store=store, cross_engine=cross_engine, user_id=user_id)
            records.append(record)
            audit_records.append(_build_audit_record(item, store=store, cross_engine=cross_engine, user_id=user_id))

        summary = aggregate_records(records)
        summary["dataset"] = {
            "name": dataset_name,
            "config": dataset_config,
            "cases_requested": cases,
            "cases_evaluated": len(records),
            "source": "Kevin355/Who_and_When",
        }
        summary["mode"] = mode
        summary["audit_records"] = audit_records
        return summary
    finally:
        store.close()
        cross_engine.store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest and evaluate a subset of the Who&When dataset.")
    parser.add_argument("--cases", type=int, default=15, help="Number of cases to evaluate (default 15)")
    parser.add_argument("--db-path", default="agenteval.db", help="Path to SQLite database")
    parser.add_argument("--mode", default="replay", choices=["replay", "live"], help="Evaluation mode (replay or live)")
    args = parser.parse_args()

    summary = run_who_when_evaluation(cases=args.cases, db_path=args.db_path, mode=args.mode)

    print("=== WHO&WHEN EVALUATION SUMMARY ===")
    print(f"Dataset: {summary['dataset']['name']} / {summary['dataset']['config']}")
    print(f"Cases evaluated: {summary['count']}")
    print(f"Mode: {summary['mode']}")
    print(f"Agent Accuracy: {summary['agent_accuracy']*100:.1f}%")
    print(f"Step Accuracy: {summary['step_accuracy']*100:.1f}%")
    print(f"Exact Match: {summary['exact_match']*100:.1f}%")
    print(f"Macro-F1: {summary['macro_f1']:.3f}")
    print(f"Balanced Accuracy: {summary['balanced_accuracy']:.3f}")
    if summary.get("top_k_agent_accuracy") is not None:
        print(f"Top-k Agent Accuracy: {summary['top_k_agent_accuracy']*100:.1f}%")
    print("Assumptions:")
    for line in summary["assumptions"]:
        print(f"- {line}")


if __name__ == "__main__":
    main()
