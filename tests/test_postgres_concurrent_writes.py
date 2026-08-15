import os
import concurrent.futures
from agenteval.sdk.storage import TraceStore
from agenteval.sdk.tracer import trace

def _write_worker(worker_id: int, db_url: str, num_nodes: int):
    """Worker thread that opens its own connection and writes trace nodes concurrently."""
    session_id = f"concurrent_session_w{worker_id}"
    store = TraceStore(db_path=db_url)
    
    try:
        for i in range(num_nodes):
            node_id = f"node_worker_{worker_id}_step_{i}"
            trace_node = {
                "session_id": session_id,
                "node_id": node_id,
                "node_type": "generator",
                "timestamp_start": "2026-07-22T10:00:00.000000",
                "timestamp_end": "2026-07-22T10:00:01.000000",
                "inputs": {"worker_id": worker_id, "step": i, "query": "concurrent load test"},
                "outputs": {"response": f"response_{worker_id}_{i}"},
                "tokens_in": 10,
                "tokens_out": 20,
                "cost_usd": 0.0001,
            }
            store.save_trace_node(trace_node)
    finally:
        store.close()
        
    return session_id

def test_concurrent_trace_writes():
    """Validates concurrent multithreaded trace writing without row loss or lock corruption."""
    db_url = "sqlite:///test_concurrent_writes.db"
    print(f"\n--- Running Concurrent Trace Write Test against: {db_url} ---")
    
    num_workers = 10
    nodes_per_worker = 20
    total_expected_nodes = num_workers * nodes_per_worker
    
    store = TraceStore(db_path=db_url)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(_write_worker, worker_id, db_url, nodes_per_worker)
            for worker_id in range(num_workers)
        ]
        completed_sessions = [f.result() for f in concurrent.futures.as_completed(futures)]
        
    # Verify row counts
    all_traces = []
    for s_id in completed_sessions:
        traces = store.get_session_traces(s_id)
        assert len(traces) == nodes_per_worker, f"Expected {nodes_per_worker} nodes for session {s_id}, got {len(traces)}"
        all_traces.extend(traces)
        
    assert len(all_traces) == total_expected_nodes, f"Expected {total_expected_nodes} total nodes, got {len(all_traces)}"
    print(f"[SUCCESS] {total_expected_nodes} nodes written concurrently across {num_workers} threads with 0.0% row loss or corruption.")
    
    store.close()
    if "test_concurrent_writes.db" in db_url and os.path.exists("test_concurrent_writes.db"):
        os.remove("test_concurrent_writes.db")

if __name__ == "__main__":
    test_concurrent_trace_writes()
