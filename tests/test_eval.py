import pytest
from agenteval.eval.metrics import EvaluationEngine, cosine_similarity

def test_json_validity_metric():
    """Checks that JSON validity correctly parses valid structures and rejects malformed ones."""
    engine = EvaluationEngine()
    
    # Valid cases
    assert engine.evaluate_json_validity('{"key": "value"}') == 1.0
    assert engine.evaluate_json_validity('[1, 2, 3]') == 1.0
    
    # Invalid cases
    assert engine.evaluate_json_validity('{"key": value}') == 0.0
    assert engine.evaluate_json_validity('Plain string text') == 0.0
    assert engine.evaluate_json_validity(None) == 0.0

def test_cosine_similarity_metric():
    """Checks cosine similarity math, including orthogonal and zero-vector edge cases."""
    assert pytest.approx(cosine_similarity([1, 0], [1, 0])) == 1.0
    assert pytest.approx(cosine_similarity([1, 0], [0, 1])) == 0.0
    assert cosine_similarity([0, 0], [3, 4]) == 0.0

def test_latency_calculation():
    """Checks that duration calculations handle ISO timestamps correctly."""
    engine = EvaluationEngine()
    
    start = "2026-07-09T12:00:00"
    end = "2026-07-09T12:00:05.500"
    
    # Expected: 5.5 seconds difference
    assert engine.evaluate_latency(start, end) == 5.5
    
    # Handles error gracefully
    assert engine.evaluate_latency("invalid-start", "invalid-end") == 0.0

def test_groundedness_metric():
    """Validates that groundedness returns a dictionary with score and judge_mode."""
    engine = EvaluationEngine()
    res = engine.evaluate_groundedness(
        "The agent is running.", 
        [{"text": "AgentEval helps teams debug agents."}]
    )
    assert isinstance(res, dict)
    assert "score" in res
    assert "judge_mode" in res
    assert res["status"] in {"complete", "fallback", "unavailable"}
    assert res["score"] is None or 0.0 <= res["score"] <= 1.0

def test_retrieval_evidence_uses_embeddings_when_available():
    """Ensures retrieval evidence can use embeddings and surfaces top-k similarity data."""
    engine = EvaluationEngine()
    res = engine.evaluate_retrieval_evidence(
        "What is AgentEval?",
        [
            {"text": "AgentEval is a diagnosis system.", "embedding": [1.0, 0.0]},
            {"text": "Other text", "embedding": [0.0, 1.0]},
        ],
        query_embedding=[1.0, 0.0],
    )
    assert res["status"] == "complete"
    assert res["method"] == "cosine_similarity"
    assert res["score"] == pytest.approx(0.5)
    assert res["max_similarity"] == pytest.approx(1.0)
    assert res["top_k_scores"][0] == pytest.approx(1.0)

def test_retrieval_evidence_unavailable_without_scores():
    """Ensures the evaluator does not invent retrieval evidence when none exists."""
    engine = EvaluationEngine()
    res = engine.evaluate_retrieval_evidence("query", [{"text": "doc without score"}])
    assert res["status"] == "unavailable"
    assert res["score"] is None

def test_instruction_following_metric():
    """Validates instruction following metric structure."""
    engine = EvaluationEngine()
    res = engine.evaluate_instruction_following(
        "Return output in clean markdown format.",
        "Here is the markdown response."
    )
    assert isinstance(res, dict)
    assert "score" in res
    assert "judge_mode" in res
    assert res["status"] in {"complete", "fallback"}
    assert 0.0 <= res["score"] <= 1.0

def test_judge_mode_llm_if_key_present(monkeypatch):
    """Asserts that judge_mode is 'llm' when the GEMINI_API_KEY is present in the environment."""
    import agenteval.eval.metrics
    if agenteval.eval.metrics.litellm is None:
        pytest.skip("litellm is not installed in this environment")
    
    monkeypatch.setattr(agenteval.eval.metrics, "CUMULATIVE_COST", 0.0)
    monkeypatch.setenv("AGENTEVAL_MAX_COST_USD_PER_RUN", "10.00")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    
    def mock_completion(*args, **kwargs):
        messages = kwargs.get("messages", [])
        prompt = messages[-1]["content"] if messages else ""
        
        class MockChoices:
            def __init__(self, content):
                class MockMessage:
                    def __init__(self, c):
                        self.content = c
                self.message = MockMessage(content)
                
        content = "YES"
        if "Decompose" in prompt:
            content = '["The agent is running."]'
            
        class MockResponse:
            def __init__(self, c):
                self.choices = [MockChoices(c)]
                self.usage = {
                    "prompt_tokens": 10,
                    "completion_tokens": 5
                }
                
        return MockResponse(content)
        
    monkeypatch.setattr(agenteval.eval.metrics.litellm, "completion", mock_completion)
    
    engine = EvaluationEngine(mode="live")
    res = engine.evaluate_groundedness(
        "The agent is running.", 
        [{"text": "AgentEval helps teams debug agents."}]
    )
    assert res["judge_mode"] == "llm"

def test_cost_guard_activation(monkeypatch):
    """Verifies that cost guard halts LLM calls and falls back to heuristics when run cost exceeds limit."""
    import os
    import agenteval.eval.metrics
    
    monkeypatch.setattr(agenteval.eval.metrics, "CUMULATIVE_COST", 0.0)
    monkeypatch.setenv("AGENTEVAL_MAX_COST_USD_PER_RUN", "0.0000001")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-to-force-llm-path")
    
    engine = EvaluationEngine(mode="live")
    
    res = engine.evaluate_instruction_following(
        "Return output in clean markdown format.",
        "Here is the markdown response."
    )
    assert res["judge_mode"] == "heuristic_fallback"
