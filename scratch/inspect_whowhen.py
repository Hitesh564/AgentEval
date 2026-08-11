from datasets import load_dataset
from agenteval.root_cause.cross_session import CrossSessionEngine
from agenteval.sdk.storage import TraceStore

def main():
    ds = load_dataset('Kevin355/Who_and_When', 'Hand-Crafted')['train']
    db_path = "agenteval.db"
    store = TraceStore(db_path=db_path)
    cross_engine = CrossSessionEngine(db_path=db_path, mode="replay")
    user_id = "who_when_user"
    
    print(f"{'Case':<5} | {'Question ID':<10} | {'Expected (Ground Truth)':<20} | {'Diagnosed RC':<30} | {'Match?'}")
    print("-" * 80)
    
    for i in range(15):
        item = ds[i]
        q_id = item["question_ID"]
        expected = item["mistake_agent"]
        start_session = f"session_{q_id}_orchestrator"
        
        try:
            res = cross_engine.diagnose_chain(start_session, user_id=user_id)
            diagnosed_rc = res["root_cause_session"]
            is_correct = expected.lower() in diagnosed_rc.lower()
            status = "MATCH" if is_correct else "MISATTRIBUTED"
            print(f"{i+1:<5} | {q_id[:8]:<10} | {expected:<20} | {diagnosed_rc:<30} | {status}")
        except Exception as e:
            print(f"{i+1:<5} | {q_id[:8]:<10} | {expected:<20} | ERROR: {e}")

if __name__ == "__main__":
    main()
