import sqlite3
import yaml
from agenteval.root_cause.engine import RootCauseEngine
from agenteval.sdk.storage import TraceStore

db_path = "agenteval.db"
store = TraceStore(db_path=db_path)
engine = RootCauseEngine(db_path=db_path, mode="replay")

with open("examples/fixtures/test_cases.yaml", "r") as f:
    fixtures = yaml.safe_load(f)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT session_id FROM traces WHERE session_id LIKE '%calib%'")
sessions = [row[0] for row in cursor.fetchall()]
conn.close()

sessions = [s for s in sessions if int(s.split("_")[-1]) < 200]

for session_id in sorted(sessions):
    suffix = int(session_id.split("_")[-1])
    idx = suffix - 100
    if 0 <= idx < len(fixtures):
        fixture = fixtures[idx]
        expected_rc = fixture["expected_root_cause"]
        
        traces = store.get_session_traces(session_id)
        diagnosed = engine.propagate_failures(traces)
        
        diagnosed_rc = "none"
        diagnosed_rc_type = "none"
        for node in diagnosed:
            if node.get("is_root_cause"):
                diagnosed_rc = node["node_id"]
                diagnosed_rc_type = node["node_type"]
                break
                
        is_correct = (diagnosed_rc == expected_rc or diagnosed_rc_type == expected_rc)
        
        if not is_correct or session_id in ("session_calib_302", "session_calib_306"):
            print(f"\n==========================================")
            print(f"SESSION: {session_id} | Expected: {expected_rc} | Diagnosed: {diagnosed_rc} | Correct: {is_correct}")
            
            # Print DB traces
            print("DB traces:")
            conn2 = sqlite3.connect(db_path)
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT node_id, attempt_number, retrieved_docs, outputs FROM traces WHERE session_id = ?", (session_id,))
            for r in cursor2.fetchall():
                print(f"  Node: {r[0]} | Attempt: {r[1]} | Docs: {r[2]} | Outputs: {r[3][:100] if r[3] else None}")
            conn2.close()
            
            # Print Engine Diagnosed Info
            print("Engine Diagnosis:")
            # Recompute session_passed debug variables
            critic_node = engine.propagate_failures(traces) # wait, diagnosed has them
            critic_m = next((n for n in diagnosed if n["node_id"] == "critic"), None)
            gen_nodes = [n for n in diagnosed if n["node_type"] == "generator" or n["node_id"] == "synthesizer"]
            final_gen = sorted(gen_nodes, key=lambda x: x["timestamp_start"])[-1] if gen_nodes else None
            
            # Let's inspect session_passed logic
            critic_ok = critic_m and critic_m["raw_health"] >= 0.70
            gen_ok = not final_gen or final_gen["raw_health"] >= 0.70
            
            print(f"  Debug session_passed: critic_ok={critic_ok}, gen_ok={gen_ok}")
            if final_gen:
                print(f"  Final Gen Node: ID={final_gen['node_id']}, Raw Health={final_gen['raw_health']:.4f}")
            for d in diagnosed:
                print(f"  Node: {d['node_id']} | Type: {d['node_type']} | Raw Health: {d['raw_health']:.4f} | Adjusted Health: {d['adjusted_health']:.4f} | Is RC: {d['is_root_cause']}")
                print(f"    Evidence: {d['evidence']}")
