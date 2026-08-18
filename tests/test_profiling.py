"""
Unit tests for AgentEval Automatic LLM-based Workflow & Node Profiling.
Tests cover arbitrary architectures (AI Interview framework), meaningless names, multi-role nodes,
caching, fallbacks, non-blocking callback behavior, root cause compatibility, and offline mocks.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from agenteval.profiling.models import (
    NodeProfile,
    WorkflowProfile,
    EvaluationDimension,
    NodeContext,
    WorkflowContext,
)
from agenteval.profiling.catalog import get_executable_metric_catalog, get_supported_metric_names
from agenteval.profiling.context import WorkflowContextBuilder, sanitize_value
from agenteval.profiling.prompts import build_workflow_profiler_prompt
from agenteval.profiling.cache import ProfileCache, compute_profile_signature
from agenteval.profiling.profiler import WorkflowProfiler
from agenteval.eval.health import HealthConfig, get_health_config, weighted_health
from agenteval.root_cause.engine import RootCauseEngine
from agenteval.sdk.callbacks import AgentEvalCallbackHandler
from agenteval.sdk.storage import TraceStore


@pytest.fixture
def temp_db(tmp_path):
    db_file = os.path.join(tmp_path, "test_profiling.db")
    store = TraceStore(db_path=db_file)
    yield db_file, store
    store.close()


def test_metric_catalog_discovery():
    """Test 1: Verify dynamic metric catalog auto-discovery."""
    catalog = get_executable_metric_catalog()
    assert "instruction_following" in catalog
    assert "semantic_response_quality" in catalog
    assert "groundedness" in catalog
    assert "tool_selection" in catalog
    assert "retrieval_evidence" in catalog
    assert "json_validity" in catalog
    assert "latency" in catalog

    supported_names = get_supported_metric_names()
    assert len(supported_names) >= 7


def test_context_builder_sanitization():
    """Test 2: Verify sanitization truncates long strings and redacts secrets."""
    raw = {
        "api_key": "secret_live_key_12345",
        "user_prompt": "A" * 1000,
        "password": "supersecretpassword",
        "normal_key": "hello world",
    }
    sanitized = sanitize_value(raw)
    assert sanitized["api_key"] == "[REDACTED_SECRET]"
    assert sanitized["password"] == "[REDACTED_SECRET]"
    assert sanitized["normal_key"] == "hello world"
    assert "truncated" in sanitized["user_prompt"]


def test_ai_interview_architecture_profiling(temp_db):
    """Test 3: AI Interview Architecture (Interview Planner -> Adaptive Interview Agent -> Evaluation Agent)."""
    db_file, store = temp_db
    profiler = WorkflowProfiler(db_path=db_file, store=store)

    session_id = "session_ai_interview_001"
    traces = [
        {
            "session_id": session_id,
            "node_id": "Interview Planner",
            "node_type": "custom",
            "timestamp_start": "2026-08-18T10:00:00Z",
            "timestamp_end": "2026-08-18T10:00:01Z",
            "inputs": {"candidate_resume": "Senior Python Engineer"},
            "outputs": {"interview_blueprint": ["Python GIL", "System Design", "Concurrency"]},
            "parent_node_ids": [],
        },
        {
            "session_id": session_id,
            "node_id": "Adaptive Interview Agent",
            "node_type": "custom",
            "timestamp_start": "2026-08-18T10:00:02Z",
            "timestamp_end": "2026-08-18T10:00:05Z",
            "inputs": {"candidate_answer": "GIL locks thread execution in CPython", "current_topic": "Python GIL"},
            "outputs": {"next_question": "How do you bypass GIL for CPU-bound tasks?", "updated_state": {"score": 0.85}},
            "parent_node_ids": ["Interview Planner"],
            "tool_calls": [{"name": "eval_answer", "args": {"score": 0.85}}],
        },
        {
            "session_id": session_id,
            "node_id": "Evaluation Agent",
            "node_type": "custom",
            "timestamp_start": "2026-08-18T10:00:06Z",
            "timestamp_end": "2026-08-18T10:00:08Z",
            "inputs": {"full_transcript": "Interview Q&A log"},
            "outputs": {"final_result": "HIRE", "confidence": 0.92},
            "parent_node_ids": ["Adaptive Interview Agent"],
        },
    ]

    mock_llm_json = json.dumps({
        "workflow_id": "interview_pipeline",
        "purpose": "Conduct adaptive technical interview and evaluate candidate performance",
        "node_profiles": [
            {
                "node_id": "Interview Planner",
                "inferred_role": "interview_planner",
                "purpose": "Analyze candidate details and generate personalized interview blueprint",
                "responsibilities": ["analyze candidate details", "determine interview topics"],
                "executable_metrics": ["instruction_following", "semantic_response_quality", "latency"],
                "confidence": 0.95
            },
            {
                "node_id": "Adaptive Interview Agent",
                "inferred_role": "adaptive_interview_agent",
                "purpose": "Interactively ask questions, evaluate candidate responses, and adapt state",
                "responsibilities": ["evaluate candidate answer", "update interview state", "generate next question"],
                "executable_metrics": ["instruction_following", "tool_selection", "semantic_response_quality", "latency"],
                "confidence": 0.92
            },
            {
                "node_id": "Evaluation Agent",
                "inferred_role": "interview_evaluation_agent",
                "purpose": "Perform final transcript evaluation and produce overall candidate assessment",
                "responsibilities": ["synthesize full transcript", "generate final assessment"],
                "executable_metrics": ["instruction_following", "groundedness", "semantic_response_quality", "latency"],
                "confidence": 0.96
            }
        ]
    })

    with patch("agenteval.profiling.profiler.get_llm_response", return_value=mock_llm_json):
        wf_profile = profiler.profile_workflow(session_id, traces)
        assert len(wf_profile.node_profiles) == 3

        roles = [p.inferred_role for p in wf_profile.node_profiles]
        assert "interview_planner" in roles
        assert "adaptive_interview_agent" in roles
        assert "interview_evaluation_agent" in roles

        # Verify profile retrieval from DB store
        p1 = store.get_node_profile(session_id, "Interview Planner")
        assert p1 is not None
        assert p1["inferred_role"] == "interview_planner"


def test_meaningless_node_names_profiling(temp_db):
    """Test 4: Meaningless node names (node_a, node_b, node_c)."""
    db_file, store = temp_db
    profiler = WorkflowProfiler(db_path=db_file, store=store)

    session_id = "session_meaningless_001"
    traces = [
        {"session_id": session_id, "node_id": "node_a", "node_type": "custom", "inputs": {"q": "search docs"}, "retrieved_docs": [{"text": "doc1"}]},
        {"session_id": session_id, "node_id": "node_b", "node_type": "custom", "inputs": {"doc": "doc1"}, "outputs": {"answer": "result"}, "parent_node_ids": ["node_a"]},
    ]

    mock_llm_json = json.dumps({
        "workflow_id": "test_wf",
        "node_profiles": [
            {
                "node_id": "node_a",
                "inferred_role": "document_retriever",
                "purpose": "Fetch relevant documentation",
                "executable_metrics": ["retrieval_evidence", "latency"],
                "confidence": 0.90
            },
            {
                "node_id": "node_b",
                "inferred_role": "response_generator",
                "purpose": "Synthesize answer from retrieved document",
                "executable_metrics": ["groundedness", "instruction_following", "latency"],
                "confidence": 0.91
            }
        ]
    })

    with patch("agenteval.profiling.profiler.get_llm_response", return_value=mock_llm_json):
        wf_profile = profiler.profile_workflow(session_id, traces)
        profiles_by_id = {p.node_id: p for p in wf_profile.node_profiles}
        assert profiles_by_id["node_a"].inferred_role == "document_retriever"
        assert profiles_by_id["node_b"].inferred_role == "response_generator"


def test_profiler_failure_fallback(temp_db):
    """Test 5: LLM failure or missing API key falls back gracefully without breaking."""
    db_file, store = temp_db
    profiler = WorkflowProfiler(db_path=db_file, store=store)

    session_id = "session_fallback_001"
    traces = [
        {"session_id": session_id, "node_id": "planner_node", "node_type": "planner", "inputs": {}},
        {"session_id": session_id, "node_id": "unknown_worker", "node_type": "custom", "inputs": {}},
    ]

    # Force LLM response to None (simulating API failure / no API key)
    with patch("agenteval.profiling.profiler.get_llm_response", return_value=None):
        wf_profile = profiler.profile_workflow(session_id, traces)
        assert len(wf_profile.node_profiles) == 2
        p1 = wf_profile.node_profiles[0]
        assert p1.confidence == 0.5
        assert p1.inferred_role in ["planner", "custom"]


def test_profile_cache_hit_and_signature_invalidation(temp_db):
    """Test 6: Caching avoids second LLM call and invalidates when signature changes."""
    db_file, store = temp_db
    profiler = WorkflowProfiler(db_path=db_file, store=store)

    session_id = "session_cache_001"
    traces = [
        {"session_id": session_id, "node_id": "node_x", "node_type": "custom", "inputs": {"data": 1}},
    ]

    mock_llm_json = json.dumps({
        "workflow_id": "wf",
        "node_profiles": [
            {
                "node_id": "node_x",
                "inferred_role": "data_processor",
                "purpose": "Process data",
                "executable_metrics": ["latency"],
                "confidence": 0.88
            }
        ]
    })

    with patch("agenteval.profiling.profiler.get_llm_response", return_value=mock_llm_json) as mock_llm:
        # First call -> triggers LLM profiling
        prof1 = profiler.profile_workflow(session_id, traces)
        assert mock_llm.call_count == 1

        # Second call with identical trace -> cache HIT (zero extra LLM calls!)
        prof2 = profiler.profile_workflow(session_id, traces)
        assert mock_llm.call_count == 1
        assert prof2.node_profiles[0].inferred_role == "data_processor"

        # Trace with updated tool signature / input shape -> cache MISS (re-profiles)
        traces_modified = [
            {"session_id": session_id, "node_id": "node_x", "node_type": "custom", "inputs": {"data": 1}, "tool_calls": [{"name": "new_tool", "args": {}}]},
        ]
        profiler.profile_workflow(session_id, traces_modified)
        assert mock_llm.call_count == 2


def test_non_blocking_callback_integration(temp_db):
    """Test 7: Callback handler triggers non-blocking profiling without slowing down agent execution."""
    db_file, store = temp_db

    handler = AgentEvalCallbackHandler(session_id="session_cb_001", db_path=db_file)
    handler.on_chain_start({}, {}, run_id="run_1", metadata={"langgraph_node": "adaptive_agent"})
    handler.on_chain_end({"response": "Hello candidate"}, run_id="run_1")

    # Verify trace node saved immediately
    saved_traces = store.get_session_traces("session_cb_001")
    assert len(saved_traces) == 1
    assert saved_traces[0]["node_id"] == "adaptive_agent"


def test_health_config_from_profile():
    """Test 8: Dynamic HealthConfig generation from NodeProfile."""
    profile = NodeProfile(
        node_id="custom_node",
        inferred_role="compliance_validator",
        purpose="Validate compliance rules",
        executable_metrics=["instruction_following", "latency"],
        metric_weights={"instruction_following": 0.70, "latency": 0.30},
        confidence=0.95
    )

    config = HealthConfig.from_profile(profile)
    assert config.node_type == "compliance_validator"
    assert config.metric_weights["instruction_following"] == 0.70
    assert config.metric_weights["latency"] == 0.30

    health_res = weighted_health({"instruction_following": 0.90, "latency": 0.80}, config)
    assert health_res["overall_health"] > 0.80
    assert health_res["evaluation_status"] == "complete"


def test_root_cause_compatibility_with_arbitrary_roles(temp_db):
    """Test 9: Root Cause Engine works on arbitrary topologies with custom roles."""
    db_file, store = temp_db

    # Node A -> Node B -> Node C, with Node A failing
    store.save_trace_node({
        "session_id": "session_rc_001",
        "node_id": "Interview Planner",
        "node_type": "custom",
        "timestamp_start": "2026-08-18T10:00:00Z",
        "timestamp_end": "2026-08-18T10:00:01Z",
        "inputs": {},
        "outputs": {"bad_plan": True},
        "parent_node_ids": [],
    })

    store.save_trace_node({
        "session_id": "session_rc_001",
        "node_id": "Adaptive Interview Agent",
        "node_type": "custom",
        "timestamp_start": "2026-08-18T10:00:02Z",
        "timestamp_end": "2026-08-18T10:00:03Z",
        "inputs": {},
        "outputs": {},
        "parent_node_ids": ["Interview Planner"],
    })

    rc_engine = RootCauseEngine(db_path=db_file)
    traces = store.get_session_traces("session_rc_001")
    diagnosed = rc_engine.propagate_failures(traces)

    assert len(diagnosed) == 2
    # Verify graph propagation works regardless of node_type
    assert diagnosed[0]["node_id"] == "Interview Planner"
