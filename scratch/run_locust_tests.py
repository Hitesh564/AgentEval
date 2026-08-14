import subprocess
import csv
import os
import time

def run_locust_stage(users: int, spawn_rate: int, run_time_sec: int = 20, csv_prefix: str = "locust_res"):
    cmd = [
        "aienv\\Scripts\\locust.exe",
        "-f", "locustfile.py",
        "--headless",
        "-u", str(users),
        "-r", str(spawn_rate),
        "--run-time", f"{run_time_sec}s",
        "--host", "http://127.0.0.1:8000",
        "--csv", f"scratch/{csv_prefix}_u{users}"
    ]
    
    print(f"\n=======================================================")
    print(f"Running Locust Load Test Stage: {users} Users (Spawn Rate: {spawn_rate}/s)")
    print(f"=======================================================")
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    # Read CSV stats
    stats_file = f"scratch/{csv_prefix}_u{users}_stats.csv"
    parsed_results = []
    
    if os.path.exists(stats_file):
        with open(stats_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Name", "")
                if name != "Aggregated":
                    parsed_results.append({
                        "name": name,
                        "req_count": row.get("Request Count", 0),
                        "fail_count": row.get("Failure Count", 0),
                        "median_ms": row.get("50%", 0),
                        "p95_ms": row.get("95%", 0),
                        "p99_ms": row.get("99%", 0),
                        "rps": row.get("Requests/s", 0)
                    })
    return parsed_results

def main():
    stages = [
        (10, 5),   # 10 users
        (50, 10),  # 50 users
        (100, 20)  # 100 users
    ]
    
    all_stage_results = {}
    
    for users, spawn_rate in stages:
        res = run_locust_stage(users, spawn_rate, run_time_sec=20)
        all_stage_results[users] = res
        time.sleep(2)
        
    print("\n\n" + "="*80)
    print("                      FINAL LOCUST LOAD TEST SUMMARY")
    print("="*80)
    
    for users in [10, 50, 100]:
        print(f"\n--- Concurrency Level: {users} Users ---")
        print(f"{'Endpoint':<35} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'p99 (ms)':<9} | {'Req/s':<8} | {'Errors':<6}")
        print("-" * 80)
        for row in all_stage_results[users]:
            print(f"{row['name']:<35} | {row['median_ms']:<9} | {row['p95_ms']:<9} | {row['p99_ms']:<9} | {float(row['rps']):<8.1f} | {row['fail_count']:<6}")

if __name__ == "__main__":
    main()
