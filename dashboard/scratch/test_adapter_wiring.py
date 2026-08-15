import os
from datetime import datetime, timezone

import pytest

pytest.importorskip("datasets")
if os.environ.get("AGENTEVAL_RUN_SCRATCH_TESTS") != "1":
    pytest.skip("scratch integration test disabled by default", allow_module_level=True)

from datasets import load_dataset

from agenteval.sdk.storage import TraceStore
from agenteval.root_cause.cross_session import CrossSessionEngine

def test_wiring(mode="replay"):
    dataset = load_dataset("Kevin355/Who_and_When", "Hand-Crafted")
    train_split = dataset["train"]
    db_path = "agenteval.db"
    store = TraceStore(db_path=db_path)
    user_id = "who_when_user"
    api_key = "who_when_secret_key"
    store.create_user(user_id, api_key)

    cases_data = []

    for idx in range(15):
        item = train_split[idx]
        q_id = str(item["question_ID"])
        history = item["history"]
        mistake_agent = item["mistake_agent"]
        mistake_step = item["mistake_step"]

        store.delete_case_traces(user_id, q_id)

        last_session_id = None
        prev_session_id = None

        # Build turn-by-turn or step-by-step sessions and links
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

            # Link this session to previous session in the turn sequence
            if prev_session_id and prev_session_id != session_id:
                store.save_session_link(session_id, prev_session_id, link_reason="Handoff", user_id=user_id)

            prev_session_id = session_id
            last_session_id = session_id
            active_step_count += 1

        cases_data.append({
            "question_id": q_id,
            "mistake_agent": mistake_agent,
            "mistake_step": mistake_step,
            "last_session": last_session_id
        })

    # Evaluate
    cross_engine = CrossSessionEngine(db_path=db_path, mode=mode)
    correct_count = 0

    print(f"\n================ TEST WIRING RESULTS ({mode.upper()}) ================")
    print(f"{'Case #':<6} | {'Expected Agent':<18} | {'Diagnosed RC Session':<40} | {'Verdict'}")
    print("-" * 80)

    for i, case in enumerate(cases_data):
        q_id = case["question_id"]
        last_session = case["last_session"]
        expected_agent = case["mistake_agent"].lower()

        res = cross_engine.diagnose_chain(last_session, user_id=user_id)
        diagnosed_rc = res["root_cause_session"]

        is_correct = expected_agent in diagnosed_rc.lower()
        verdict = "CORRECT" if is_correct else "INCORRECT"
        if is_correct:
            correct_count += 1

        print(f"{i+1:<6} | {case['mistake_agent']:<18} | {diagnosed_rc:<40} | {verdict}")

    acc = (correct_count / len(cases_data)) * 100.0
    print("-" * 80)
    print(f"Accuracy: {acc:.1f}% ({correct_count}/{len(cases_data)})")

if __name__ == "__main__":
    test_wiring()
