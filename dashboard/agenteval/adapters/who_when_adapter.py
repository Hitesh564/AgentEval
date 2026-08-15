import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
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
    parts = str(session_id).split("_")
    if not parts:
        return _normalize_label(session_id)
    return _normalize_label(parts[-1])


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

    for step_index, step in enumerate(history):
        role = step.get("role")
        if role == "human":
            continue

        role_clean = str(role).lower()
        node_type = _role_to_node_type(role_clean)
        if "thought" in role_clean or "termination" in role_clean or "orchestrator" in role_clean:
            agent_name = "orchestrator"
        else:
            agent_name = role_clean

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
            "parent_node_ids": [f"step_{step_index - 1}"] if step_index > 0 else [],
            "source_role": role_clean,
            "history_index": step_index,
            "user_id": user_id,
        }
        traces.append(trace_node)

        if prev_session_id and prev_session_id != session_id:
            traces[-1]["parent_session_id"] = prev_session_id

        prev_session_id = session_id
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
            expected_step=str(item.get("mistake_step")),
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
        _normalize_label(step["session_id"].split("_")[-1])
        for step in diagnosed_chain
        if step["status"] in ("root-cause", "co-contributor")
    ]
    expected_agent = _normalize_label(item["mistake_agent"])
    predicted_agent = "ambiguous" if root_session == "ambiguous" else _agent_label_from_session(root_session)

    predicted_step = None
    if root_node is not None:
        root_trace = next((node for node in traces if node["session_id"] == root_node["session_id"]), None)
        if root_trace is not None:
            predicted_step = root_trace.get("source_role") or root_trace.get("node_id")

    expected_step = item.get("mistake_step")
    agent_correct = expected_agent == predicted_agent
    step_correct = _step_matches(expected_step, predicted_step, root_node["root_cause_node"] if root_node else None)
    exact_match = agent_correct and step_correct

    return WhoWhenEvaluationRecord(
        case_id=q_id,
        expected_agent=expected_agent,
        predicted_agent=predicted_agent,
        expected_step=str(expected_step) if expected_step is not None else None,
        predicted_step=str(predicted_step) if predicted_step is not None else None,
        agent_correct=agent_correct,
        step_correct=step_correct,
        exact_match=exact_match,
        top_k_agents=[agent for agent in top_k_agents if agent != "none"],
    )


def aggregate_records(records: Sequence[WhoWhenEvaluationRecord]) -> Dict[str, Any]:
    y_true = [record.expected_agent for record in records]
    y_pred = [record.predicted_agent for record in records]
    step_true = [record.expected_step or "none" for record in records]
    step_pred = [record.predicted_step or "none" for record in records]

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
            "Step labels are compared using a normalization layer that accepts node IDs, step numbers, and textual roles.",
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
    from datasets import load_dataset
    from agenteval.root_cause.cross_session import CrossSessionEngine
    from agenteval.sdk.storage import TraceStore

    dataset = load_dataset(dataset_name, dataset_config)
    train_split = dataset["train"]
    store = TraceStore(db_path=db_path)
    store.create_user(user_id, api_key)

    records: List[WhoWhenEvaluationRecord] = []
    cross_engine = CrossSessionEngine(db_path=db_path, mode=mode)
    try:
        for idx in range(min(cases, len(train_split))):
            item = train_split[idx]
            q_id = str(item["question_ID"])
            store.delete_case_traces(user_id, q_id)
            record = evaluate_case(item, store=store, cross_engine=cross_engine, user_id=user_id)
            records.append(record)

        summary = aggregate_records(records)
        summary["dataset"] = {
            "name": dataset_name,
            "config": dataset_config,
            "cases_requested": cases,
            "cases_evaluated": len(records),
            "source": "Kevin355/Who_and_When",
        }
        summary["mode"] = mode
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
