from datasets import load_dataset
from agenteval.root_cause.cross_session import CrossSessionEngine
from agenteval.sdk.storage import TraceStore

def main():
    ds = load_dataset("Kevin355/Who_and_When", "Hand-Crafted")["train"]
    db_path = "agenteval.db"
    store = TraceStore(db_path=db_path)
    cross_engine = CrossSessionEngine(db_path=db_path, mode="replay")
    user_id = "who_when_user"

    print("=== RAW WHO&WHEN DATASET LABELS & DIAGNOSES (CASES 1-15) ===")
    print(f"{'Case #':<6} | {'Question ID':<10} | {'Raw Mistake Agent (Ground Truth)':<32} | {'Diagnosed Root Cause':<35} | {'Verdict'}")
    print("-" * 105)

    for i in range(15):
        item = ds[i]
        q_id = str(item["question_ID"])
        expected_agent = str(item["mistake_agent"])
        start_session = f"session_{q_id}_orchestrator"
        
        try:
            res = cross_engine.diagnose_chain(start_session, user_id=user_id)
            diagnosed_rc = res["root_cause_session"]
            is_correct = expected_agent.lower() in diagnosed_rc.lower()
            verdict = "MATCH (CORRECT)" if is_correct else "MISATTRIBUTED"
            print(f"{i+1:<6} | {q_id[:8]:<10} | {expected_agent:<32} | {diagnosed_rc[:35]:<35} | {verdict}")
        except Exception as e:
            print(f"{i+1:<6} | {q_id[:8]:<10} | {expected_agent:<32} | ERROR: {e}")

if __name__ == "__main__":
    main()
