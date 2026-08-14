import os
import time
import statistics
from fastapi.testclient import TestClient

from agenteval.sdk.storage import TraceStore
from agenteval.sdk.tracer import trace
from agenteval.server.main import app

def measure_endpoint_baseline(client: TestClient, api_key: str, method: str, endpoint: str, num_requests: int = 50):
    headers = {"X-API-Key": api_key}
    latencies = []
    
    # Warm-up request
    client.request(method, endpoint, headers=headers)
    
    for _ in range(num_requests):
        start_time = time.perf_counter()
        response = client.request(method, endpoint, headers=headers)
        end_time = time.perf_counter()
        
        assert response.status_code == 200, f"Expected 200 OK for {endpoint}, got {response.status_code}: {response.text}"
        latencies.append((end_time - start_time) * 1000.0) # in ms
        
    latencies.sort()
    
    p50 = statistics.median(latencies)
    p95_index = int(0.95 * len(latencies))
    p99_index = int(0.99 * len(latencies))
    p95 = latencies[min(p95_index, len(latencies) - 1)]
    p99 = latencies[min(p99_index, len(latencies) - 1)]
    mean_lat = statistics.mean(latencies)
    min_lat = min(latencies)
    max_lat = max(latencies)
    
    return {
        "endpoint": endpoint,
        "num_requests": num_requests,
        "min_ms": round(min_lat, 2),
        "mean_ms": round(mean_lat, 2),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "max_ms": round(max_lat, 2)
    }

def main():
    db_url = os.environ.get("AGENTEVAL_DATABASE_URL", "postgresql://agenteval@127.0.0.1:5432/agenteval")
    print(f"=== Zero-Concurrency Baseline Latency Measurement ===")
    print(f"Database URL: {db_url}")
    
    store = TraceStore(db_path=db_url)
    user_id = "loadtest_user"
    api_key = "loadtest_secret_key_123"
    store.create_user(user_id, api_key)
    
    # Ensure test trace data exists in DB for loadtest_user
    session_id_calib = "session_calib_loadtest_001"
    session_id_fixed = "session_fixed_loadtest_001"
    
    with trace(session_id=session_id_calib, node_id="planner", node_type="planner", db_path=db_url, api_key=api_key) as t:
        t.inputs = {"q": "Baseline latency test"}
        t.outputs = {"response": "Plan OK"}
        
    with trace(session_id=session_id_calib, node_id="generator", node_type="generator", db_path=db_url, api_key=api_key) as t:
        t.inputs = {"q": "Baseline latency test"}
        t.outputs = {"response": "Generator response"}
        t.parent_node_ids = ["planner"]
        
    with trace(session_id=session_id_fixed, node_id="planner", node_type="planner", db_path=db_url, api_key=api_key) as t:
        t.inputs = {"q": "Baseline latency test fixed"}
        t.outputs = {"response": "Plan OK"}
        
    client = TestClient(app)
    
    endpoints_to_test = [
        ("GET", "/api/sessions"),
        ("GET", f"/api/sessions/{session_id_calib}/trace"),
        ("GET", f"/api/sessions/{session_id_calib}/chain"),
        ("GET", "/api/benchmark/compare"),
    ]
    
    results = []
    for method, ep in endpoints_to_test:
        res = measure_endpoint_baseline(client, api_key, method, ep, num_requests=50)
        results.append(res)
        
    print("\n----------------------------------------------------------------------------------------")
    print(f"{'Endpoint':<40} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'p99 (ms)':<9} | {'Mean (ms)':<9}")
    print("----------------------------------------------------------------------------------------")
    for r in results:
        print(f"{r['endpoint']:<40} | {r['p50_ms']:<9} | {r['p95_ms']:<9} | {r['p99_ms']:<9} | {r['mean_ms']:<9}")
    print("----------------------------------------------------------------------------------------\n")

if __name__ == "__main__":
    main()
