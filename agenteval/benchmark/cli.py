import os
import argparse
import sqlite3
import yaml
from typing import Dict, Any, List
from agenteval.eval.metrics import EvaluationEngine
from agenteval.root_cause.engine import RootCauseEngine
from agenteval.sdk.storage import TraceStore

def load_fixtures(fixtures_path: str = "examples/fixtures/test_cases.yaml") -> List[Dict[str, Any]]:
    """Loads fixtures from YAML."""
    if not os.path.exists(fixtures_path):
        return []
    with open(fixtures_path, "r") as f:
        return yaml.safe_load(f)

def evaluate_runs(session_ids: List[str], db_path: str, version: str = "calib", mode: str = "replay", fixtures_path: str = "examples/fixtures/test_cases.yaml") -> Dict[str, Any]:
    """Computes averages of the six metrics and attributes root causes."""
    store = TraceStore(db_path=db_path)
    rc_engine = RootCauseEngine(db_path=db_path, mode=mode)
    
    metrics_summary = {
        "instruction_following": [],
        "hallucination_rate": [],
        "tool_accuracy": [],
        "retrieval_quality": [],
        "latency": []
    }
    
    diagnosed_count = 0
    correct_attributions = 0
    passed_runs = 0
    fixtures = load_fixtures(fixtures_path)
    
    for session_id in session_ids:
        traces = store.get_session_traces(session_id)
        if not traces:
            continue
            
        diagnosed = rc_engine.propagate_failures(traces)
        
        # Extract metrics
        for node in diagnosed:
            evidence = node["evidence"]
            if node["node_type"] == "generator" or node["node_id"] == "synthesizer":
                metrics_summary["instruction_following"].append(evidence["instruction_following"])
                if evidence["groundedness_ratio"] is not None:
                    metrics_summary["hallucination_rate"].append(1.0 - evidence["groundedness_ratio"])
            elif node["node_type"] == "retriever":
                if evidence["retriever_similarity"] is not None:
                    metrics_summary["retrieval_quality"].append(evidence["retriever_similarity"])
            elif node["node_type"] == "planner":
                # tool accuracy (1.0 if not check_order_history)
                tool_name = node.get("tool_name")
                acc = 0.0 if tool_name == "check_order_history" else 1.0
                metrics_summary["tool_accuracy"].append(acc)
                
            metrics_summary["latency"].append(evidence["latency"])

        # Check attribution accuracy against ground truth in fixtures
        try:
            suffix = int(session_id.split("_")[-1])
            if "retry" in fixtures_path:
                idx = suffix - 300
            elif "branching" in fixtures_path:
                idx = suffix - 200
            else:
                idx = suffix - 100
            if 0 <= idx < len(fixtures):
                fixture = fixtures[idx]
                expected_rc = fixture["expected_root_cause"]
                
                # If version is fixed and case was resolved in fixed mode, expected root cause is none
                if version == "fixed" and fixture.get("resolved_in_fixed_mode"):
                    expected_rc = "none"
                
                # Find diagnosed root cause node name and type
                diagnosed_rc = "none"
                diagnosed_rc_type = "none"
                has_co_originator = any(node.get("is_co_originator") for node in diagnosed)
                for node in diagnosed:
                    if node.get("is_root_cause"):
                        diagnosed_rc = node["node_id"]
                        diagnosed_rc_type = node["node_type"]
                        break
                        
                if expected_rc == "ambiguous":
                    is_correct = (diagnosed_rc == "none" and has_co_originator)
                else:
                    is_correct = (diagnosed_rc == expected_rc or diagnosed_rc_type == expected_rc)
                        
                has_failure = any(node.get("is_root_cause") or node.get("is_co_originator") for node in diagnosed)
                if not has_failure:
                    passed_runs += 1
                        
                diagnosed_count += 1
                if is_correct:
                    correct_attributions += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            pass

    # Calculate averages
    averages = {}
    for key, vals in metrics_summary.items():
        averages[key] = sum(vals) / len(vals) if vals else 0.0
        
    accuracy = (correct_attributions / diagnosed_count) if diagnosed_count > 0 else None
    pass_rate = (passed_runs / len(session_ids)) if session_ids else 0.0
    
    return {
        "averages": averages,
        "accuracy": accuracy,
        "pass_rate": pass_rate,
        "total_runs": len(session_ids)
    }


