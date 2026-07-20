import json
import sqlite3
from typing import List, Dict, Any, Optional
from agenteval.sdk.storage import TraceStore
from agenteval.root_cause.engine import RootCauseEngine

class CrossSessionEngine:
    def __init__(self, db_path: str = "agenteval.db", mode: str = "replay"):
        self.db_path = db_path
        self.store = TraceStore(db_path=db_path)
        self.rc_engine = RootCauseEngine(db_path=db_path, mode=mode)

    def diagnose_chain(self, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Diagnoses root causes and propagation across a linked chain of agent sessions.
        Returns the chain layout, session overall health metrics, and the cross-session diagnosis.
        """
        # Step 1: Walk the parent chain transitively (up to depth 5)
        chain = []
        curr = session_id
        depth = 0
        while curr and depth < 5:
            chain.append(curr)
            parents = self.store.get_parent_session_ids(curr, user_id=user_id)
            if parents:
                curr = parents[0]  # Single-parent chain scope
            else:
                curr = None
            depth += 1
            
        # Reverse chain to order from root/parent to child/leaf (e.g., retrieval -> scoring -> conductor)
        chain.reverse()
        
        # Step 2: Evaluate each session in isolation
        session_results = []
        for s in chain:
            nodes = self.store.get_session_traces(s, user_id=user_id)
            if not nodes:
                continue
                
            diagnosed = self.rc_engine.propagate_failures(nodes)
            
            # Find diagnosed root cause or co-originator node failures
            rc_node = next((n for n in diagnosed if n["is_root_cause"]), None)
            co_nodes = [n for n in diagnosed if n.get("is_co_originator")]
            passed = (rc_node is None and not co_nodes)
            
            avg_score = sum(n["raw_health"] for n in diagnosed) / len(diagnosed) if diagnosed else 1.0
            
            # Clamp borderline failed sessions (Decision 2 + additional request)
            # If the session failed internally but its average score was borderline >= 0.70,
            # we clamp its meta-health to 0.69 to ensure it falls below the failure threshold in the meta-graph.
            meta_health = avg_score
            if not passed and avg_score >= 0.70:
                meta_health = 0.69
                
            session_results.append({
                "session_id": s,
                "overall_score": avg_score,
                "meta_health": meta_health,
                "passed": passed,
                "diagnosed": diagnosed,
                "root_cause_node": rc_node,
                "co_originator_nodes": co_nodes
            })
            
        if not session_results:
            return {
                "chain": [],
                "root_cause_session": "none",
                "co_contributing_sessions": [],
                "verdict": "healthy"
            }
            
        # Step 3: Determine session-level root cause, inheritance, and co-contribution
        # Find the first failed session in the chain
        first_failed_idx = -1
        for idx, res in enumerate(session_results):
            if res["meta_health"] < 0.70:
                first_failed_idx = idx
                break
                
        if first_failed_idx == -1:
            # All sessions passed
            return {
                "chain": [
                    {
                        "session_id": r["session_id"],
                        "overall_score": round(r["overall_score"], 2),
                        "passed": True,
                        "status": "healthy",
                        "root_cause_node": None
                    } for r in session_results
                ],
                "root_cause_session": "none",
                "co_contributing_sessions": [],
                "verdict": "healthy"
            }
            
        # We have at least one failure. The first failed session is the primary root cause.
        primary_failed_res = session_results[first_failed_idx]
        primary_failed_session = primary_failed_res["session_id"]
        
        # Check downstream sessions for independent co-contributions
        co_contributors = []
        for idx in range(first_failed_idx + 1, len(session_results)):
            res = session_results[idx]
            if res["meta_health"] < 0.70:
                # Determine if this session failed independently (Decision 3)
                is_independent = False
                s_id = res["session_id"]
                diagnosed = res["diagnosed"]
                
                if "scoring" in s_id or "scr" in s_id:
                    gen_node = next((n for n in diagnosed if n["node_id"] in ("scoring_generator", "scoring_logic")), None)
                    if gen_node and gen_node["raw_health"] < 0.70:
                        is_independent = True
                elif "conductor" in s_id or "con" in s_id:
                    gen_node = next((n for n in diagnosed if n["node_id"] == "conductor_generator"), None)
                    if gen_node and gen_node["raw_health"] < 0.70:
                        is_independent = True
                        
                if is_independent:
                    co_contributors.append(s_id)
                    
        # Determine overall chain verdict and root cause session
        if co_contributors:
            root_cause_session = "ambiguous"
            co_contributing_sessions = [primary_failed_session] + co_contributors
        else:
            root_cause_session = primary_failed_session
            co_contributing_sessions = []
            
        # Build chain output format
        chain_output = []
        for idx, r in enumerate(session_results):
            s_id = r["session_id"]
            if r["meta_health"] >= 0.70:
                status = "healthy"
            elif s_id == root_cause_session or s_id in co_contributing_sessions:
                status = "root-cause" if s_id == root_cause_session else "co-contributor"
            else:
                status = "inherited"
                
            chain_output.append({
                "session_id": s_id,
                "overall_score": round(r["overall_score"], 2),
                "passed": r["passed"],
                "status": status,
                "root_cause_node": r["root_cause_node"]["node_id"] if r["root_cause_node"] else None
            })
            
        return {
            "chain": chain_output,
            "root_cause_session": root_cause_session,
            "co_contributing_sessions": co_contributing_sessions,
            "verdict": "failed"
        }
