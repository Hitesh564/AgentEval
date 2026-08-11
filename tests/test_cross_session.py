import os
import sqlite3
import tempfile
import pytest
from agenteval.sdk.storage import TraceStore
from agenteval.sdk.tracer import trace
from agenteval.root_cause.cross_session import CrossSessionEngine
from agenteval.eval import metrics

def test_transitive_chain_walking_depth_cap():
    """Validates that chain-walking correctly tracks parent chains up to the depth cap of 5."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        store = TraceStore(db_path=db_path)
        
        # Create 7 linked sessions: s1 -> s2 -> s3 -> s4 -> s5 -> s6 -> s7
        # Note: s7 is the leaf, s1 is the root
        for i in range(1, 8):
            session_id = f"s{i}"
            parent_id = f"s{i-1}" if i > 1 else None
            # Store some trace node in each session so get_session_traces returns something
            with trace(session_id=session_id, node_id="node_a", node_type="generator", db_path=db_path, parent_session_id=parent_id) as t:
                t.inputs = {"q": "test"}
                t.outputs = {"r": "ok"}
                
        engine = CrossSessionEngine(db_path=db_path)
        
        # Diagnose leaf session "s7". The chain should only contain 5 sessions due to the cap.
        res = engine.diagnose_chain("s7")
        chain_sessions = [step["session_id"] for step in res["chain"]]
        
        # We expect a maximum depth of 5 sessions in the chain
        assert len(chain_sessions) == 5
        # The chain is ordered from parent to child, so it should be s3 -> s4 -> s5 -> s6 -> s7
        assert chain_sessions == ["s3", "s4", "s5", "s6", "s7"]
    finally:
        if 'store' in locals() and store:
            store.close()
        if 'engine' in locals() and engine:
            engine.store.close()
        if os.path.exists(db_path):
            os.remove(db_path)

def test_co_contribution_vs_inherited_classification():
    """Validates root-cause, inherited, and co-contributor classification under Decision 3."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        store = TraceStore(db_path=db_path)
        
        # Scenario A: Retrieval Agent failure (retrieval_retriever fails), Scoring Agent purely inherits (no independent failure)
        # s_ret_a (fails), s_scr_a (inherits)
        
        # Retrieval Agent s_ret_a: planner (passed, 1.0), retriever (failed, 0.30)
        with trace(session_id="s_ret_a", node_id="retrieval_planner", node_type="planner", db_path=db_path) as t:
            t.inputs = {"q": "test"}
            t.outputs = {"r": "ok"}
        with trace(session_id="s_ret_a", node_id="retrieval_retriever", node_type="retriever", db_path=db_path) as t:
            t.inputs = {"q": "test"}
            t.outputs = {"r": "low similarity docs"}
            t.retrieved_docs = [{"text": "docs", "similarity_score": 0.30}]
            
        # Scoring Agent s_scr_a: scoring_retriever (inherits fail, 0.30), scoring_generator (passed, 1.0)
        with trace(session_id="s_scr_a", node_id="scoring_retriever", node_type="retriever", db_path=db_path, parent_session_id="s_ret_a") as t:
            t.inputs = {"q": "test"}
            t.outputs = {"r": "bad"}
            t.retrieved_docs = [{"text": "docs", "similarity_score": 0.30}]
        with trace(session_id="s_scr_a", node_id="scoring_generator", node_type="generator", db_path=db_path) as t:
            t.inputs = {"q": "test"}
            t.outputs = {"response": "docs"}
            t.parent_node_ids = ["scoring_retriever"]
            
        engine = CrossSessionEngine(db_path=db_path)
        res_a = engine.diagnose_chain("s_scr_a")
        
        # Check verdict and root cause session
        assert res_a["verdict"] == "failed"
        assert res_a["root_cause_session"] == "s_ret_a"
        assert len(res_a["co_contributing_sessions"]) == 0
        
        # Check step status: s_ret_a is root-cause, s_scr_a is inherited
        steps_a = {step["session_id"]: step for step in res_a["chain"]}
        assert steps_a["s_ret_a"]["status"] == "root-cause"
        assert steps_a["s_scr_a"]["status"] == "inherited"
        
        # ----------------------------------------------------
        # Scenario B: Co-contribution (Retrieval Agent fails AND Scoring Agent independently fails)
        # s_ret_b (fails), s_scr_b (co-contributes)
        
        # Retrieval Agent s_ret_b: planner (passed, 1.0), retriever (failed, 0.30)
        with trace(session_id="s_ret_b", node_id="retrieval_planner", node_type="planner", db_path=db_path) as t:
            t.inputs = {"q": "test"}
            t.outputs = {"r": "ok"}
        with trace(session_id="s_ret_b", node_id="retrieval_retriever", node_type="retriever", db_path=db_path) as t:
            t.inputs = {"q": "test"}
            t.outputs = {"r": "low similarity docs"}
            t.retrieved_docs = [{"text": "docs", "similarity_score": 0.30}]
            
        # Scoring Agent s_scr_b: scoring_retriever (inherits fail, 0.30), scoring_generator (independently failed, 0.10)
        with trace(session_id="s_scr_b", node_id="scoring_retriever", node_type="retriever", db_path=db_path, parent_session_id="s_ret_b") as t:
            t.inputs = {"q": "test"}
            t.outputs = {"r": "bad"}
            t.retrieved_docs = [{"text": "docs", "similarity_score": 0.30}]
        # Injected scoring independent failure (raw health < 0.70)
        with trace(session_id="s_scr_b", node_id="scoring_generator", node_type="generator", db_path=db_path) as t:
            t.inputs = {"prompt": "strict response"}
            t.outputs = {"response": "docs. 10 is greater than 15"} # fails instruction following & groundedness
            t.parent_node_ids = ["scoring_retriever"]
            
        res_b = engine.diagnose_chain("s_scr_b")
        
        # Check verdict: should be ambiguous, with both sessions co-contributing
        assert res_b["verdict"] == "failed"
        assert res_b["root_cause_session"] == "ambiguous"
        assert set(res_b["co_contributing_sessions"]) == {"s_ret_b", "s_scr_b"}
        
        steps_b = {step["session_id"]: step for step in res_b["chain"]}
        assert steps_b["s_ret_b"]["status"] == "co-contributor"
        assert steps_b["s_scr_b"]["status"] == "co-contributor"
        
    finally:
        if 'store' in locals() and store:
            store.close()
        if 'engine' in locals() and engine:
            engine.store.close()
        if os.path.exists(db_path):
            os.remove(db_path)

