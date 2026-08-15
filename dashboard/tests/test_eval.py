import pytest
import pytest

from agenteval.eval.metrics import EvaluationEngine, cosine_similarity
from agenteval.eval.health import get_health_config, weighted_health
from agenteval.eval.calibration import (
    select_threshold,
    calibrate_threshold,
    balanced_accuracy,
    roc_auc_score,
    pr_auc_score,
    ConfidenceCalibration,
    expected_calibration_error,
    brier_score,
    reliability_diagram,
)

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

def test_tool_selection_semantic_ranking_with_embeddings():
    """Checks that tool selection can rank candidates with embeddings and compute a margin."""
    engine = EvaluationEngine()
    res = engine.evaluate_tool_selection(
        chosen_tool="search_docs",
        candidate_tools=[
            {"name": "search_docs", "embedding": [1.0, 0.0]},
            {"name": "lookup_policy", "embedding": [0.7, 0.7]},
            {"name": "small_talk", "embedding": [0.0, 1.0]},
        ],
        expected_tool="search_docs",
        query_embedding=[1.0, 0.0],
    )
    assert res["status"] == "complete"
    assert res["method"] == "cosine_similarity"
    assert res["score"] == 1.0
    assert res["chosen_score"] == pytest.approx(1.0)
    assert res["runner_up_score"] == pytest.approx(0.70710678, rel=1e-6)
    assert res["margin"] == pytest.approx(0.29289322, rel=1e-6)
    assert res["candidate_tools"][0]["similarity"] == pytest.approx(1.0)

def test_tool_selection_missing_embeddings_is_not_fabricated():
    """Checks that missing embeddings do not fabricate semantic confidence."""
    engine = EvaluationEngine()
    res = engine.evaluate_tool_selection(
        chosen_tool="search_docs",
        candidate_tools=["search_docs", "lookup_policy"],
        query_embedding=None,
        expected_tool=None,
    )
    assert res["status"] == "unavailable"
    assert res["score"] is None
    assert res["chosen_score"] is None

def test_tool_selection_duplicate_names_and_zero_vectors():
    """Checks duplicate tool names and zero vectors do not break ranking."""
    engine = EvaluationEngine()
    res = engine.evaluate_tool_selection(
        chosen_tool="search_docs",
        candidate_tools=[
            {"name": "search_docs", "embedding": [0.0, 0.0]},
            {"name": "search_docs", "embedding": [1.0, 0.0]},
        ],
        expected_tool="search_docs",
        query_embedding=[1.0, 0.0],
    )
    assert res["score"] == 1.0
    assert res["candidate_tools"][0]["similarity"] == 0.0
    assert res["candidate_tools"][1]["similarity"] == 1.0

def test_weighted_health_uses_configured_weights():
    """Checks that weighted health is computed from the configured metric mix."""
    config = get_health_config("generator")
    health = weighted_health(
        {
            "groundedness": 0.50,
            "instruction_following": 0.90,
            "schema_validity": 1.0,
            "latency": 0.80,
        },
        config,
    )
    expected = (0.35 * 0.50 + 0.25 * 0.90 + 0.20 * 1.0 + 0.20 * 0.80)
    assert health["overall_health"] == pytest.approx(expected)
    assert health["weakest_dimension"] == "groundedness"
    assert "groundedness" in health["failed_dimensions"]

def test_threshold_selection_prefers_best_f1():
    """Checks threshold selection on labeled calibration examples."""
    threshold, metrics = select_threshold([0.1, 0.2, 0.8, 0.9], [1, 1, 0, 0])
    assert 0.2 <= threshold <= 0.8
    assert metrics["f1"] >= 0.5
    assert balanced_accuracy([1, 1, 0, 0], [1, 1, 0, 0]) == 1.0

def test_calibration_result_metadata():
    """Checks calibration metadata is versioned and split-aware."""
    result = calibrate_threshold(
        metric="retrieval",
        values=[0.1, 0.2, 0.8, 0.9],
        labels=[1, 1, 0, 0],
        dataset="unit-test",
        split="calibration",
        calibration_version="v1",
    )
    assert result.metric == "retrieval"
    assert result.dataset == "unit-test"
    assert result.split == "calibration"
    assert result.calibration_version == "v1"
    assert result.threshold is not None


def test_threshold_calibration_uses_failure_score_for_auc():
    """Checks that lower health maps to higher failure score for AUC calculations."""
    result = calibrate_threshold(
        metric="overall_health",
        values=[0.1, 0.2, 0.8, 0.9],
        labels=[1, 1, 0, 0],
        dataset="unit-test",
        split="calibration",
        calibration_version="v1",
    )
    assert result.roc_auc == pytest.approx(1.0)
    assert result.pr_auc == pytest.approx(1.0)


