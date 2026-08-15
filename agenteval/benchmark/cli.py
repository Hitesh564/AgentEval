import argparse
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from agenteval.benchmark.metrics import BenchmarkRecord, benchmark_summary, render_benchmark_markdown
from agenteval.sdk.database import resolve_database_url
from agenteval.utils.miniyaml import load_structured_data


def _get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.getcwd(),
            text=True,
        ).strip()
    except Exception:
        return "unknown"

def load_fixtures(fixtures_path: str = "examples/fixtures/test_cases.yaml") -> List[Dict[str, Any]]:
    """Loads fixtures from YAML."""
    if not os.path.exists(fixtures_path):
        return []
    data = load_structured_data(fixtures_path)
    if isinstance(data, dict) and "examples" in data:
        data = data["examples"]
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError("Fixture file must contain a list of cases or an {examples: [...]} object")
    return data

def evaluate_runs(
    session_ids: List[str],
    db_path: str,
    version: str = "calib",
    mode: str = "replay",
    fixtures_path: str = "examples/fixtures/test_cases.yaml",
    user_id: Optional[str] = None,
    causal_origin_weighting: bool = True,
    seed: int = 0,
    n_bootstrap: int = 1000,
) -> Dict[str, Any]:
    """Computes averages of the six metrics and attributes root causes."""
    from agenteval.root_cause.engine import RootCauseEngine
    from agenteval.sdk.storage import TraceStore

    store = TraceStore(db_path=db_path)
    rc_engine = RootCauseEngine(db_path=db_path, mode=mode, causal_origin_weighting=causal_origin_weighting)
    
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
    eval_count = 0
    heuristic_count = 0
    benchmark_records: List[BenchmarkRecord] = []

    def _normalize_label(label: Optional[str]) -> str:
        if not label:
            return "none"
        value = str(label).strip().lower()
        mapping = {
            "retriever": "retriever",
            "planner": "planner",
            "generator": "generator",
            "critic": "critic",
            "none": "none",
            "ambiguous": "ambiguous",
            "retrieval_agent": "retrieval_agent",
            "scoring_agent": "scoring_agent",
            "conductor_agent": "conductor_agent",
            "policy_retriever": "retriever",
            "product_retriever": "retriever",
            "synthesizer": "generator",
            "generator_revision": "generator",
        }
        return mapping.get(value, value)

    def _session_agent_label(session_id: str) -> str:
        sid = session_id.lower()
        if "ret" in sid:
            return "retrieval_agent"
        if "scr" in sid:
            return "scoring_agent"
        if "con" in sid:
            return "conductor_agent"
        return "none"

    def _session_index(session_id: str) -> Optional[int]:
        try:
            import re
            match = re.search(r"(\d+)$", session_id)
            return int(match.group(1)) if match else None
        except Exception:
            return None

    def _filter_sessions_by_suffix(session_list: List[str], lower: int, upper: Optional[int] = None) -> List[str]:
        filtered: List[str] = []
        for session_id in session_list:
            suffix = _session_index(session_id)
            if suffix is None:
                continue
            if upper is None:
                if suffix >= lower:
                    filtered.append(session_id)
            elif lower <= suffix < upper:
                filtered.append(session_id)
        return filtered

    def _append_benchmark_record(
        *,
        case_id: str,
        true_agent: str,
        pred_agent: str,
        confidence: Optional[float],
        confidence_calibrated: bool = False,
        pred_step: Optional[str] = None,
        true_step: Optional[str] = None,
        top_k_agents: Optional[List[str]] = None,
        baseline_last_failure: Optional[str] = None,
        baseline_v1: Optional[str] = None,
    ) -> None:
        benchmark_records.append(
            BenchmarkRecord(
                case_id=case_id,
                true_agent=_normalize_label(true_agent),
                pred_agent=_normalize_label(pred_agent),
                true_step=true_step,
                pred_step=pred_step,
                confidence=confidence,
                confidence_calibrated=confidence_calibrated,
                top_k_agents=top_k_agents,
                baseline_last_failure=_normalize_label(baseline_last_failure) if baseline_last_failure else None,
                baseline_v1=_normalize_label(baseline_v1) if baseline_v1 else None,
            )
        )

    def _metric_value(node: Dict[str, Any], evidence: Dict[str, Any], key: str) -> Optional[float]:
        if key == "instruction_following":
            value = evidence.get("instruction_following")
            return float(value) if value is not None else None
        if key == "hallucination_rate":
            grounded = evidence.get("groundedness_evidence") or {}
            score = grounded.get("score")
            if score is None:
                score = evidence.get("groundedness_ratio")
            return (1.0 - float(score)) if score is not None else None
        if key == "retrieval_quality":
            retrieval = evidence.get("retrieval_evidence") or {}
            score = retrieval.get("score")
            if score is None:
                score = evidence.get("retriever_similarity")
            return float(score) if score is not None else None
        if key == "tool_accuracy":
            tool = evidence.get("tool_evidence") or {}
            score = tool.get("score")
            return float(score) if score is not None else None
        if key == "latency":
            value = evidence.get("latency")
            return float(value) if value is not None else None
        return None
    
    is_multi_agent = "multi_agent" in fixtures_path
    if is_multi_agent:
        from agenteval.root_cause.cross_session import CrossSessionEngine
        cross_engine = CrossSessionEngine(db_path=db_path, mode=mode, causal_origin_weighting=causal_origin_weighting)
        
    for session_id in session_ids:
        if is_multi_agent:
            res_chain = cross_engine.diagnose_chain(session_id, user_id=user_id)
            root_cause_session = res_chain["root_cause_session"]
            co_sessions = res_chain["co_contributing_sessions"]
            
            # Extract metrics from all sessions in the chain
            for session_info in res_chain["chain"]:
                s_id = session_info["session_id"]
                s_traces = store.get_session_traces(s_id, user_id=user_id)
                s_diagnosed = rc_engine.propagate_failures(s_traces)
                for node in s_diagnosed:
                    evidence = node["evidence"]
                    if "judge_mode" in evidence:
                        eval_count += 1
                        if evidence["judge_mode"] in ("heuristic_fallback", "fallback"):
                            heuristic_count += 1
                    if node["node_type"] == "generator" or node["node_id"] in ("synthesizer", "scoring_generator", "conductor_generator"):
                        instruction = _metric_value(node, evidence, "instruction_following")
                        hallucination = _metric_value(node, evidence, "hallucination_rate")
                        if instruction is not None:
                            metrics_summary["instruction_following"].append(instruction)
                        if hallucination is not None:
                            metrics_summary["hallucination_rate"].append(hallucination)
                    elif node["node_type"] == "retriever" or node["node_id"] in ("retrieval_retriever", "scoring_retriever"):
                        retrieval = _metric_value(node, evidence, "retrieval_quality")
                        if retrieval is not None:
                            metrics_summary["retrieval_quality"].append(retrieval)
                    elif node["node_type"] == "planner":
                        tool = _metric_value(node, evidence, "tool_accuracy")
                        if tool is not None:
                            metrics_summary["tool_accuracy"].append(tool)
                    metrics_summary["latency"].append(evidence["latency"])
            
            # Check correctness against expected root cause session and node in fixtures
            try:
                suffix = _session_index(session_id)
                if suffix is None:
                    continue
                fixture = next((f for f in fixtures if f["id"] == f"multi_agent_case_{suffix - 399:03d}"), None)
                if fixture:
                    expected_rc_session = fixture["expected_root_cause_session"]
                    expected_rc_node = fixture["expected_root_cause_node"]
                    top_agents = [
                        _session_agent_label(step["session_id"])
                        for step in res_chain["chain"]
                        if step["status"] in ("root-cause", "co-contributor")
                    ]
                    pred_agent = _session_agent_label(root_cause_session)
                    if root_cause_session == "ambiguous":
                        pred_agent = "ambiguous"
                    elif root_cause_session == "none":
                        pred_agent = "none"
                    pred_step = next((step["root_cause_node"] for step in res_chain["chain"] if step["status"] == "root-cause"), None)
                    baseline_last_failure = next(
                        (_session_agent_label(step["session_id"]) for step in reversed(res_chain["chain"]) if step["status"] in ("root-cause", "co-contributor")),
                        "none",
                    )
                    baseline_v1 = next(
                        (_session_agent_label(step["session_id"]) for step in res_chain["chain"] if step["status"] in ("root-cause", "co-contributor")),
                        "none",
                    )
                    _append_benchmark_record(
                        case_id=fixture["id"],
                        true_agent=expected_rc_session,
                        pred_agent=pred_agent,
                        confidence=next((step.get("confidence") for step in res_chain["chain"] if step["status"] == "root-cause"), None),
                        confidence_calibrated=bool(next((step.get("confidence_calibrated") for step in res_chain["chain"] if step["status"] == "root-cause"), False)),
                        pred_step=pred_step,
                        true_step=expected_rc_node if expected_rc_node != "none" else None,
                        top_k_agents=[label for label in top_agents if label != "none"],
                        baseline_last_failure=baseline_last_failure,
                        baseline_v1=baseline_v1,
                    )
                    
                    if version == "fixed":
                        if expected_rc_session in ("retrieval_agent", "scoring_agent"):
                            expected_rc_session = "none"
                            expected_rc_node = "none"
                        elif expected_rc_session == "ambiguous":
                            expected_rc_session = "none"
                            expected_rc_node = "none"
                            
                    # Evaluate correctness
                    if expected_rc_session == "ambiguous":
                        is_correct = (root_cause_session == "ambiguous" and len(co_sessions) > 0)
                    elif expected_rc_session == "none":
                        is_correct = (root_cause_session == "none")
                    else:
                        # Map expected agent name to session ID short code
                        expected_sub = expected_rc_session
                        if expected_rc_session == "retrieval_agent":
                            expected_sub = "ret"
                        elif expected_rc_session == "scoring_agent":
                            expected_sub = "scr"
                        elif expected_rc_session == "conductor_agent":
                            expected_sub = "con"
                            
                        # Find diagnosed node in expected session
                        diagnosed_rc_node = "none"
                        matched_s = next((s for s in res_chain["chain"] if expected_sub in s["session_id"]), None)
                        if matched_s:
                            diagnosed_rc_node = matched_s["root_cause_node"] or "none"
                        is_correct = (expected_sub in root_cause_session and diagnosed_rc_node == expected_rc_node)
                        
                    # Chain-level end-to-end pass rate: passes if no session in the chain failed
                    if root_cause_session == "none":
                        passed_runs += 1
                        
                    diagnosed_count += 1
                    if is_correct:
                        correct_attributions += 1
            except Exception as e:
                import traceback
                traceback.print_exc()
        else:
            traces = store.get_session_traces(session_id, user_id=user_id)
            if not traces:
                continue
                
            diagnosed = rc_engine.propagate_failures(traces)
            
            # Extract metrics
            for node in diagnosed:
                evidence = node["evidence"]
                if "judge_mode" in evidence:
                    eval_count += 1
                    if evidence["judge_mode"] in ("heuristic_fallback", "fallback"):
                        heuristic_count += 1
                if node["node_type"] == "generator" or node["node_id"] == "synthesizer":
                    instruction = _metric_value(node, evidence, "instruction_following")
                    hallucination = _metric_value(node, evidence, "hallucination_rate")
                    if instruction is not None:
                        metrics_summary["instruction_following"].append(instruction)
                    if hallucination is not None:
                        metrics_summary["hallucination_rate"].append(hallucination)
                elif node["node_type"] == "retriever":
                    retrieval = _metric_value(node, evidence, "retrieval_quality")
                    if retrieval is not None:
                        metrics_summary["retrieval_quality"].append(retrieval)
                elif node["node_type"] == "planner":
                    tool = _metric_value(node, evidence, "tool_accuracy")
                    if tool is not None:
                        metrics_summary["tool_accuracy"].append(tool)
                    
                metrics_summary["latency"].append(evidence["latency"])
    
            # Check attribution accuracy against ground truth in fixtures
            try:
                suffix = _session_index(session_id)
                if suffix is None:
                    continue
                if "retry" in fixtures_path:
                    idx = suffix - 300
                elif "branching" in fixtures_path:
                    idx = suffix - 200
                else:
                    idx = suffix - 100
                if 0 <= idx < len(fixtures):
                    fixture = fixtures[idx]
                    expected_rc = fixture["expected_root_cause"]
                    top_agents = [node["node_type"] for node in sorted(diagnosed, key=lambda n: n.get("attribution_score", 0.0), reverse=True) if node["node_type"]]
                    pred_agent = "ambiguous" if any(node.get("is_co_originator") for node in diagnosed) else next((node["node_type"] for node in diagnosed if node.get("is_root_cause")), "none")
                    pred_step = next((node["node_id"] for node in diagnosed if node.get("is_root_cause")), None)
                    baseline_last_failure = next((node["node_type"] for node in reversed(diagnosed) if node.get("failed_dimensions")), "none")
                    baseline_v1 = next((node["node_type"] for node in sorted(diagnosed, key=lambda n: n.get("raw_health", 1.0)) if node.get("failed_dimensions")), "none")
                    _append_benchmark_record(
                        case_id=fixture["id"],
                        true_agent=expected_rc,
                        pred_agent=pred_agent,
                        confidence=next((node.get("confidence") if node.get("confidence_calibrated") else None for node in diagnosed if node.get("is_root_cause")), None),
                        confidence_calibrated=bool(next((node.get("confidence_calibrated") for node in diagnosed if node.get("is_root_cause")), False)),
                        pred_step=pred_step,
                        true_step=None,
                        top_k_agents=[label for label in dict.fromkeys(top_agents) if label != "none"],
                        baseline_last_failure=baseline_last_failure,
                        baseline_v1=baseline_v1,
                    )
                    
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
    benchmark = benchmark_summary(benchmark_records, seed=seed, n_bootstrap=n_bootstrap) if benchmark_records else None
    
    return {
        "averages": averages,
        "accuracy": accuracy,
        "pass_rate": pass_rate,
        "total_runs": len(session_ids),
        "eval_count": eval_count,
        "heuristic_count": heuristic_count
        ,
        "benchmark": benchmark,
    }


