import os
import sqlite3
import argparse
from datetime import datetime, timezone
from datasets import load_dataset

from agenteval.sdk.storage import TraceStore
from agenteval.root_cause.cross_session import CrossSessionEngine

def main():
    parser = argparse.ArgumentParser(description="Ingest and evaluate a subset of the Who&When dataset.")
    parser.add_argument("--cases", type=int, default=15, help="Number of cases to evaluate (default 15)")
    parser.add_argument("--db-path", default="agenteval.db", help="Path to SQLite database")
    parser.add_argument("--mode", default="replay", choices=["replay", "live"], help="Evaluation mode (replay or live)")
    parser.add_argument("--batch", type=int, choices=[1, 2, 3], help="Batch index to run (1, 2, or 3, each containing 5 cases)")
    args = parser.parse_args()

    # Load dataset
    print(f"Loading Who&When dataset (Hand-Crafted)...")
    dataset = load_dataset("Kevin355/Who_and_When", "Hand-Crafted")
    train_split = dataset["train"]

    # Determine slice of train_split to run
    if args.batch:
        start_idx = (args.batch - 1) * 5
        end_idx = start_idx + 5
        print(f"Running Batch {args.batch} (cases {start_idx} to {end_idx-1})")
    else:
        start_idx = 0
        end_idx = args.cases
        print(f"Running all {args.cases} cases")

    limit = min(len(train_split), end_idx)
    run_indices = range(start_idx, limit)

    store = TraceStore(db_path=args.db_path)
    
    # Register default user
    user_id = "who_when_user"
    api_key = "who_when_secret_key"
    store.create_user(user_id, api_key)
    
    print(f"Ingesting {len(run_indices)} cases into '{args.db_path}' under user '{user_id}'...")
    
    # Clean old traces for current batch cases only
    conn = sqlite3.connect(args.db_path)
    for idx in run_indices:
        item = train_split[idx]
        q_id = item["question_ID"]
        conn.execute("DELETE FROM traces WHERE user_id = ? AND session_id LIKE ?", (user_id, f"session_{q_id}_%"))
        conn.execute("DELETE FROM session_links WHERE user_id = ? AND (child_session_id LIKE ? OR parent_session_id LIKE ?)", (user_id, f"session_{q_id}_%", f"session_{q_id}_%"))
    conn.commit()
    conn.close()

    cases_data = []
    
    for idx in run_indices:
        item = train_split[idx]
        q_id = item["question_ID"]
        history = item["history"]
        mistake_agent = item["mistake_agent"]
        mistake_step = item["mistake_step"]
        
        # Save case metadata
        cases_data.append({
            "question_id": q_id,
            "mistake_agent": mistake_agent,
            "mistake_step": mistake_step,
            "question": item["question"]
        })
        
        # Ingest history as traces
        for i, step in enumerate(history):
            role = step.get("role")
            if role == "human":
                continue
                
            # Map role to specific node type
            role_clean = role.lower()
            if "thought" in role_clean:
                agent_name = "orchestrator"
                node_type = "planner"
            elif "termination" in role_clean:
                agent_name = "orchestrator"
                node_type = "critic"
            elif "orchestrator" in role_clean:
                agent_name = "orchestrator"
                node_type = "planner"
            else:
                agent_name = role_clean
                node_type = "generator"
                
            session_id = f"session_{q_id}_{agent_name}"
            node_id = f"step_{i}"
            
            # Input context
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
            
            # Save node
            store.save_trace_node(trace_node)
            
            # Record active agents to link them
            if agent_name != "orchestrator":
                child_session = session_id
                parent_session = f"session_{q_id}_orchestrator"
                store.save_session_link(child_session, parent_session, link_reason="Handoff", user_id=user_id)

    print("Ingestion complete. Starting evaluation...")
    
    # Step 3: Run cases through unmodified CrossSessionEngine
    cross_engine = CrossSessionEngine(db_path=args.db_path, mode=args.mode)
    
    correct_count = 0
    evaluated_cases = 0
    
    print("\n================== WHO&WHEN EVALUATION REPORT ==================")
    print(f"Mode: {args.mode.upper()} | Targeted Cases: {len(cases_data)}")
    print("-" * 80)
    
    for case in cases_data:
        q_id = case["question_id"]
        # The primary root coordinator session is orchestrator
        start_session = f"session_{q_id}_orchestrator"
        
        try:
            # Diagnose
            res = cross_engine.diagnose_chain(start_session, user_id=user_id)
            diagnosed_rc = res["root_cause_session"]
            
            # Expected root cause session name/ID
            expected_agent = case["mistake_agent"].lower()
            
            # Check correctness
            is_correct = False
            if expected_agent in diagnosed_rc.lower():
                is_correct = True
                
            if is_correct:
                correct_count += 1
                status = "CORRECT"
            else:
                status = "INCORRECT"
                
            print(f"Case ID: {q_id[:8]}... | Expected Agent: {case['mistake_agent']:<15} | Diagnosed: {diagnosed_rc:<35} | Verdict: {status}")
            evaluated_cases += 1
        except Exception as e:
            print(f"\n[ERROR] Failed to evaluate case {q_id[:8]}...: {str(e)}")
            if "RateLimitError" in str(type(e)) or "rate limit" in str(e).lower() or "429" in str(e):
                print("[WARNING] LLM Rate Limit/Quota Exceeded. Stopping evaluation early to preserve partial results.")
                break
            else:
                raise e
        
    accuracy = (correct_count / evaluated_cases) if evaluated_cases > 0 else 0.0
    print("-" * 80)
    print(f"Causal Attribution Accuracy: {accuracy*100:.1f}% ({correct_count}/{evaluated_cases} correct on successfully evaluated cases)")
    print("=================================================================")

if __name__ == "__main__":
    main()
