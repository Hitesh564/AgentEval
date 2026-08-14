import os
from datetime import datetime, timezone
from datasets import load_dataset

from agenteval.sdk.storage import TraceStore
from agenteval.root_cause.cross_session import CrossSessionEngine

def inspect_subscores():
    dataset = load_dataset("Kevin355/Who_and_When", "Hand-Crafted")
    train_split = dataset["train"]
    db_path = "agenteval.db"
    store = TraceStore(db_path=db_path)
    user_id = "who_when_user"

    # Select 3 diverse cases: Case 1 (WebSurfer ground truth), Case 2 (Orchestrator ground truth), Case 15 (FileSurfer ground truth)
    target_indices = [0, 1, 14]

    for idx in target_indices:
        item = train_split[idx]
        q_id = str(item["question_ID"])
        history = item["history"]
        mistake_agent = item["mistake_agent"]

        print("\n" + "=" * 90)
        print(f"CASE {idx+1} (ID: {q_id[:8]}...) | Ground Truth Mistake Agent: {mistake_agent}")
        print("=" * 90)

        store.delete_case_traces(user_id, q_id)
        last_session_id = None
        prev_session_id = None
        step_index = 0

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

            session_id = f"session_{q_id}_step{step_index}_{agent_name}"
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
            step_index += 1

        # Inspect engine evidence collection & calculate_raw_health for each session in chain
        cross_engine = CrossSessionEngine(db_path=db_path, mode="replay")
        res = cross_engine.diagnose_chain(last_session_id, user_id=user_id)

        print(f"Traversed Chain Length: {len(res['chain'])} sessions")
        print("-" * 90)
        print(f"{'Session ID':<45} | {'Node Type':<10} | {'Inst. Foll.':<12} | {'Latency':<8} | {'Raw Health':<10}")
        print("-" * 90)

        for s_info in res["chain"]:
            s_id = s_info["session_id"]
            nodes = store.get_session_traces(s_id, user_id=user_id)
            for node in nodes:
                evidence = cross_engine.rc_engine.collect_evidence(node, nodes)
                health = cross_engine.rc_engine.calculate_raw_health(node, evidence)
                inst_score = evidence.get("instruction_following")
                lat_score = evidence.get("latency")
                raw_h = health.get("raw_health")
                sub_h = health.get("sub_healths")
                print(f"{s_id:<45} | {node['node_type']:<10} | {str(inst_score):<12} | {str(lat_score):<8} | {str(raw_h):<10}")
                print(f"   -> Sub-health breakdown: {sub_h}")
                print(f"   -> Inputs/Query preview: {str(node.get('inputs', {}))[:80]}...")
                print(f"   -> Outputs/Response preview: {str(node.get('outputs', {}))[:80]}...")

if __name__ == "__main__":
    inspect_subscores()