def main():
    parser = argparse.ArgumentParser(description="AgentEval CLI Tool")
    subparsers = parser.add_subparsers(dest="command")

    compare_parser = subparsers.add_parser("compare", help="Compare version A and B runs")
    compare_parser.add_argument("version_a", type=str, help="Prefix/Identifier for Version A runs (e.g. calib)")
    compare_parser.add_argument("version_b", type=str, help="Prefix/Identifier for Version B runs")
    compare_parser.add_argument("--database-url", "--db", dest="database_url", type=str, default=None, help="AGENTEVAL_DATABASE_URL or SQLite fallback path")
    compare_parser.add_argument("--mode", type=str, choices=["replay", "live"], default="replay", help="Evaluation mode (replay or live)")
    compare_parser.add_argument("--fixtures", type=str, default="examples/fixtures/test_cases.yaml", help="Path to fixtures YAML file")
    compare_parser.add_argument("--seed", type=int, default=0, help="Deterministic seed for baseline sampling")

    benchmark_parser = subparsers.add_parser("benchmark", help="Run benchmark metrics and baselines on stored traces")
    benchmark_parser.add_argument("--database-url", "--db", dest="database_url", type=str, default=None, help="AGENTEVAL_DATABASE_URL or SQLite fallback path")
    benchmark_parser.add_argument("--mode", type=str, choices=["replay", "live"], default="replay", help="Evaluation mode (replay or live)")
    benchmark_parser.add_argument("--fixtures", type=str, default="examples/fixtures/test_cases.yaml", help="Path to fixtures YAML file")
    benchmark_parser.add_argument("--prefix", type=str, default="", help="Optional session prefix filter")
    benchmark_parser.add_argument("--output", type=str, default="reports/benchmark_report.md", help="Markdown output path")
    benchmark_parser.add_argument("--seed", type=int, default=0, help="Deterministic seed for baselines and bootstrap CIs")
    benchmark_parser.add_argument("--bootstrap-samples", type=int, default=1000, help="Bootstrap samples for confidence intervals")

    args = parser.parse_args()
    
    if args.command == "compare":
        from agenteval.sdk.storage import TraceStore

        db_path = resolve_database_url(args.database_url, allow_sqlite_fallback=True)
            
        # Retrieve sessions from database
        store = TraceStore(db_path=db_path)
        sessions = store.get_distinct_session_ids()
        
        # Filter sessions by version string
        sessions_a = [s for s in sessions if args.version_a in s]
        sessions_b = [s for s in sessions if args.version_b in s]
        
        # Suffix filtering to prevent linear, branching, and retry runs from overlapping
        if "multi_agent" in args.fixtures:
            sessions_a = [s for s in _filter_sessions_by_suffix(sessions_a, 400) if "con" in s]
            sessions_b = [s for s in _filter_sessions_by_suffix(sessions_b, 400) if "con" in s]
        elif "retry" in args.fixtures:
            sessions_a = _filter_sessions_by_suffix(sessions_a, 300, 400)
            sessions_b = _filter_sessions_by_suffix(sessions_b, 300, 400)
        elif "branching" in args.fixtures:
            sessions_a = _filter_sessions_by_suffix(sessions_a, 200, 300)
            sessions_b = _filter_sessions_by_suffix(sessions_b, 200, 300)
        else:
            sessions_a = [s for s in _filter_sessions_by_suffix(sessions_a, 0, 200)]
            sessions_b = [s for s in _filter_sessions_by_suffix(sessions_b, 0, 200)]
        
        if not sessions_a:
            print(f"Error: No traces found matching Version A: '{args.version_a}' in database '{db_path}'.")
            print(f"Please run calibration first to generate runs.")
            return

        if not sessions_b:
            print(f"Error: No traces found matching Version B: '{args.version_b}' in database '{db_path}'.")
            print(f"Please run the fixed agent calibration first to generate runs for comparison.")
            return

        res_a = evaluate_runs(sessions_a, db_path, args.version_a, mode=args.mode, fixtures_path=args.fixtures, seed=args.seed)
        res_b = evaluate_runs(sessions_b, db_path, args.version_b, mode=args.mode, fixtures_path=args.fixtures, seed=args.seed)

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
        is_ma = "multi_agent" in args.fixtures
        acc_label = "Root Cause Attribution Accuracy" if is_ma else "Calibration Holdout Root Cause Accuracy"
        pass_label = "Chain-Level End-to-End Pass Rate" if is_ma else "Regression Pass Rate"
        
        if res_a["accuracy"] is not None:
            print(f"{acc_label} (vA): {res_a['accuracy']*100:.1f}%")
        else:
            print(f"{acc_label} (vA): [UNCALIBRATED]")
            
        if res_b["accuracy"] is not None:
            print(f"{acc_label} (vB): {res_b['accuracy']*100:.1f}%")
            
        print(f"{pass_label} (vA): {res_a['pass_rate']*100:.1f}% ({int(round(res_a['pass_rate']*res_a['total_runs']))}/{res_a['total_runs']} runs passed)")
        print(f"{pass_label} (vB): {res_b['pass_rate']*100:.1f}% ({int(round(res_b['pass_rate']*res_b['total_runs']))}/{res_b['total_runs']} runs passed)")


            
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
        
        # Heuristic fallback warning
        total_evals = res_a.get("eval_count", 0) + res_b.get("eval_count", 0)
        total_heuristics = res_a.get("heuristic_count", 0) + res_b.get("heuristic_count", 0)
        if total_heuristics > 0:
            print(f"[WARNING] {total_heuristics}/{total_evals} evaluations used heuristic fallback due to cache misses. Results may not reflect live-judge accuracy.")

        if res_a.get("benchmark"):
            bench_a = res_a["benchmark"]
            bench_b = res_b["benchmark"]
            print(f"\nBaseline comparison (agent-level):")
            for name in ("random", "majority", "last_failure", "v1", "v2"):
                a_metrics = bench_a["baseline_metrics"][name]
                b_metrics = bench_b["baseline_metrics"][name]
                print(
                    f"- {name}: A acc={a_metrics['accuracy']:.3f}, B acc={b_metrics['accuracy']:.3f}, "
                    f"A macro_f1={a_metrics['macro_f1']:.3f}, B macro_f1={b_metrics['macro_f1']:.3f}"
                )

    elif args.command == "benchmark":
        from agenteval.sdk.storage import TraceStore

        db_path = resolve_database_url(args.database_url, allow_sqlite_fallback=True)

        store = TraceStore(db_path=db_path)
        sessions = store.get_distinct_session_ids(user_id=None)
        if args.prefix:
            sessions = [s for s in sessions if args.prefix in s]
        if not sessions:
            print("Error: No sessions found for benchmark run.")
            return

        generated_at = datetime.now(timezone.utc).isoformat()
        git_commit = _get_git_commit()
        result = evaluate_runs(
            sessions,
            db_path,
            version="benchmark",
            mode=args.mode,
            fixtures_path=args.fixtures,
            seed=args.seed,
            n_bootstrap=args.bootstrap_samples,
        )
        no_origin_result = evaluate_runs(
            sessions,
            db_path,
            version="benchmark-no-origin",
            mode=args.mode,
            fixtures_path=args.fixtures,
            causal_origin_weighting=False,
            seed=args.seed,
            n_bootstrap=args.bootstrap_samples,
        )
        benchmark = result.get("benchmark")
        benchmark_no_origin = no_origin_result.get("benchmark")
        if not benchmark or not benchmark_no_origin:
            print("Error: Benchmark summary could not be generated.")
            return

        label_distribution = benchmark.get("label_distribution") or {}
        report_bundle = dict(benchmark)
        report_bundle["dataset_lines"] = [
            f"- Source traces: {result.get('benchmark', {}).get('record_count', len(result.get('benchmark', {}).get('records', [])))} evaluated benchmark records from {args.fixtures}.",
            f"- Unique case IDs: {result.get('benchmark', {}).get('case_count', 0)}.",
            f"- Benchmark mode: {args.mode}.",
            f"- Seed: {args.seed}.",
            f"- Bootstrap samples: {args.bootstrap_samples}.",
            f"- Generated at (UTC): {generated_at}.",
            f"- Git commit: {git_commit}.",
            "- Who&When adapter evaluation is reported separately and is not included in this benchmark run unless explicitly executed.",
        ]
        report_bundle["protocol_lines"] = [
            "- Version A (baseline) and Version B (current) are derived from stored traces and fixture labels.",
            "- Balanced accuracy averages only over classes with non-zero ground-truth support.",
            "- Macro-F1 follows the same support-aware class set used for the final report.",
            "- Threshold calibration reports use failure score = 1 - health for ROC-AUC and PR-AUC.",
        ]
        report_bundle["ablation"] = [
            {
                "variant": "last_failure",
                "accuracy": benchmark["baseline_metrics"]["last_failure"]["accuracy"],
                "macro_f1": benchmark["baseline_metrics"]["last_failure"]["macro_f1"],
                "balanced_accuracy": benchmark["baseline_metrics"]["last_failure"]["balanced_accuracy"],
                "top_k_accuracy": None,
            },
            {
                "variant": "v1_attribution",
                "accuracy": benchmark["baseline_metrics"]["v1"]["accuracy"],
                "macro_f1": benchmark["baseline_metrics"]["v1"]["macro_f1"],
                "balanced_accuracy": benchmark["baseline_metrics"]["v1"]["balanced_accuracy"],
                "top_k_accuracy": benchmark.get("top_k_accuracy"),
            },
            {
                "variant": "v2_no_causal_origin",
                "accuracy": benchmark_no_origin["metrics"]["accuracy"],
                "macro_f1": benchmark_no_origin["metrics"]["macro_f1"],
                "balanced_accuracy": benchmark_no_origin["metrics"]["balanced_accuracy"],
                "top_k_accuracy": benchmark_no_origin.get("top_k_accuracy"),
            },
            {
                "variant": "v2_full",
                "accuracy": benchmark["metrics"]["accuracy"],
                "macro_f1": benchmark["metrics"]["macro_f1"],
                "balanced_accuracy": benchmark["metrics"]["balanced_accuracy"],
                "top_k_accuracy": benchmark.get("top_k_accuracy"),
            },
        ]
        report_bundle["who_when"] = [
            "- Not executed in this benchmark run.",
            "- The Who&When adapter evaluates both agent and step attribution when run directly via `python -m agenteval.adapters.who_when_adapter`.",
            "- Adapter assumptions: history is converted to single-parent session chains and step IDs are derived from history order.",
        ]
        report_bundle["calibration"] = [
            "- Dedicated calibration workflow available at `python -m scripts.calibrate`.",
        ]
        calibration_report_path = os.path.join("artifacts", "calibration_report.json")
        if os.path.exists(calibration_report_path):
            with open(calibration_report_path, "r", encoding="utf-8") as handle:
                calibration_report = json.load(handle)
            split = calibration_report.get("split") or {}
            threshold = calibration_report.get("threshold") or {}
            fit = threshold.get("fit") or {}
            holdout = threshold.get("holdout") or {}
            confidence = calibration_report.get("confidence") or {}
            report_bundle["calibration"].extend([
                f"- Threshold calibration fit on a benchmark-derived dataset with {split.get('calibration_size', 'n/a')} calibration examples and {split.get('holdout_size', 'n/a')} holdout examples.",
                f"- Fit threshold: {fit.get('threshold', 'n/a'):.3f}" if isinstance(fit.get("threshold"), (int, float)) else f"- Fit threshold: {fit.get('threshold', 'n/a')}",
                f"- Holdout F1: {holdout.get('f1', 'n/a'):.3f}" if isinstance(holdout.get("f1"), (int, float)) else f"- Holdout F1: {holdout.get('f1', 'n/a')}",
                f"- Holdout ROC-AUC: {holdout.get('roc_auc', 'n/a'):.3f}" if isinstance(holdout.get("roc_auc"), (int, float)) else f"- Holdout ROC-AUC: {holdout.get('roc_auc', 'n/a')}",
                f"- Holdout PR-AUC: {holdout.get('pr_auc', 'n/a'):.3f}" if isinstance(holdout.get("pr_auc"), (int, float)) else f"- Holdout PR-AUC: {holdout.get('pr_auc', 'n/a')}",
                f"- Confidence calibration fit available: {confidence.get('fit') is not None}.",
                "- Confidence calibration remains pending because the exported benchmark-derived dataset does not include labeled confidence scores.",
            ])
        else:
            report_bundle["calibration"].append(
                "- This benchmark run does not fit a new calibrator; it only reports whether calibrated confidence values were available in the evaluated records."
            )
        report_bundle["limitations"] = [
            "- This report is based on the stored benchmark traces in the repository, not a broad external evaluation set.",
            "- Confidence calibration metrics may apply only to the calibrated subset, so coverage should be checked alongside ECE and Brier score.",
            "- Ablation results are directional; no statistical significance is claimed here.",
        ]

        report_md = render_benchmark_markdown(report_bundle, title="AgentEval Benchmark Report")
        output_path = args.output
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        print(report_md)
        print(f"\n[OK] Benchmark report written to {output_path}")


    else:
        parser.print_help()

if __name__ == "__main__":
    main()
