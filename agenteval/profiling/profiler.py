"""
LLM-based Workflow & Node Profiler for AgentEval.
Provides automatic workflow-level profiling, signature-based caching, non-blocking execution,
and graceful fallback mechanisms.
"""

import json
import time
import re
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from agenteval.eval.metrics import get_llm_response, _resolve_model_name
from agenteval.profiling.models import NodeProfile, WorkflowProfile, EvaluationDimension, WorkflowContext, ProfilingMeta

from agenteval.profiling.catalog import get_executable_metric_catalog, get_supported_metric_names
from agenteval.profiling.context import WorkflowContextBuilder
from agenteval.profiling.prompts import SYSTEM_PROFILER_PROMPT, build_workflow_profiler_prompt, PROFILER_VERSION
from agenteval.profiling.cache import ProfileCache, compute_profile_signature

# Dedicated thread pool for non-blocking profiling tasks
_PROFILER_THREAD_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="agenteval_profiler")


class WorkflowProfiler:
    """
    Workflow Profiler that observes execution context, calls LLM for semantic profiling,
    caches results, and integrates with EvaluationEngine and HealthConfig.
    """

    def __init__(
        self,
        db_path: str = "agenteval.db",
        model_name: Optional[str] = None,
        store: Optional[Any] = None,
    ):
        self.db_path = db_path
        self.model_name = _resolve_model_name(model_name)
        if store is not None:
            self.store = store
        else:
            try:
                from agenteval.sdk.storage import TraceStore
                self.store = TraceStore(db_path=db_path)
            except Exception:
                self.store = None

        self.cache = ProfileCache(store=self.store)
        self.metric_catalog = get_executable_metric_catalog()
        self.valid_metric_names = set(get_supported_metric_names())

    def _fallback_heuristic_role(self, node_name: str) -> str:
        """Legacy fallback string classification for fallback profiles."""
        name = node_name.lower()
        if "planner" in name:
            return "planner"
        elif "retriever" in name or "search" in name:
            return "retriever"
        elif "generator" in name or "response" in name:
            return "generator"
        elif "critic" in name or "eval" in name:
            return "critic"
        elif "tool" in name:
            return "tool"
        return "custom"

    def create_fallback_profile(
        self,
        session_id: str,
        node_id: str,
        node_type_hint: Optional[str] = None,
    ) -> NodeProfile:
        """Creates a conservative fallback profile when LLM profiling is unavailable or fails."""
        role = node_type_hint or self._fallback_heuristic_role(node_id)
        
        # Determine basic metrics based on fallback role
        executable_metrics = ["instruction_following", "semantic_response_quality", "latency"]
        if role == "retriever":
            executable_metrics = ["retrieval_evidence", "latency"]
        elif role == "planner":
            executable_metrics = ["tool_selection", "instruction_following", "semantic_response_quality", "latency"]
        elif role == "generator":
            executable_metrics = ["groundedness", "instruction_following", "semantic_response_quality", "json_validity", "latency"]

        # Basic default metric weights
        weights = {m: round(1.0 / len(executable_metrics), 2) for m in executable_metrics}

        return NodeProfile(
            session_id=session_id,
            node_id=node_id,
            profile_signature=f"fallback_{node_id}",
            profile_version=PROFILER_VERSION,
            inferred_role=role,
            purpose=f"Fallback profile for node '{node_id}'",
            responsibilities=[f"Execute {role} operations"],
            inputs_summary=["Generic inputs"],
            outputs_summary=["Generic outputs"],
            tools_used=[],
            evaluation_dimensions=[
                EvaluationDimension(
                    dimension_name="general_quality",
                    description="General node execution quality",
                    mapped_executable_metrics=executable_metrics,
                    is_executable=True,
                )
            ],
            executable_metrics=executable_metrics,
            metric_weights=weights,
            confidence=0.5,
        )

    def parse_and_validate_llm_output(
        self,
        raw_output: str,
        session_id: str,
        context: WorkflowContext,
    ) -> WorkflowProfile:
        """Parses LLM output, validates JSON schema and ensures executable metrics match catalog."""
        clean_json = raw_output.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json.split("\n", 1)[1]
        if clean_json.startswith("```"):
            clean_json = clean_json.split("\n", 1)[1]
        if clean_json.endswith("```"):
            clean_json = clean_json.rsplit("\n", 1)[0]

        parsed = json.loads(clean_json.strip())
        if not isinstance(parsed, dict):
            raise ValueError("LLM output is not a JSON object")

        node_profiles_data = parsed.get("node_profiles", [])
        validated_profiles: List[NodeProfile] = []

        # Map node_id -> node_ctx for signature computation
        ctx_map = {n.node_id: n for n in context.node_contexts}

        for np_data in node_profiles_data:
            if not isinstance(np_data, dict) or "node_id" not in np_data:
                continue

            node_id = str(np_data["node_id"])
            inferred_role = str(np_data.get("inferred_role") or self._fallback_heuristic_role(node_id))
            purpose = str(np_data.get("purpose") or f"Functional node {node_id}")
            responsibilities = np_data.get("responsibilities") or []
            if not isinstance(responsibilities, list):
                responsibilities = [str(responsibilities)]

            inputs_summary = np_data.get("inputs_summary") or []
            outputs_summary = np_data.get("outputs_summary") or []
            tools_used = np_data.get("tools_used") or []

            # Validate and filter executable metrics against real catalog
            raw_metrics = np_data.get("executable_metrics") or []
            valid_metrics = [m for m in raw_metrics if m in self.valid_metric_names]
            if not valid_metrics:
                # Default safety metrics if LLM returned unsupported names
                valid_metrics = ["instruction_following", "semantic_response_quality", "latency"]

            # Parse evaluation dimensions
            eval_dims_data = np_data.get("evaluation_dimensions") or []
            validated_dims: List[EvaluationDimension] = []
            for ed in eval_dims_data:
                if isinstance(ed, dict):
                    dim_name = str(ed.get("dimension_name", "quality"))
                    desc = str(ed.get("description", ""))
                    mapped = [m for m in ed.get("mapped_executable_metrics", []) if m in self.valid_metric_names]
                    validated_dims.append(
                        EvaluationDimension(
                            dimension_name=dim_name,
                            description=desc,
                            mapped_executable_metrics=mapped,
                            is_executable=len(mapped) > 0,
                        )
                    )

            # Metric weights
            raw_weights = np_data.get("metric_weights") or {}
            validated_weights: Dict[str, float] = {}
            if isinstance(raw_weights, dict):
                for m, w in raw_weights.items():
                    if m in valid_metrics:
                        try:
                            validated_weights[m] = max(0.0, min(1.0, float(w)))
                        except (ValueError, TypeError):
                            pass

            if not validated_weights and valid_metrics:
                equal_w = round(1.0 / len(valid_metrics), 2)
                validated_weights = {m: equal_w for m in valid_metrics}

            confidence = np_data.get("confidence", 0.9)
            try:
                confidence = max(0.0, min(1.0, float(confidence)))
            except (ValueError, TypeError):
                confidence = 0.9

            nctx = ctx_map.get(node_id)
            signature = compute_profile_signature(nctx, context.execution_graph) if nctx else f"sig_{node_id}"

            profile = NodeProfile(
                session_id=session_id,
                workflow_id=context.workflow_id,
                node_id=node_id,
                profile_signature=signature,
                profile_version=PROFILER_VERSION,
                inferred_role=inferred_role,
                purpose=purpose,
                responsibilities=[str(r) for r in responsibilities],
                inputs_summary=[str(i) for i in inputs_summary],
                outputs_summary=[str(o) for o in outputs_summary],
                tools_used=[str(t) for t in tools_used],
                evaluation_dimensions=validated_dims,
                executable_metrics=valid_metrics,
                metric_weights=validated_weights,
                confidence=confidence,
            )
            validated_profiles.append(profile)

        return WorkflowProfile(
            workflow_id=context.workflow_id,
            purpose=str(parsed.get("purpose", "")),
            node_profiles=validated_profiles,
        )
    # Execution traces -> Build context -> check profile cached? -> create profile -> save cache -> return workflow
    def profile_workflow(
        self,
        session_id: str,
        traces: List[Dict[str, Any]],
        workflow_id: str = "default_workflow",
    ) -> WorkflowProfile:
        """
        Profiles a workflow using a SINGLE LLM call for all nodes.
        Checks cache first. Uncached nodes trigger profiling.
        """
        start_time = time.time()
        context = WorkflowContextBuilder.build_workflow_context(session_id, traces, workflow_id=workflow_id)

        if not context.node_contexts:
            return WorkflowProfile(workflow_id=workflow_id, purpose="Empty workflow", node_profiles=[])

        # Check cache for existing node profiles
        cached_node_profiles: List[NodeProfile] = []
        uncached_contexts = []

        for nctx in context.node_contexts:
            sig = compute_profile_signature(nctx, context.execution_graph)
            cached_prof = self.cache.get_by_signature(sig)
            if not cached_prof:
                candidate_prof = self.cache.get_by_node(session_id, nctx.node_id)
                # Only reuse node-based profile if signature matches
                if candidate_prof and (not candidate_prof.profile_signature or candidate_prof.profile_signature == sig):
                    cached_prof = candidate_prof

            if cached_prof:
                cached_node_profiles.append(cached_prof)
            else:
                uncached_contexts.append(nctx)

        # If all nodes are already cached, return immediately!
        if not uncached_contexts and cached_node_profiles:
            meta = ProfilingMeta(
                session_id=session_id,
                nodes_profiled_count=len(cached_node_profiles),
                model=self.model_name,
                latency_sec=time.time() - start_time,
                cache_hit=True,
                success=True,
            )
            return WorkflowProfile(workflow_id=workflow_id, purpose="Cached workflow", node_profiles=cached_node_profiles)

        # Construct prompt for uncached nodes
        sub_context = WorkflowContext(
            session_id=session_id,
            workflow_id=workflow_id,
            total_nodes=len(uncached_contexts),
            node_ids=[n.node_id for n in uncached_contexts],
            execution_graph=context.execution_graph,
            node_contexts=uncached_contexts,
            global_inputs_excerpt=context.global_inputs_excerpt,
        )

        prompt = build_workflow_profiler_prompt(sub_context, self.metric_catalog)

        try:
            llm_raw = get_llm_response(prompt, system_prompt=SYSTEM_PROFILER_PROMPT, model_name=self.model_name)
            if not llm_raw:
                raise RuntimeError("LLM returned empty response or API key unavailable")

            wf_profile = self.parse_and_validate_llm_output(llm_raw, session_id, sub_context)

            # Save newly generated profiles to cache & store
            for prof in wf_profile.node_profiles:
                self.cache.set(prof)
                cached_node_profiles.append(prof)

            meta = ProfilingMeta(
                session_id=session_id,
                nodes_profiled_count=len(wf_profile.node_profiles),
                model=self.model_name,
                latency_sec=time.time() - start_time,
                cache_hit=False,
                success=True,
            )
            return WorkflowProfile(
                workflow_id=workflow_id,
                purpose=wf_profile.purpose,
                node_profiles=cached_node_profiles,
            )

        except Exception as e:
            print(f"[WorkflowProfiler Warning] LLM profiling failed: {e}. Falling back to heuristic profiles.")
            fallback_profiles = []
            for nctx in uncached_contexts:
                fb = self.create_fallback_profile(session_id, nctx.node_id)
                self.cache.set(fb)
                fallback_profiles.append(fb)

            all_profiles = cached_node_profiles + fallback_profiles
            return WorkflowProfile(
                workflow_id=workflow_id,
                purpose="Fallback workflow profile",
                node_profiles=all_profiles,
            )

    def profile_workflow_async(
        self,
        session_id: str,
        traces: List[Dict[str, Any]],
        workflow_id: str = "default_workflow",
    ):
        """Asynchronously profiles a workflow in a background thread without blocking execution."""
        _PROFILER_THREAD_POOL.submit(self.profile_workflow, session_id, traces, workflow_id)