def test_failure_score_auc_direction():
    """Checks that reversed ranking does not report a high AUC."""
    failure_scores_good = [0.9, 0.8, 0.2, 0.1]
    failure_scores_bad = [0.1, 0.2, 0.8, 0.9]
    labels = [1, 1, 0, 0]
    assert roc_auc_score(labels, failure_scores_good) == pytest.approx(1.0)
    assert pr_auc_score(labels, failure_scores_good) == pytest.approx(1.0)
    assert roc_auc_score(labels, failure_scores_bad) == pytest.approx(0.0)
    assert pr_auc_score(labels, failure_scores_bad) < 0.8

def test_confidence_calibration_metrics_and_identity_fallback():
    """Checks calibrated confidence helpers return calibrated probabilities and calibration metrics."""
    calibrator = ConfidenceCalibration.identity()
    fallback = calibrator.calibrate(0.42)
    assert fallback["raw_score"] == pytest.approx(0.42)
    assert fallback["calibrated_probability"] is None
    assert fallback["confidence_calibrated"] is False
    assert fallback["status"] == "unavailable"

    report = expected_calibration_error([0, 0, 1, 1], [0.05, 0.15, 0.85, 0.95], n_bins=2)
    assert report["ece"] >= 0.0
    assert len(report["bins"]) == 2
    assert brier_score([0, 0, 1, 1], [0.05, 0.15, 0.85, 0.95]) < 0.03
    diag = reliability_diagram([0, 0, 1, 1], [0.05, 0.15, 0.85, 0.95], n_bins=2)
    assert len(diag) == 2

def test_calibration_artifact_round_trip(tmp_path):
    """Checks calibration artifacts can be saved and loaded without losing metadata."""
    from agenteval.eval.calibration import ThresholdCalibrationArtifact

    artifact = ThresholdCalibrationArtifact(
        metric="overall_health",
        threshold=0.71,
        precision=0.8,
        recall=0.75,
        f1=0.77,
        roc_auc=0.9,
        pr_auc=0.88,
        split="calibration",
        dataset="unit-test",
        dataset_version="v1",
        calibration_version="2026-08",
        timestamp="2026-08-11T00:00:00Z",
        configuration={"node_type": "generator"},
    )
    path = tmp_path / "threshold.json"
    artifact.save_json(str(path))
    loaded = ThresholdCalibrationArtifact.load_json(str(path))
    assert loaded.threshold == pytest.approx(0.71)
    assert loaded.dataset == "unit-test"
    assert loaded.configuration["node_type"] == "generator"

def test_temperature_and_isotonic_calibration_fit():
    """Checks both calibration strategies produce monotone, versioned artifacts."""
    temperature = ConfidenceCalibration.fit_temperature_scaling(
        [0.1, 0.2, 0.8, 0.9],
        [0, 0, 1, 1],
        version="v-temp",
    )
    assert temperature.method == "temperature_scaling"
    assert temperature.status == "complete"
    assert 0.25 <= temperature.temperature <= 5.0
    assert temperature.predict(0.2) < temperature.predict(0.8)

    isotonic = ConfidenceCalibration.fit_isotonic(
        [0.1, 0.2, 0.8, 0.9],
        [0, 0, 1, 1],
        version="v-iso",
    )
    assert isotonic.method == "isotonic"
    assert isotonic.status == "complete"
    assert isotonic.predict(0.2) <= isotonic.predict(0.8)
    summary = isotonic.summary([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1])
    assert "ece" in summary
    assert "brier_score" in summary


def test_confidence_calibration_round_trip(tmp_path):
    """Checks fitted confidence calibrators can be saved and loaded."""
    calibrator = ConfidenceCalibration.fit_temperature_scaling(
        [0.1, 0.2, 0.8, 0.9],
        [0, 0, 1, 1],
        version="v-save",
    )
    path = tmp_path / "calibrator.json"
    calibrator.save_json(str(path))
    loaded = ConfidenceCalibration.load_json(str(path))
    assert loaded.method == calibrator.method
    assert loaded.status == calibrator.status
    assert loaded.predict(0.2) == pytest.approx(calibrator.predict(0.2))

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

def test_judge_mode_llm_if_key_present(monkeypatch, tmp_path):
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
    
    engine = EvaluationEngine(db_path=str(tmp_path / "judge_mode.db"), mode="live")
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
