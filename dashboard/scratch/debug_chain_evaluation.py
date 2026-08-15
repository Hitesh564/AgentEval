import os
from datetime import datetime, timezone
from datasets import load_dataset

from agenteval.sdk.storage import TraceStore
from agenteval.root_cause.cross_session import CrossSessionEngine

def debug_case_1():
    dataset = load_dataset("Kevin355/Who_and_When", "Hand-Crafted")
    train_split = dataset["train"]
    db_path = "agenteval.db"
    store = TraceStore(db_path=db_path)
    user_id = "who_when_user"

    item = train_split[0] # Case 1
    q_id = str(item["question_ID"])
    history = item["history"]

    store.delete_case_traces(user_id, q_id)

    last_session_id = None
    prev_session_id = None

    active_step_count = 0
    for i, step in enumerate(history):
        role = step.get("role")
        if role == "human":
            continue

        role_clean = role.lower()
        if "thought" in role_clean or "termination" in role_clean or "orchestrator" in role_clean:
            agent_name = "orchestrator"
            node_type = "planner" if "termination" not in role_clean else "critic"
        else:
            agent_name = role_clean
            node_type = "generator"

        session_id = f"session_{q_id}_step{active_step_count}_{agent_name}"
        node_id = f"step_{i}"

        prev_turns = history[:i]
        input_prompt = ""
        for pt in prev_turns:
            input_prompt += f"{pt.get('role')}: {pt.get('content')}\n"

        trace_node = {
            "session_id": session_id,
            "node_id": node_id,
            "node_type": node_type,
            "timestamp_start": datetime.now(timezone.utc).isoformat(),
            "timestamp_end": datetime.now(timezone.utc).isoformat(),
            "inputs": {
                "query": item["question"],
                "input_prompt": input_prompt.strip()
            },
            "outputs": {
                "response": step.get("content")
            },
            "parent_node_ids": [f"step_{i-1}"] if i > 0 else [],
            "user_id": user_id
        }

        store.save_trace_node(trace_node)

        if prev_session_id and prev_session_id != session_id:
            store.save_session_link(session_id, prev_session_id, link_reason="Handoff", user_id=user_id)

        prev_session_id = session_id
        last_session_id = session_id
        active_step_count += 1

    cross_engine = CrossSessionEngine(db_path=db_path, mode="replay")
    res = cross_engine.diagnose_chain(last_session_id, user_id=user_id)

    print("=== DEBUG CHAIN EVALUATION FOR CASE 1 ===")
    print(f"Chain length: {len(res['chain'])}")
    for s_info in res["chain"]:
        s_id = s_info["session_id"]
        nodes = store.get_session_traces(s_id, user_id=user_id)
        diagnosed = cross_engine.rc_engine.propagate_failures(nodes)
        min_health = min(n["raw_health"] for n in diagnosed) if diagnosed else 1.0
        print(f"Session: {s_id:<45} | Status: {s_info['status']:<12} | Score: {s_info['overall_score']:.2f} | Min Node Health: {min_health:.2f}")

if __name__ == "__main__":
    debug_case_1()
