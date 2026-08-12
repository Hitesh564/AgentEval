import os
from typing import Dict, Any, List, Optional
from agenteval.taxonomy import FailureType
from agenteval.eval.metrics import EvaluationEngine
from agenteval.eval.health import get_health_config, weighted_health
from agenteval.eval.calibration import ConfidenceCalibration, ThresholdCalibrationArtifact
from agenteval.sdk.storage import TraceStore

class RootCauseEngine:
    """
    Root Cause Engine that analyzes agent trace graphs to find the early-origin failure nodes.
    Uses taxonomy.py FailureType enums for classification.
    """
    def __init__(
        self,
        db_path: str = "agenteval.db",
        latency_budget: float = 2.0,
        mode: Optional[str] = None,
        confidence_calibrator: Optional[ConfidenceCalibration] = None,
        confidence_calibration_path: Optional[str] = None,
        threshold_calibration_path: Optional[str] = None,
        threshold_calibration: Optional[ThresholdCalibrationArtifact] = None,
    ):
        self.db_path = db_path
        self.latency_budget = latency_budget
        if mode is None:
            mode = os.environ.get("AGENTEVAL_MODE", "replay")
        self.eval_engine = EvaluationEngine(db_path=db_path, mode=mode)
        self.store = TraceStore(db_path=db_path)
        self.confidence_calibrator = (
            confidence_calibrator
            or self._load_confidence_calibrator(
                confidence_calibration_path
                or os.environ.get("AGENTEVAL_CONFIDENCE_CALIBRATION_PATH")
            )
        )
        self.threshold_calibration = (
            threshold_calibration
            or self._load_threshold_calibration(
                threshold_calibration_path
                or os.environ.get("AGENTEVAL_THRESHOLD_CALIBRATION_PATH")
            )
        )

    def _load_confidence_calibrator(self, path: Optional[str]) -> Optional[ConfidenceCalibration]:
        if not path or not os.path.exists(path):
            return None
        try:
            return ConfidenceCalibration.load_json(path)
        except Exception:
            return None

    def _load_threshold_calibration(self, path: Optional[str]) -> Optional[ThresholdCalibrationArtifact]:
        if not path or not os.path.exists(path):
            return None
        try:
            return ThresholdCalibrationArtifact.load_json(path)
        except Exception:
            return None

    def _calibrated_failure_threshold(self, node_type: str, config) -> float:
        if self.threshold_calibration is not None:
            metric = str(self.threshold_calibration.metric).lower()
            if metric in {node_type.lower(), "overall", "overall_health", "all"}:
                return float(self.threshold_calibration.threshold)
        return config.threshold_policy.get("overall", 0.70)

    def get_failure_threshold(self, node_type: str) -> float:
        """Returns the active failure threshold for a node type."""
        return self._calibrated_failure_threshold(node_type, get_health_config(node_type))

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
            "judge_mode": "deterministic",
            "retrieval_evidence": None,
            "groundedness_evidence": None,
            "tool_evidence": None,
            "latency_evidence": None,
        }
        inputs = node.get("inputs") or {}
        outputs = node.get("outputs") or {}
        output_text = ""
        if isinstance(outputs, dict):
            output_text = outputs.get("response") or outputs.get("plan") or outputs.get("content") or ""
        else:
            output_text = str(outputs)

        query = inputs.get("query") or inputs.get("q") or inputs.get("question") or node.get("query", "")

        # 1. Latency evidence
        if node.get("timestamp_start") and node.get("timestamp_end"):
            evidence["latency"] = self.eval_engine.evaluate_latency(
                node["timestamp_start"],
                node["timestamp_end"]
            )
            evidence["latency_evidence"] = {
                "value": evidence["latency"],
                "status": "complete",
                "method": "latency",
            }

        # 2. Retrieval similarity evidence
        docs = node.get("retrieved_docs") or []
        if docs:
            query_embedding = inputs.get("query_embedding") or inputs.get("embedding")
            retrieval_res = self.eval_engine.evaluate_retrieval_evidence(
                str(query) if query is not None else None,
                docs,
                query_embedding=query_embedding,
            )
            evidence["retrieval_evidence"] = retrieval_res
            if retrieval_res.get("score") is not None:
                evidence["retriever_similarity"] = retrieval_res["score"]
            if retrieval_res.get("judge_mode") in ("llm", "cached_llm", "heuristic_fallback"):
                evidence["judge_mode"] = retrieval_res["judge_mode"]

        # 3. Tool evidence and planner instruction following
        if node["node_type"] == "planner":
            tool_calls = node.get("tool_calls") or []
            candidate_tools = []
            if isinstance(tool_calls, list):
                for tc in tool_calls:
                    if isinstance(tc, dict) and tc.get("name"):
                        candidate_tools.append(tc["name"])

            tool_res = self.eval_engine.evaluate_tool_selection(
                node.get("tool_name"),
                candidate_tools=candidate_tools or None,
                expected_tool=node.get("expected_tool"),
                tool_descriptions=node.get("tool_descriptions"),
            )
            evidence["tool_evidence"] = tool_res
            if tool_res.get("margin") is not None:
                evidence["tool_margin"] = tool_res["margin"]

            system_prompt = f"Plan task execution for query: {query}"
            inst_res = self.eval_engine.evaluate_instruction_following(system_prompt, output_text)
            evidence["instruction_following"] = inst_res.get("score", evidence["instruction_following"])
            if inst_res.get("judge_mode") in ("llm", "cached_llm", "heuristic_fallback"):
                evidence["judge_mode"] = inst_res["judge_mode"]

        # 4. Groundedness and instruction-following evidence for generators
        if (node["node_type"] == "generator" or node["node_id"] == "synthesizer") and session_traces:
            ret_nodes = [n for n in session_traces if n["node_type"] == "retriever"]
            all_docs = []
            for r in ret_nodes:
                r_docs = r.get("retrieved_docs") or []
                if isinstance(r_docs, list):
                    all_docs.extend(r_docs)

            stripped = output_text.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                evidence["json_valid"] = self.eval_engine.evaluate_json_validity(output_text)

            grounded_res = self.eval_engine.evaluate_groundedness(output_text, all_docs)
            evidence["groundedness_evidence"] = grounded_res
            if grounded_res.get("score") is not None:
                evidence["groundedness_ratio"] = grounded_res["score"]
            if grounded_res.get("judge_mode") in ("llm", "cached_llm", "heuristic_fallback"):
                evidence["judge_mode"] = grounded_res["judge_mode"]

            q_val = query or ""
            system_prompt = f"Answer queries correctly. Query: {q_val}"
            inst_res = self.eval_engine.evaluate_instruction_following(system_prompt, output_text)
            evidence["instruction_following"] = inst_res.get("score", evidence["instruction_following"])
            if inst_res.get("judge_mode") in ("llm", "cached_llm", "heuristic_fallback"):
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

            g_ratio = None
            if gen_output and docs:
                g_res = self.eval_engine.evaluate_groundedness(gen_output, docs)
                evidence["groundedness_evidence"] = g_res
                g_ratio = g_res.get("score")
                if g_ratio is not None:
                    evidence["groundedness_ratio"] = g_ratio
                if g_res.get("judge_mode") in ("llm", "cached_llm", "heuristic_fallback"):
                    evidence["judge_mode"] = g_res["judge_mode"]

            outputs = node.get("outputs") or {}
            feedback = ""
            if isinstance(outputs, dict):
                feedback = outputs.get("critic_feedback") or node.get("critic_feedback", "")
            else:
                feedback = str(outputs)

            is_pass = "pass" in str(feedback).lower()
            is_fail = "fail" in str(feedback).lower()

            if g_ratio is not None:
                if g_ratio < 0.50:
                    evidence["critic_correctness"] = 0.0 if is_pass else 1.0
                else:
                    evidence["critic_correctness"] = 0.0 if is_fail else 1.0
                
        return evidence

    def calculate_raw_health(self, node: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes weighted node health across the available evidence dimensions.
        Keeps per-dimension metrics and weakest-dimension signals for attribution.
        """
        node_type = node["node_type"]
        config = get_health_config(node_type)

        metric_scores: Dict[str, Optional[float]] = {}

        latency_health = max(0.0, 1.0 - (evidence["latency"] / self.latency_budget))
        metric_scores["latency"] = latency_health

        if node_type == "retriever":
            retrieval = evidence.get("retrieval_evidence") or {}
            retrieval_score = retrieval.get("score", evidence.get("retriever_similarity"))
            if retrieval_score is not None:
                metric_scores["retrieval_relevance"] = float(retrieval_score)
            if retrieval.get("recall_at_k") is not None:
                metric_scores["retrieval_recall"] = float(retrieval["recall_at_k"])
            if retrieval.get("evidence", {}).get("retrieved_docs_count") is not None:
                metric_scores["retrieval_coverage"] = 1.0 if retrieval["evidence"]["retrieved_docs_count"] > 0 else 0.0

        if node_type == "planner":
            tool_evidence = evidence.get("tool_evidence") or {}
            if tool_evidence.get("score") is not None:
                metric_scores["tool_selection"] = float(tool_evidence["score"])
            if tool_evidence.get("argument_score") is not None:
                metric_scores["tool_arguments"] = float(tool_evidence["argument_score"])
            if evidence.get("instruction_following") is not None:
                metric_scores["instruction_following"] = float(evidence["instruction_following"])

        if node_type == "generator" or node["node_id"] == "synthesizer":
            if evidence.get("groundedness_ratio") is not None:
                metric_scores["groundedness"] = float(evidence["groundedness_ratio"])
            if evidence.get("instruction_following") is not None:
                metric_scores["instruction_following"] = float(evidence["instruction_following"])
            if evidence.get("json_valid") is not None:
                metric_scores["schema_validity"] = float(evidence["json_valid"])

        if node_type == "critic":
            if evidence.get("critic_correctness") is not None:
                metric_scores["critic_correctness"] = float(evidence["critic_correctness"])
            if evidence.get("instruction_following") is not None:
                metric_scores["instruction_following"] = float(evidence["instruction_following"])

        health = weighted_health(metric_scores, config)
        raw_health = health["overall_health"] if health["overall_health"] is not None else 0.0
        worst_dim = health["weakest_dimension"]
        failure_type = None
        threshold = self._calibrated_failure_threshold(node_type, config)
        if health["overall_health"] is not None and health["overall_health"] < threshold:
            if worst_dim in ("retrieval", "retrieval_relevance", "retrieval_recall", "retrieval_coverage"):
                failure_type = FailureType.RETRIEVAL_FAILURE
            elif worst_dim == "tool_selection":
                failure_type = FailureType.TOOL_SELECTION_FAILURE
            elif worst_dim == "tool_arguments":
                failure_type = FailureType.TOOL_SELECTION_FAILURE
            elif worst_dim == "instruction":
                # Instruction violation could mean reasoning or planning error
                if "cancel" in str(node.get("inputs", "")).lower() and node["node_type"] == "planner":
                    failure_type = FailureType.PLANNING_FAILURE
                else:
                    failure_type = FailureType.REASONING_FAILURE
            elif worst_dim in ("grounding", "groundedness"):
                failure_type = FailureType.GROUNDING_FAILURE
            elif worst_dim in ("formatting", "schema_validity"):
                failure_type = FailureType.OUTPUT_FORMATTING_FAILURE
            elif worst_dim == "latency":
                failure_type = FailureType.LATENCY_FAILURE
            elif worst_dim == "critic_correctness":
                failure_type = FailureType.REASONING_FAILURE
            else:
                failure_type = FailureType.REASONING_FAILURE
                
        return {
            "raw_health": raw_health,
            "overall_health": raw_health,
            "metric_scores": health["metric_scores"],
            "weakest_dimension": health["weakest_dimension"],
            "weakest_dimension_score": health["weakest_dimension_score"],
            "failed_dimensions": health["failed_dimensions"],
            "evaluation_status": health["evaluation_status"],
            "sub_healths": health["metric_scores"],
            "legacy_min_health": health["legacy_min_health"],
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
            first_attempt = attempts[0]
            final_attempt = attempts[-1]
            final_evidence = self.collect_evidence(final_attempt, session_traces)
            first_evidence = self.collect_evidence(first_attempt, session_traces) if len(attempts) > 1 else final_evidence
            health_details = self.calculate_raw_health(final_attempt, final_evidence)
            first_health_details = self.calculate_raw_health(first_attempt, first_evidence)

            final_health = health_details["raw_health"]
            first_attempt_health = first_health_details["raw_health"]
            n_retries = len(attempts) - 1

            consolidated_health = final_health

            final_evidence["retry_count"] = n_retries
            final_evidence["first_attempt_health"] = first_attempt_health
            final_evidence["final_attempt_health"] = final_health
            final_evidence["retry_latency_cost"] = sum(
                max(0.0, self.eval_engine.evaluate_latency(a["timestamp_start"], a["timestamp_end"]))
                for a in attempts
            ) if len(attempts) > 1 else 0.0
            
            # If the final attempt is healthy, clear failure_type; retries remain explicit evidence.
            failure_type = health_details["failure_type"]
            failure_threshold = self._calibrated_failure_threshold(final_attempt["node_type"], get_health_config(final_attempt["node_type"]))
            if consolidated_health >= failure_threshold:
                failure_type = None
            
            node_maps[node_id] = {
                "node_id": node_id,
                "node_type": final_attempt["node_type"],
                "parent_node_ids": final_attempt.get("parent_node_ids", []),
                "raw_health": consolidated_health,
                "adjusted_health": consolidated_health,
                "overall_health": health_details.get("overall_health", consolidated_health),
                "metric_scores": health_details.get("metric_scores", {}),
                "weakest_dimension": health_details.get("weakest_dimension"),
                "weakest_dimension_score": health_details.get("weakest_dimension_score"),
                "failed_dimensions": health_details.get("failed_dimensions", []),
                "evaluation_status": health_details.get("evaluation_status", "complete"),
                "legacy_min_health": health_details.get("legacy_min_health"),
                "failure_type": failure_type,
                "evidence": final_evidence,
                "is_root_cause": False,
                "is_co_originator": False,
                "inherited_from_node_ids": [],
                "confidence": 1.0,
                "confidence_tier": "high",
                "judge_mode": final_evidence["judge_mode"],
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

        # Build reverse dependency edges for downstream evidence
        child_map: Dict[str, List[str]] = {node_id: [] for node_id in node_maps}
        for n_data in sorted_nodes:
            for parent_id in n_data.get("parent_node_ids", []):
                if parent_id in child_map:
                    child_map[parent_id].append(n_data["node_id"])

        # Step 2.5: Compute dependency-aware attribution evidence
        total_nodes = max(1, len(sorted_nodes))
        for idx, n_data in enumerate(sorted_nodes):
            node_id = n_data["node_id"]
            parents = n_data.get("parent_node_ids", [])
            child_ids = child_map.get(node_id, [])

            local_failure_score = max(0.0, 1.0 - n_data["raw_health"])
            upstream_scores = [max(0.0, 1.0 - node_maps[p]["raw_health"]) for p in parents if p in node_maps]
            upstream_dependency_score = sum(upstream_scores) / len(upstream_scores) if upstream_scores else 0.0
            downstream_scores = [max(0.0, 1.0 - node_maps[c]["raw_health"]) for c in child_ids if c in node_maps]
            downstream_consistency_score = sum(downstream_scores) / len(downstream_scores) if downstream_scores else 0.0
            temporal_score = 1.0 - (idx / (total_nodes - 1)) if total_nodes > 1 else 1.0
            origin_prior = max(0.0, min(1.0, 1.0 - upstream_dependency_score))

            components = {
                "local_failure_score": local_failure_score,
                "upstream_dependency_score": upstream_dependency_score,
                "downstream_consistency_score": downstream_consistency_score,
                "temporal_score": temporal_score,
            }
            weights = {
                "local_failure_score": 0.45,
                "upstream_dependency_score": 0.20,
                "downstream_consistency_score": 0.15,
                "temporal_score": 0.20,
            }
            weight_sum = sum(weights.values())
            attribution_score = sum(components[k] * weights[k] for k in components) / weight_sum if weight_sum else local_failure_score
            causal_origin_score = (
                0.45 * local_failure_score
                + 0.20 * origin_prior
                + 0.15 * downstream_consistency_score
                + 0.20 * temporal_score
            )
            causal_origin_score = max(0.0, min(1.0, causal_origin_score))

            n_data["children_node_ids"] = child_ids
            n_data["attribution_evidence"] = components
            n_data["attribution_score"] = attribution_score
            n_data["causal_origin_score"] = causal_origin_score

        # Step 3: Identify failure candidates that do not inherit failure from upstream
        candidates = []
        for n_data in sorted_nodes:
            node_id = n_data["node_id"]
            
            # Check if this node's failure was corrected by a downstream revision node (e.g., generator_revision)
            revision_id = f"{node_id}_revision"
            node_threshold = self._calibrated_failure_threshold(n_data["node_type"], get_health_config(n_data["node_type"]))
            is_resolved_by_revision = (
                revision_id in node_maps 
                and node_maps[revision_id]["raw_health"] >= node_threshold
            )
            
            if n_data.get("failed_dimensions") and not is_resolved_by_revision:
                parents = n_data["parent_node_ids"]
                has_failed_parent = False
                if parents:
                    parent_failure_types = {
                        node_maps[p]["failure_type"].value
                        for p in parents
                        if p in node_maps and node_maps[p].get("failure_type") is not None and p != node_id
                    }
                    current_failure_type = n_data.get("failure_type").value if n_data.get("failure_type") is not None else None
                    has_failed_parent = current_failure_type in parent_failure_types if current_failure_type else False
                if not has_failed_parent:
                    candidates.append(n_data)
        
        # Sort candidates by causal origin score rather than pure local severity alone.
        candidates.sort(key=lambda x: x.get("causal_origin_score", x.get("attribution_score", 0.0)), reverse=True)
        
        root_cause_node = None
        is_ambiguous = False
        candidate_separation = 0.0
        calibrated_probability = None
        confidence_calibrated = False
        confidence = None
        confidence_tier = "high"

        candidate_scores = [
            c.get("causal_origin_score", c.get("attribution_score", c["raw_health"]))
            for c in candidates
        ]
        if len(candidates) == 1:
            root_cause_node = candidates[0]
            root_cause_node["is_root_cause"] = True

            h_root = candidate_scores[0]
            h_second = 0.0
            candidate_separation = max(0.0, min(1.0, h_root - h_second))
        elif len(candidates) >= 2:
            c1 = candidates[0]
            c2 = candidates[1]
            gap = abs(c1["raw_health"] - c2["raw_health"])
            
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
                candidate_separation = 0.0
                confidence_tier = "ambiguous"
            else:
                # Worst candidate is root cause
                root_cause_node = c1
                root_cause_node["is_root_cause"] = True
                h_root = c1.get("causal_origin_score", c1.get("attribution_score", c1["raw_health"]))
                h_second = c2.get("causal_origin_score", c2.get("attribution_score", c2["raw_health"]))
                candidate_separation = max(0.0, min(1.0, h_root - h_second))

        if self.confidence_calibrator is not None:
            calibrated = self.confidence_calibrator.calibrate(candidate_separation)
            calibrated_probability = calibrated.get("calibrated_probability")
            confidence_calibrated = bool(calibrated.get("confidence_calibrated"))
            confidence = calibrated_probability if calibrated_probability is not None else candidate_separation
        else:
            confidence = candidate_separation
                
        # Set confidence tier for non-ambiguous cases
        if not is_ambiguous and root_cause_node:
            tier_basis = confidence if confidence is not None else candidate_separation
            if tier_basis >= 0.75:
                confidence_tier = "high"
            elif tier_basis >= 0.40:
                confidence_tier = "medium"
            else:
                confidence_tier = "ambiguous"
                
        # Propagate confidence & confidence_tier to all nodes in node_maps
        for n_data in node_maps.values():
            n_data["confidence"] = confidence
            n_data["confidence_calibrated"] = confidence_calibrated
            n_data["confidence_tier"] = confidence_tier
            n_data["candidate_separation"] = candidate_separation
            n_data["raw_score"] = candidate_separation
            n_data["calibrated_probability"] = calibrated_probability
            n_data["calibration_method"] = self.confidence_calibrator.method if self.confidence_calibrator is not None else "identity"
            n_data["calibration_status"] = self.confidence_calibrator.status if self.confidence_calibrator is not None else "unavailable"
            n_data["calibration_version"] = self.confidence_calibrator.version if self.confidence_calibrator is not None else "unavailable"
            n_data["ranked_candidates"] = [
                {
                    "node_id": c["node_id"],
                    "node_type": c["node_type"],
                    "attribution_score": c.get("attribution_score", c["raw_health"]),
                    "causal_origin_score": c.get("causal_origin_score", c.get("attribution_score", c["raw_health"])),
                    "raw_health": c["raw_health"],
                    "failure_type": c["failure_type"].value if c.get("failure_type") else None,
                }
                for c in candidates
            ]

        # Step 3.5: Set is_inherited_degradation boolean and inherited_from_node_ids
        for n_data in node_maps.values():
            parents = n_data["parent_node_ids"]
            failed_parents = []
            if parents:
                failed_parents = [
                    p for p in parents 
                    if p in node_maps and node_maps[p].get("failed_dimensions")
                ]
            
            n_data["is_inherited_degradation"] = (not n_data["is_root_cause"]) and (not n_data["is_co_originator"]) and bool(failed_parents)
            n_data["inherited_from_node_ids"] = failed_parents
                
        return list(node_maps.values())

