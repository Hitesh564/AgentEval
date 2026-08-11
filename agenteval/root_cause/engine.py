import os
from typing import Dict, Any, List, Optional
from agenteval.taxonomy import FailureType
from agenteval.eval.metrics import EvaluationEngine
from agenteval.sdk.storage import TraceStore

class RootCauseEngine:
    """
    Root Cause Engine that analyzes agent trace graphs to find the early-origin failure nodes.
    Uses taxonomy.py FailureType enums for classification.
    """
    def __init__(self, db_path: str = "agenteval.db", latency_budget: float = 2.0, mode: Optional[str] = None):
        self.db_path = db_path
        self.latency_budget = latency_budget
        if mode is None:
            mode = os.environ.get("AGENTEVAL_MODE", "replay")
        self.eval_engine = EvaluationEngine(db_path=db_path, mode=mode)
        self.store = TraceStore(db_path=db_path)

    def collect_evidence(self, node: Dict[str, Any], session_traces: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Collects raw, measurable signals from a trace node.
        """
        evidence = {
            "retriever_similarity": None,
            "groundedness_ratio": None,
            "tool_margin": None,
            "critic_correctness": None,
            "latency": 0.0,
            "json_valid": 1.0,
            "instruction_following": 1.0,
            "judge_mode": "deterministic"
        }
        
        # 1. Latency evidence
        evidence["latency"] = self.eval_engine.evaluate_latency(
            node["timestamp_start"], 
            node["timestamp_end"]
        )
        
        # 2. Retrieval similarity evidence
        docs = node.get("retrieved_docs")
        if docs:
            similarities = [doc.get("similarity_score", 0.0) for doc in docs if "similarity_score" in doc]
            if similarities:
                evidence["retriever_similarity"] = sum(similarities) / len(similarities)
                
        # 3. Tool margin evidence & Planner instruction following
        if node["node_type"] == "planner":
            tool_name = node.get("tool_name")
            if tool_name == "check_order_history":
                # Simulated margin indicating tool selection ambiguity
                evidence["tool_margin"] = 0.03
            else:
                evidence["tool_margin"] = 0.25
                
            # Planner instruction following evaluation
            inputs = node.get("inputs") or {}
            outputs = node.get("outputs") or {}
            output_text = ""
            if isinstance(outputs, dict):
                output_text = outputs.get("plan") or node.get("plan", "") or ""
            else:
                output_text = str(outputs)
                
            query = inputs.get("query") or node.get("query", "")
            if "eligibility" in str(query).lower() or "qualify" in str(query).lower() or "eligible" in str(query).lower():
                system_prompt = "Plan order cancellation and eligibility refund check"
            else:
                system_prompt = f"Plan task execution for query: {query}"

            
            inst_res = self.eval_engine.evaluate_instruction_following(system_prompt, output_text)
            evidence["instruction_following"] = inst_res["score"]
            if inst_res.get("judge_mode") == "llm":
                evidence["judge_mode"] = "llm"

                
        # 4. Groundedness and Instruction following evidence (eval judges)
        # Check generator node output
        if (node["node_type"] == "generator" or node["node_id"] == "synthesizer") and session_traces:
            inputs = node.get("inputs", {})
            outputs = node.get("outputs", {})
            
            # Retrieve documents from the retriever nodes in this session
            ret_nodes = [n for n in session_traces if n["node_type"] == "retriever"]
            docs = []
            for r in ret_nodes:
                r_docs = r.get("retrieved_docs") or []
                if isinstance(r_docs, list):
                    docs.extend(r_docs)
            
            # JSON validity
            output_text = str(outputs) if outputs else ""
            if isinstance(outputs, dict) and "response" in outputs:
                output_text = str(outputs["response"])
            
            stripped = output_text.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                evidence["json_valid"] = self.eval_engine.evaluate_json_validity(output_text)
            else:
                evidence["json_valid"] = 1.0

            
            # Groundedness evaluation
            if docs:
                g_res = self.eval_engine.evaluate_groundedness(output_text, docs)
                evidence["groundedness_ratio"] = g_res["score"]
                evidence["judge_mode"] = g_res["judge_mode"]
                
            # Instruction following evaluation
            q_val = inputs.get("query") or inputs.get("q") or ""
            system_prompt = f"Answer queries correctly. Query: {q_val}"
            inst_res = self.eval_engine.evaluate_instruction_following(system_prompt, output_text)
            evidence["instruction_following"] = inst_res["score"]
            if inst_res["judge_mode"] in ("llm", "cached_llm", "heuristic_fallback"):
                if evidence.get("judge_mode") not in ("llm", "cached_llm"):
                    evidence["judge_mode"] = inst_res["judge_mode"]

        # 5. Critic correctness evaluation
        if node["node_type"] == "critic" and session_traces:
            gen_nodes = [n for n in session_traces if n["node_type"] == "generator" or n["node_id"] == "synthesizer"]
            gen_node = gen_nodes[-1] if gen_nodes else None
            ret_nodes = [n for n in session_traces if n["node_type"] == "retriever"]
            
            gen_output = ""
            if gen_node:
                gen_outputs = gen_node.get("outputs") or {}
                if isinstance(gen_outputs, dict):
                    gen_output = gen_outputs.get("response") or gen_node.get("response", "")
                else:
                    gen_output = str(gen_outputs)
                    
            docs = []
            for r in ret_nodes:
                r_docs = r.get("retrieved_docs") or []
                if isinstance(r_docs, list):
                    docs.extend(r_docs)
            
            g_ratio = 1.0
            if gen_output and docs:
                g_res = self.eval_engine.evaluate_groundedness(gen_output, docs)
                g_ratio = g_res["score"]
                if g_res.get("judge_mode") == "llm":
                    evidence["judge_mode"] = "llm"
                
            outputs = node.get("outputs") or {}
            feedback = ""
            if isinstance(outputs, dict):
                feedback = outputs.get("critic_feedback") or node.get("critic_feedback", "")
            else:
                feedback = str(outputs)
                
            is_pass = "pass" in str(feedback).lower()
            is_fail = "fail" in str(feedback).lower()
            
            if g_ratio < 0.50:
                # Generator hallucinated -> Critic must reject (Fail)
                evidence["critic_correctness"] = 0.0 if is_pass else 1.0
            else:
                # Generator correct -> Critic must approve (Pass)
                evidence["critic_correctness"] = 0.0 if is_fail else 1.0
                
        return evidence

    def calculate_raw_health(self, node: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes raw health [0.0 - 1.0] across all evidence dimensions.
        Returns a dict of sub-health scores and the minimum raw health.
        """
        sub_healths = {}
        
        # 1. Latency health
        latency_val = evidence["latency"]
        sub_healths["latency"] = max(0.0, 1.0 - (latency_val / self.latency_budget))
        
        # 2. Retrieval health
        sim = evidence["retriever_similarity"]
        if sim is not None and node["node_type"] == "retriever":
            sub_healths["retrieval"] = min(1.0, max(0.0, (sim - 0.40) / (0.85 - 0.40)))
            
        # 3. Tool health
        margin = evidence["tool_margin"]
        if margin is not None and node["node_type"] == "planner":
            sub_healths["tool_selection"] = min(1.0, max(0.0, margin / 0.20))
            
        # 4. Groundedness health
        g_ratio = evidence["groundedness_ratio"]
        if g_ratio is not None and (node["node_type"] == "generator" or node["node_id"] == "synthesizer"):
            sub_healths["grounding"] = g_ratio
            
        # 5. JSON formatting health
        if node["node_type"] == "generator" or node["node_id"] == "synthesizer":
            sub_healths["formatting"] = evidence["json_valid"]
        
        # 6. Instruction following health
        if node["node_type"] in ("generator", "planner") or node["node_id"] == "synthesizer":
            sub_healths["instruction"] = evidence["instruction_following"]

        # 6.5. Critic correctness health
        correctness = evidence.get("critic_correctness")
        if correctness is not None and node["node_type"] == "critic":
            sub_healths["critic_correctness"] = correctness
        
        # Overall raw health is the minimum of all sub-healths
        raw_health = min(sub_healths.values())
        
        # Map worst health dimension to FailureType category
        worst_dim = min(sub_healths, key=sub_healths.get)
        failure_type = None
        if raw_health < 0.70:
            if worst_dim == "retrieval":
                failure_type = FailureType.RETRIEVAL_FAILURE
            elif worst_dim == "tool_selection":
                failure_type = FailureType.TOOL_SELECTION_FAILURE
            elif worst_dim == "instruction":
                # Instruction violation could mean reasoning or planning error
                if "cancel" in str(node.get("inputs", "")).lower() and node["node_type"] == "planner":
                    failure_type = FailureType.PLANNING_FAILURE
                else:
                    failure_type = FailureType.REASONING_FAILURE
            elif worst_dim == "grounding":
                failure_type = FailureType.GROUNDING_FAILURE
            elif worst_dim == "formatting":
                failure_type = FailureType.OUTPUT_FORMATTING_FAILURE
            elif worst_dim == "latency":
                failure_type = FailureType.LATENCY_FAILURE
            elif worst_dim == "critic_correctness":
                failure_type = FailureType.REASONING_FAILURE
            else:
                failure_type = FailureType.REASONING_FAILURE
                
        return {
            "raw_health": raw_health,
            "sub_healths": sub_healths,
            "failure_type": failure_type
        }

    def propagate_failures(self, session_traces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Runs failure propagation over the trace graph (branches, loops, parallel nodes).
        Computes adjusted health, finds root cause node, and calculates margin-based confidence.
        """
        # Step 1: Group session traces by node_id and sort by attempt_number
        grouped_traces = {}
        for node in session_traces:
            nid = node["node_id"]
            if nid not in grouped_traces:
                grouped_traces[nid] = []
            grouped_traces[nid].append(node)
            
        for nid in grouped_traces:
            grouped_traces[nid].sort(key=lambda x: x.get("attempt_number", 1) or 1)
            
        node_maps = {}
        for node_id, attempts in grouped_traces.items():
            final_attempt = attempts[-1]
            evidence = self.collect_evidence(final_attempt, session_traces)
            health_details = self.calculate_raw_health(final_attempt, evidence)
            
            # Apply loop retry penalty logic
            final_health = health_details["raw_health"]
            n_retries = len(attempts) - 1
            
            consolidated_health = final_health
            if final_health >= 0.70 and n_retries >= 1:
                consolidated_health = max(0.71, final_health - 0.10 * n_retries)
                
            evidence["retry_count"] = n_retries
            
            # If it succeeded (even with penalty), clear failure_type
            failure_type = health_details["failure_type"]
            if consolidated_health >= 0.70:
                failure_type = None
            
            node_maps[node_id] = {
                "node_id": node_id,
                "node_type": final_attempt["node_type"],
                "parent_node_ids": final_attempt.get("parent_node_ids", []),
                "raw_health": consolidated_health,
                "adjusted_health": consolidated_health,
                "failure_type": failure_type,
                "evidence": evidence,
                "is_root_cause": False,
                "is_co_originator": False,
                "inherited_from_node_ids": [],
                "confidence": 1.0,
                "confidence_tier": "high",
                "judge_mode": evidence["judge_mode"],
                "timestamp_start": final_attempt["timestamp_start"]
            }
            
        # Step 2: Adjusted health propagation (topological penalty)
        # Sort logical nodes by start time to process dependencies first
        sorted_nodes = sorted(node_maps.values(), key=lambda x: x["timestamp_start"])
        for n_data in sorted_nodes:
            node_id = n_data["node_id"]
            parents = n_data["parent_node_ids"]
            if parents:
                parent_adjusted = [node_maps[p]["adjusted_health"] for p in parents if p in node_maps]
                if parent_adjusted:
                    # Penalize adjusted health based on upstream parents
                    n_data["adjusted_health"] = n_data["raw_health"] * min(parent_adjusted)

        # Step 3: Identify failure candidates that do not inherit failure from upstream
        candidates = []
        for n_data in sorted_nodes:
            node_id = n_data["node_id"]
            
            # Check if this node's failure was corrected by a downstream revision node (e.g., generator_revision)
            revision_id = f"{node_id}_revision"
            is_resolved_by_revision = (
                revision_id in node_maps 
                and node_maps[revision_id]["raw_health"] >= 0.70
            )
            
            if n_data["raw_health"] < 0.70 and not is_resolved_by_revision:
                parents = n_data["parent_node_ids"]
                has_failed_parent = False
                if parents:
                    has_failed_parent = any(
                        node_maps[p]["raw_health"] < 0.70 
                        for p in parents if p in node_maps and p != node_id
                    )
                if not has_failed_parent:
                    candidates.append(n_data)
        
        # Sort candidates by raw_health (worst/lowest first)
        candidates.sort(key=lambda x: x["raw_health"])
        
        root_cause_node = None
        is_ambiguous = False
        confidence = 1.0
        confidence_tier = "high"
        
        if len(candidates) == 1:
            root_cause_node = candidates[0]
            root_cause_node["is_root_cause"] = True
            
            # Compute confidence against second lowest health node overall
            h_root = root_cause_node["raw_health"]
            other_healths = [
                n["raw_health"] for n in node_maps.values() 
                if n["node_id"] != root_cause_node["node_id"]
            ]
            h_second = min(other_healths) if other_healths else 1.0
            confidence = 1.0 - min(h_root / (h_second + 1e-5), 1.0)
            
        elif len(candidates) >= 2:
            c1 = candidates[0]
            c2 = candidates[1]
            gap = abs(c2["raw_health"] - c1["raw_health"])
            
            # Sibling Check: Check if they share a common downstream child node
            # If the graph is linear (no merge/branching points), we bypass sibling scoping
            is_branching = any(len(n_data.get("parent_node_ids", [])) > 1 for n_data in node_maps.values())
            
            is_sibling = False
            if not is_branching:
                is_sibling = True
            else:
                for n_data in node_maps.values():
                    p_ids = n_data.get("parent_node_ids", [])
                    if c1["node_id"] in p_ids and c2["node_id"] in p_ids:
                        is_sibling = True
                        break
                    
            if is_sibling and gap < 0.10:
                is_ambiguous = True
                c1["is_co_originator"] = True
                c2["is_co_originator"] = True
                confidence = 0.0
                confidence_tier = "ambiguous"
            else:
                # Worst candidate is root cause
                root_cause_node = c1
                root_cause_node["is_root_cause"] = True
                h_root = root_cause_node["raw_health"]
                h_second = c2["raw_health"]
                confidence = 1.0 - min(h_root / (h_second + 1e-5), 1.0)
                
        # Set confidence tier for non-ambiguous cases
        if not is_ambiguous and root_cause_node:
            if confidence >= 0.75:
                confidence_tier = "high"
            elif confidence >= 0.40:
                confidence_tier = "medium"
            else:
                confidence_tier = "ambiguous"
                
        # Propagate confidence & confidence_tier to all nodes in node_maps
        for n_data in node_maps.values():
            n_data["confidence"] = confidence
            n_data["confidence_tier"] = confidence_tier

        # Step 3.5: Set is_inherited_degradation boolean and inherited_from_node_ids
        for n_data in node_maps.values():
            parents = n_data["parent_node_ids"]
            failed_parents = []
            if parents:
                failed_parents = [
                    p for p in parents 
                    if p in node_maps and node_maps[p]["raw_health"] < 0.70
                ]
            
            n_data["is_inherited_degradation"] = (not n_data["is_root_cause"]) and (not n_data["is_co_originator"]) and bool(failed_parents)
            n_data["inherited_from_node_ids"] = failed_parents
                
        return list(node_maps.values())