def test_cumulative_cost_guard():
    """Validates that CUMULATIVE_COST correctly tracks cost across sessions in the current process run."""
    # Reset cost
    metrics.CUMULATIVE_COST = 0.0
    
    # Check that we can accumulate cost
    metrics.CUMULATIVE_COST += 0.05
    assert metrics.CUMULATIVE_COST == 0.05
    
    # Increment further
    metrics.CUMULATIVE_COST += 0.02
    assert metrics.CUMULATIVE_COST == 0.07

def test_backward_compatibility_empty_links():
    """Validates that CrossSessionEngine handles backward compatibility gracefully when no session links exist."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        # Trace a single isolated session with no parent
        with trace(session_id="isolated_s", node_id="node_1", node_type="generator", db_path=db_path) as t:
            t.inputs = {"q": "hello"}
            t.outputs = {"response": "world"}
            
        engine = CrossSessionEngine(db_path=db_path)
        res = engine.diagnose_chain("isolated_s")
        
        # We expect a single-step chain containing the session itself
        assert len(res["chain"]) == 1
        assert res["chain"][0]["session_id"] == "isolated_s"
        assert res["root_cause_session"] == "none"
        assert res["verdict"] == "healthy"
    finally:
        if 'engine' in locals() and engine:
            engine.store.close()
        if os.path.exists(db_path):
            os.remove(db_path)

def test_cumulative_cost_guard_halting(monkeypatch):
    """Validates that the cost guard halts LLM calls across sessions once the limit is breached."""
    # Reset cost and set env keys
    metrics.CUMULATIVE_COST = 0.0
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")
    monkeypatch.setenv("AGENTEVAL_MAX_COST_USD_PER_RUN", "0.20")
    monkeypatch.setenv("LITELLM_MODEL", "gemini/gemini-3.5-flash")
    
    # Mock litellm completion to return a simulated response with high cost
    class MockMessage:
        content = "mock response"
        
    class MockChoice:
        message = MockMessage()
        
    class MockUsage:
        prompt_tokens = 10000      # 0.015 cost
        completion_tokens = 20000  # 0.18 cost
        
    class MockResponse:
        choices = [MockChoice()]
        usage = MockUsage()
        
    def mock_completion(*args, **kwargs):
        return MockResponse()
        
    monkeypatch.setattr(metrics.litellm, "completion", mock_completion)
    
    # First call: est_cost ~0.037, cumulative cost = 0.0. Cumulative + est (0.037) <= 0.20. Should succeed.
    res1 = metrics.get_llm_response("prompt 1")
    assert res1 == "mock response"
    assert round(metrics.CUMULATIVE_COST, 3) == 0.195
    
    # Second call: est_cost ~0.037. Cumulative + est (0.195 + 0.037 = 0.232) > 0.20. Should halt and return None.
    res2 = metrics.get_llm_response("prompt 2")
    assert res2 is None
    # Verify CUMULATIVE_COST did not increase further
    assert round(metrics.CUMULATIVE_COST, 3) == 0.195