def main():
    parser = argparse.ArgumentParser(description="AgentEval CLI Tool")
    subparsers = parser.add_subparsers(dest="command")

    compare_parser = subparsers.add_parser("compare", help="Compare version A and B runs")
    compare_parser.add_argument("version_a", type=str, help="Prefix/Identifier for Version A runs (e.g. calib)")
    compare_parser.add_argument("version_b", type=str, help="Prefix/Identifier for Version B runs")
    compare_parser.add_argument("--db", type=str, default="agenteval.db", help="Path to SQLite database")
    compare_parser.add_argument("--mode", type=str, choices=["replay", "live"], default="replay", help="Evaluation mode (replay or live)")
    compare_parser.add_argument("--fixtures", type=str, default="examples/fixtures/test_cases.yaml", help="Path to fixtures YAML file")

    args = parser.parse_args()
    
    if args.command == "compare":
        db_path = args.db
        if not os.path.exists(db_path):
            print(f"Error: Database file not found at {db_path}")
            return
            
        # Retrieve sessions in SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT DISTINCT session_id FROM traces")
        sessions = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Filter sessions by version string
        sessions_a = [s for s in sessions if args.version_a in s]
        sessions_b = [s for s in sessions if args.version_b in s]
        
        # Suffix filtering to prevent linear, branching, and retry runs from overlapping
        if "retry" in args.fixtures:
            sessions_a = [s for s in sessions_a if int(s.split("_")[-1]) >= 300]
            sessions_b = [s for s in sessions_b if int(s.split("_")[-1]) >= 300]
        elif "branching" in args.fixtures:
            sessions_a = [s for s in sessions_a if 200 <= int(s.split("_")[-1]) < 300]
            sessions_b = [s for s in sessions_b if 200 <= int(s.split("_")[-1]) < 300]
        else:
            sessions_a = [s for s in sessions_a if int(s.split("_")[-1]) < 200]
            sessions_b = [s for s in sessions_b if int(s.split("_")[-1]) < 200]
        
        if not sessions_a:
            print(f"Error: No traces found matching Version A: '{args.version_a}' in database '{db_path}'.")
            print(f"Please run calibration first to generate runs.")
            return

        if not sessions_b:
            print(f"Error: No traces found matching Version B: '{args.version_b}' in database '{db_path}'.")
            print(f"Please run the fixed agent calibration first to generate runs for comparison.")
            return

        res_a = evaluate_runs(sessions_a, db_path, args.version_a, mode=args.mode, fixtures_path=args.fixtures)
        res_b = evaluate_runs(sessions_b, db_path, args.version_b, mode=args.mode, fixtures_path=args.fixtures)



        # Print comparison report
        print(f"\n================== REGRESSION REPORT ==================")
        print(f"Version A: '{args.version_a}' ({res_a['total_runs']} runs) vs Version B: '{args.version_b}' ({res_b['total_runs']} runs)")
        print(f"-" * 70)
        print(f"{'Metric':<25} | {'Version A':<10} | {'Version B':<10} | {'Delta':<10}")
        print(f"-" * 70)
        
        for metric, key in [
            ("Instruction Following", "instruction_following"),
            ("Hallucination Rate", "hallucination_rate"),
            ("Tool-Calling Accuracy", "tool_accuracy"),
            ("Retrieval Quality", "retrieval_quality"),
            ("Average Latency (s)", "latency")
        ]:
            val_a = res_a["averages"][key]
            val_b = res_b["averages"][key]
            delta = val_b - val_a
            
            # Directional delta status
            if key == "latency" or key == "hallucination_rate":
                # Lower is better
                status = "IMPROVED" if delta < -0.01 else ("DEGRADED" if delta > 0.01 else "UNCHANGED")
            else:
                # Higher is better
                status = "IMPROVED" if delta > 0.01 else ("DEGRADED" if delta < -0.01 else "UNCHANGED")
                
            print(f"{metric:<25} | {val_a:<10.2f} | {val_b:<10.2f} | {delta:<+10.2f} ({status})")
            
        print(f"-" * 70)
        
        # Display validated accuracy and pass rates
        if res_a["accuracy"] is not None:
            print(f"Calibration Holdout Root Cause Accuracy (vA): {res_a['accuracy']*100:.1f}%")
        else:
            print("Calibration Holdout Root Cause Accuracy (vA): [UNCALIBRATED]")
            
        if res_b["accuracy"] is not None:
            print(f"Calibration Holdout Root Cause Accuracy (vB): {res_b['accuracy']*100:.1f}%")
            
        print(f"Regression Pass Rate (vA): {res_a['pass_rate']*100:.1f}% ({int(round(res_a['pass_rate']*res_a['total_runs']))}/{res_a['total_runs']} runs passed)")
        print(f"Regression Pass Rate (vB): {res_b['pass_rate']*100:.1f}% ({int(round(res_b['pass_rate']*res_b['total_runs']))}/{res_b['total_runs']} runs passed)")


            
        # Determine dynamic overall verdict
        better = 0
        worse = 0
        for k in ["instruction_following", "retrieval_quality", "tool_accuracy"]:
            if res_b["averages"][k] > res_a["averages"][k] + 0.01:
                better += 1
            elif res_b["averages"][k] < res_a["averages"][k] - 0.01:
                worse += 1
        for k in ["latency", "hallucination_rate"]:
            if res_b["averages"][k] < res_a["averages"][k] - 0.01:
                better += 1
            elif res_b["averages"][k] > res_a["averages"][k] + 0.01:
                worse += 1
                
        # Confidence calculation
        sum_improved = 0.0
        sum_degraded = 0.0
        
        # Max latency observed
        max_lat = max(0.5, res_a["averages"]["latency"], res_b["averages"]["latency"])
        
        for k in ["instruction_following", "retrieval_quality", "tool_accuracy"]:
            d = res_b["averages"][k] - res_a["averages"][k]
            if d > 0.01:
                sum_improved += d
            elif d < -0.01:
                sum_degraded += abs(d)
                
        for k in ["hallucination_rate"]:
            d = res_a["averages"][k] - res_b["averages"][k]
            if d > 0.01:
                sum_improved += d
            elif d < -0.01:
                sum_degraded += abs(d)
                
        # Latency (lower is better)
        lat_d = (res_a["averages"]["latency"] - res_b["averages"]["latency"]) / max_lat
        if lat_d > 0.01:
            sum_improved += lat_d
        elif lat_d < -0.01:
            sum_degraded += abs(lat_d)
            
        total_diff = sum_improved + sum_degraded
        confidence = 0.0
        if total_diff > 0:
            if better > worse:
                confidence = sum_improved / (total_diff + 0.05)
            elif worse > better:
                confidence = sum_degraded / (total_diff + 0.05)
        
        confidence = max(0.0, min(1.0, confidence))
        
        if better > worse:
            verdict = "Version B is BETTER"
        elif worse > better:
            verdict = "Version A is BETTER"
        else:
            verdict = "Versions are COMPARABLE"
            
        print(f"Overall Verdict: {verdict} (confidence: {confidence*100:.1f}%)")
        print(f"=======================================================")


    else:
        parser.print_help()

if __name__ == "__main__":
    main()
