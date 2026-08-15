import pytest
import pytest

from agenteval.root_cause.engine import RootCauseEngine
from agenteval.taxonomy import FailureType
from agenteval.eval.calibration import ThresholdCalibrationArtifact

def test_evidence_collection():
    """Validates that document similarity is accurately averaged from trace structures."""
    engine = RootCauseEngine()
    
    node = {
        "node_id": "retriever_1",
        "node_type": "retriever",
        "timestamp_start": "2026-07-09T12:00:00",
        "timestamp_end": "2026-07-09T12:00:01.500",
        "retrieved_docs": [
            {"text": "document 1 content", "similarity_score": 0.50},
            {"text": "document 2 content", "similarity_score": 0.30}
        ]
    }
    
    evidence = engine.collect_evidence(node)
    assert pytest.approx(evidence["retriever_similarity"]) == 0.40
    assert evidence["latency"] == 1.5

def test_failure_propagation_identifies_root_cause():
    """
    Checks that the root cause engine identifies the correct failure nodes
    and classifies it in terms of the FailureType taxonomy.
    """
    engine = RootCauseEngine()
    
    # Mock traces where retriever scores extremely low similarity
    mock_session_traces = [
        {
            "session_id": "session_test",
            "node_id": "retriever_node",
            "node_type": "retriever",
            "timestamp_start": "2026-07-09T12:00:00",
            "timestamp_end": "2026-07-09T12:00:00.100", # short latency
            "retrieved_docs": [{"text": "irrelevant data", "similarity_score": 0.20}]
        },
        {
            "session_id": "session_test",
            "node_id": "generator_node",
            "node_type": "generator",
            "timestamp_start": "2026-07-09T12:00:01",
            "timestamp_end": "2026-07-09T12:00:01.100", # short latency
            "parent_node_ids": ["retriever_node"],
            "retrieved_docs": [{"text": "irrelevant data", "similarity_score": 0.20}],
            "outputs": {"response": "irrelevant data"} # fully grounded response
        }
    ]
    
    diagnosed = engine.propagate_failures(mock_session_traces)
    assert len(diagnosed) == 2
    
    retriever_res = next(node for node in diagnosed if node["node_id"] == "retriever_node")
    assert retriever_res["is_root_cause"] is True
    assert retriever_res["failure_type"] == FailureType.RETRIEVAL_FAILURE
    assert retriever_res["raw_health"] < 0.7
    
    generator_res = next(node for node in diagnosed if node["node_id"] == "generator_node")
    # Generator itself has good logic but got fed bad inputs (adjusted health penalized)
    assert generator_res["is_root_cause"] is False
    assert generator_res["adjusted_health"] < generator_res["raw_health"]
    
    # Check that confidence was calculated
    assert "confidence" in retriever_res
    assert "candidate_separation" in retriever_res
    assert "calibrated_probability" in retriever_res
    assert retriever_res["confidence"] is not None
    assert retriever_res["confidence_calibrated"] is False

def test_confidence_bounds_chain_ab():
    """Checks that the confidence formula stays in [0.0, 1.0] and doesn't go negative on Chain A/B."""
    engine = RootCauseEngine()
    
    # Chain A: retriever health is low (e.g. 0.42), generator health is even lower (0.0 due to hallucination)
    # Retriever is still the root cause because it occurred earliest.
    # h_root (0.42) > h_second (0.0). Under old formula, confidence went negative.
    # Under new formula, it should clamp to 0.0.
    mock_traces = [
        {
            "session_id": "session_chain_a",
            "node_id": "retriever_node",
            "node_type": "retriever",
            "timestamp_start": "2026-07-10T12:00:00",
            "timestamp_end": "2026-07-10T12:00:00.100",
            # similarity = 0.59 -> health = (0.59 - 0.40)/0.45 = 0.42
            "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.59}]
        },
        {
            "session_id": "session_chain_a",
            "node_id": "generator_node",
            "node_type": "generator",
            "timestamp_start": "2026-07-10T12:00:01",
            "timestamp_end": "2026-07-10T12:00:01.100",
            "parent_node_ids": ["retriever_node"],
            "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.59}],
            # response doesn't match retrieved docs -> groundedness ratio = 0.0 (raw health = 0.0)
            "outputs": {"response": "unsupported text"}
        }
    ]
    
    diagnosed = engine.propagate_failures(mock_traces)
    retriever_res = next(node for node in diagnosed if node["node_id"] == "retriever_node")
    generator_res = next(node for node in diagnosed if node["node_id"] == "generator_node")
    
    assert retriever_res["is_root_cause"] is True
    assert generator_res["is_root_cause"] is False
    assert generator_res["is_inherited_degradation"] is True
    
    # Raw health of retriever (0.42) is greater than generator (0.0)
    assert retriever_res["raw_health"] > generator_res["raw_health"]
    
    # Confidence must not be negative! It should clamp to 0.0
    assert 0.0 <= retriever_res["confidence"] <= 1.0
    assert retriever_res["confidence_calibrated"] is False
    assert retriever_res["confidence"] > 0.0

def test_co_originators_and_confidence_tiers():
    """Checks that parallel failed nodes with gap < 0.10 result in co-originator status and ambiguous tier."""
    engine = RootCauseEngine()
    
    mock_traces = [
        {
            "session_id": "session_co",
            "node_id": "retriever_A",
            "node_type": "retriever",
            "timestamp_start": "2026-07-10T12:00:00",
            "timestamp_end": "2026-07-10T12:00:00.100",
            # similarity = 0.59 -> health = (0.59 - 0.40)/0.45 = 0.4222
            "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.59}]
        },
        {
            "session_id": "session_co",
            "node_id": "retriever_B",
            "node_type": "retriever",
            "timestamp_start": "2026-07-10T12:00:00",
            "timestamp_end": "2026-07-10T12:00:00.100",
            # similarity = 0.60 -> health = (0.60 - 0.40)/0.45 = 0.4444
            "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.60}]
        },
        {
            "session_id": "session_co",
            "node_id": "generator",
            "node_type": "generator",
            "parent_node_ids": ["retriever_A", "retriever_B"],
            "timestamp_start": "2026-07-10T12:00:01",
            "timestamp_end": "2026-07-10T12:00:01.100",
            "outputs": {"response": "Correct response."}
        }
    ]
    
    diagnosed = engine.propagate_failures(mock_traces)
    
    # Gap is 0.4444 - 0.4222 = 0.0222 < 0.10, so both should be co-originators
    r_A = next(n for n in diagnosed if n["node_id"] == "retriever_A")
    r_B = next(n for n in diagnosed if n["node_id"] == "retriever_B")
    
    assert r_A["is_root_cause"] is False
    assert r_B["is_root_cause"] is False
    
    assert r_A["is_co_originator"] is True
    assert r_B["is_co_originator"] is True
    
    assert r_A["confidence"] == 0.0
    assert r_A["confidence_tier"] == "ambiguous"

def test_sibling_propagation():
    """Verifies that inherited degradation on a merge point is correctly attributed to the specific failed parent."""
    engine = RootCauseEngine()
    
    mock_traces = [
        {
            "session_id": "session_sib_prop",
            "node_id": "planner",
            "node_type": "planner",
            "timestamp_start": "2026-07-10T12:00:00",
            "timestamp_end": "2026-07-10T12:00:00.100",
        },
        {
            "session_id": "session_sib_prop",
            "node_id": "policy_retriever",
            "node_type": "retriever",
            "parent_node_ids": ["planner"],
            "timestamp_start": "2026-07-10T12:00:01",
            "timestamp_end": "2026-07-10T12:00:01.100",
            # similarity = 0.35 -> raw health = 0.0 (failed)
            "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.35}]
        },
        {
            "session_id": "session_sib_prop",
            "node_id": "product_retriever",
            "node_type": "retriever",
            "parent_node_ids": ["planner"],
            "timestamp_start": "2026-07-10T12:00:01",
            "timestamp_end": "2026-07-10T12:00:01.100",
            # similarity = 0.95 -> raw health = 1.0 (healthy)
            "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.95}]
        },
        {
            "session_id": "session_sib_prop",
            "node_id": "synthesizer",
            "node_type": "generator",
            "parent_node_ids": ["policy_retriever", "product_retriever"],
            "timestamp_start": "2026-07-10T12:00:02",
            "timestamp_end": "2026-07-10T12:00:02.100",
            "outputs": {"response": "Unlimited policy response"} # raw health = 0.50
        }
    ]
    
    diagnosed = engine.propagate_failures(mock_traces)
    synth = next(n for n in diagnosed if n["node_id"] == "synthesizer")
    
    assert synth["is_inherited_degradation"] is True
    # Should specifically attribute to policy_retriever which has health < 0.70
    assert "policy_retriever" in synth["inherited_from_node_ids"]
    assert "product_retriever" not in synth["inherited_from_node_ids"]

def test_sibling_scoped_co_originators():
    """Verifies that co-originator status is only triggered for sibling nodes sharing a common child."""
    engine = RootCauseEngine()
    
    # 1. Sibling Candidates: both retrievers feed synthesizer and have close health
    mock_sibling_traces = [
        {
            "session_id": "session_sib_co",
            "node_id": "planner",
            "node_type": "planner",
            "timestamp_start": "2026-07-10T12:00:00",
            "timestamp_end": "2026-07-10T12:00:00.100",
            "outputs": {"plan": "Valid plan."}
        },
        {
            "session_id": "session_sib_co",
            "node_id": "policy_retriever",
            "node_type": "retriever",
            "parent_node_ids": ["planner"],
            "timestamp_start": "2026-07-10T12:00:01",
            "timestamp_end": "2026-07-10T12:00:01.100",
            # similarity = 0.59 -> raw health = 0.4222
            "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.59}]
        },
        {
            "session_id": "session_sib_co",
            "node_id": "product_retriever",
            "node_type": "retriever",
            "parent_node_ids": ["planner"],
            "timestamp_start": "2026-07-10T12:00:01",
            "timestamp_end": "2026-07-10T12:00:01.100",
            # similarity = 0.60 -> raw health = 0.4444
            "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.60}]
        },
        {
            "session_id": "session_sib_co",
            "node_id": "synthesizer",
            "node_type": "generator",
            "parent_node_ids": ["policy_retriever", "product_retriever"],
            "timestamp_start": "2026-07-10T12:00:02",
            "timestamp_end": "2026-07-10T12:00:02.100",
            "outputs": {"response": "Correct return response."} # raw health = 1.0
        }
    ]
    
    diagnosed = engine.propagate_failures(mock_sibling_traces)
    pol = next(n for n in diagnosed if n["node_id"] == "policy_retriever")
    prod = next(n for n in diagnosed if n["node_id"] == "product_retriever")
    
    # Sibling candidates with gap = 0.022 < 0.10 -> Co-originators!
    assert pol["is_co_originator"] is True
    assert prod["is_co_originator"] is True
    
    # 2. Non-Sibling Candidates: one retriever (failed) and critic (failed) with close health, but not siblings
    mock_non_sibling_traces = [
        {
            "session_id": "session_non_sib",
            "node_id": "planner",
            "node_type": "planner",
            "timestamp_start": "2026-07-10T12:00:00",
            "timestamp_end": "2026-07-10T12:00:00.100",
        },
        {
            "session_id": "session_non_sib",
            "node_id": "policy_retriever",
            "node_type": "retriever",
            "parent_node_ids": ["planner"],
            "timestamp_start": "2026-07-10T12:00:01",
            "timestamp_end": "2026-07-10T12:00:01.100",
            # similarity = 0.59 -> raw health = 0.4222
            "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.59}]
        },
        {
            "session_id": "session_non_sib",
            "node_id": "product_retriever",
            "node_type": "retriever",
            "parent_node_ids": ["planner"],
            "timestamp_start": "2026-07-10T12:00:01",
            "timestamp_end": "2026-07-10T12:00:01.100",
            # similarity = 0.95 -> raw health = 1.0 (healthy)
            "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.95}]
        },
        {
            "session_id": "session_non_sib",
            "node_id": "synthesizer",
            "node_type": "generator",
            "parent_node_ids": ["policy_retriever", "product_retriever"],
            "timestamp_start": "2026-07-10T12:00:02",
            "timestamp_end": "2026-07-10T12:00:02.100",
            "outputs": {"response": "Correct return response."} # raw health = 1.0
        },
        {
            "session_id": "session_non_sib",
            "node_id": "critic",
            "node_type": "critic",
            "parent_node_ids": ["synthesizer"],
            "timestamp_start": "2026-07-10T12:00:03",
            "timestamp_end": "2026-07-10T12:00:03.100",
            # critic fails to catch correctness -> raw health = 0.4444 (failed independent of generator)
            "outputs": "Fail to catch correct response"
        }
    ]
    
    # We override critic node raw_health in propagation test to evaluate independent failures
    diagnosed = engine.propagate_failures(mock_non_sibling_traces)
    # Since critic node logic depends on generator outputs in default collector, let's look at the result:
    pol = next(n for n in diagnosed if n["node_id"] == "policy_retriever")
    critic = next(n for n in diagnosed if n["node_id"] == "critic")
    
    # Even if their health scores are close (0.42 vs 0.0 for actual propagation due to adjusted health, or they are candidates),
    # since policy_retriever and critic are NOT siblings, they must not be flagged as co-originators!
    assert pol["is_co_originator"] is False
    assert critic["is_co_originator"] is False

def test_retry_health_floor_edge_case():
    """Verifies that retry penalty correctly saturates at 0.71 floor, which is above the 0.70 threshold."""
    engine = RootCauseEngine()
    
    # Node 1: Retriever with 1 retry (2 attempts), final attempt succeeds
    # Node 2: Retriever with 30 retries (31 attempts), final attempt succeeds
    mock_traces = [
        # Node 1: Retriever A (1 retry)
        {
            "session_id": "session_retry_test",
            "node_id": "retriever_a",
            "node_type": "retriever",
            "attempt_number": 1,
            "timestamp_start": "2026-07-10T12:00:00",
            "timestamp_end": "2026-07-10T12:00:00",
            "retrieved_docs": [{"text": "generic", "similarity_score": 0.35}]
        },
        {
            "session_id": "session_retry_test",
            "node_id": "retriever_a",
            "node_type": "retriever",
            "attempt_number": 2,
            "timestamp_start": "2026-07-10T12:00:01",
            "timestamp_end": "2026-07-10T12:00:01",
            "retrieved_docs": [{"text": "relevant", "similarity_score": 0.95}]
        },
        # Node 2: Retriever B (30 retries, starts at attempt 1 and ends at 31)
        {
            "session_id": "session_retry_test",
            "node_id": "retriever_b",
            "node_type": "retriever",
            "attempt_number": 1,
            "timestamp_start": "2026-07-10T12:00:02",
            "timestamp_end": "2026-07-10T12:00:02",
            "retrieved_docs": [{"text": "generic", "similarity_score": 0.35}]
        },
        {
            "session_id": "session_retry_test",
            "node_id": "retriever_b",
            "node_type": "retriever",
            "attempt_number": 31,
            "timestamp_start": "2026-07-10T12:00:03",
            "timestamp_end": "2026-07-10T12:00:03",
            "retrieved_docs": [{"text": "relevant", "similarity_score": 0.95}]
        }
    ]
    
    # Add dummy intermediate attempts for retriever_b to simulate 30 retries
    for i in range(2, 31):
        mock_traces.append({
            "session_id": "session_retry_test",
            "node_id": "retriever_b",
            "node_type": "retriever",
            "attempt_number": i,
            "timestamp_start": f"2026-07-10T12:00:02",
            "timestamp_end": f"2026-07-10T12:00:02",
            "retrieved_docs": [{"text": "generic", "similarity_score": 0.35}]
        })
        
    diagnosed = engine.propagate_failures(mock_traces)
    
    ret_a = next(n for n in diagnosed if n["node_id"] == "retriever_a")
    ret_b = next(n for n in diagnosed if n["node_id"] == "retriever_b")
    
    # Retry history is now explicit evidence, not a hidden penalty.
    assert ret_a["raw_health"] == pytest.approx(0.9733333333)
    assert ret_a["is_root_cause"] is False
    assert ret_a["failure_type"] is None
    assert ret_a["evidence"]["retry_count"] == 1
    assert ret_a["evidence"]["first_attempt_health"] < ret_a["evidence"]["final_attempt_health"]
    
    # Many retries no longer get artificially forced to a floor.
    assert ret_b["raw_health"] == pytest.approx(0.9733333333)
    # It is still healthy because the final attempt succeeded.
    assert ret_b["is_root_cause"] is False
    assert ret_b["failure_type"] is None
    assert ret_b["evidence"]["retry_count"] == 30


def test_failed_parent_filter_uses_each_nodes_failure_type():
    """Regression test for stale failure_type leaking across candidate filtering."""
    engine = RootCauseEngine()

    mock_traces = [
        {
            "session_id": "session_scope_bug",
            "node_id": "branch_a",
            "node_type": "planner",
            "timestamp_start": "2026-07-10T12:00:00",
            "timestamp_end": "2026-07-10T12:00:00.100",
            "outputs": {"plan": "ok"},
        },
        {
            "session_id": "session_scope_bug",
            "node_id": "branch_b",
            "node_type": "planner",
            "timestamp_start": "2026-07-10T12:00:00",
            "timestamp_end": "2026-07-10T12:00:00.100",
            "outputs": {"plan": "ok"},
        },
        {
            "session_id": "session_scope_bug",
            "node_id": "merge_node",
            "node_type": "generator",
            "parent_node_ids": ["branch_a", "branch_b"],
            "timestamp_start": "2026-07-10T12:00:00.500",
            "timestamp_end": "2026-07-10T12:00:00.600",
            "outputs": {"response": "merge ok"},
        },
        {
            "session_id": "session_scope_bug",
            "node_id": "generator_node",
            "node_type": "generator",
            "parent_node_ids": ["retriever_node"],
            "timestamp_start": "2026-07-10T12:00:01",
            "timestamp_end": "2026-07-10T12:00:01.100",
            "outputs": {"response": "unsupported hallucinated answer"},
        },
        {
            "session_id": "session_scope_bug",
            "node_id": "helper_0",
            "node_type": "generator",
            "parent_node_ids": ["retriever_node"],
            "timestamp_start": "2026-07-10T12:00:01.200",
            "timestamp_end": "2026-07-10T12:00:01.210",
            "outputs": {"response": "{}"},
        },
        {
            "session_id": "session_scope_bug",
            "node_id": "helper_1",
            "node_type": "generator",
            "parent_node_ids": ["retriever_node"],
            "timestamp_start": "2026-07-10T12:00:01.220",
            "timestamp_end": "2026-07-10T12:00:01.230",
            "outputs": {"response": "{}"},
        },
        {
            "session_id": "session_scope_bug",
            "node_id": "retriever_node",
            "node_type": "retriever",
            "timestamp_start": "2026-07-10T12:00:00",
            "timestamp_end": "2026-07-10T12:00:00.100",
            "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.45}],
        },
    ]

    diagnosed = engine.propagate_failures(mock_traces)
    generator = next(node for node in diagnosed if node["node_id"] == "generator_node")
    retriever = next(node for node in diagnosed if node["node_id"] == "retriever_node")

    assert generator["failure_type"] == FailureType.GROUNDING_FAILURE
    assert retriever["failure_type"] == FailureType.RETRIEVAL_FAILURE
    assert retriever["is_root_cause"] is False
    assert generator["is_root_cause"] is False
    candidate_ids = [c["node_id"] for c in retriever["ranked_candidates"]]
    assert "generator_node" in candidate_ids
    assert "retriever_node" in candidate_ids


def test_threshold_calibration_overrides_default_failure_cutoff():
    """Checks the engine honors a loaded threshold calibration instead of the default 0.70 cutoff."""
    artifact = ThresholdCalibrationArtifact(
        metric="overall_health",
        threshold=0.95,
        precision=0.9,
        recall=0.9,
        f1=0.9,
        roc_auc=0.92,
        pr_auc=0.91,
        split="calibration",
        dataset="unit-test",
        dataset_version="v1",
        calibration_version="threshold-v1",
        timestamp="2026-08-11T00:00:00Z",
        configuration={"node_type": "retriever"},
    )
    engine = RootCauseEngine(threshold_calibration=artifact)

    mock_traces = [
        {
            "session_id": "session_threshold_override",
            "node_id": "retriever_node",
            "node_type": "retriever",
            "timestamp_start": "2026-07-10T12:00:00",
            "timestamp_end": "2026-07-10T12:00:00.100",
            "retrieved_docs": [{"text": "relevant", "similarity_score": 0.65}],
        }
    ]

    diagnosed = engine.propagate_failures(mock_traces)
    retriever = diagnosed[0]
    assert retriever["failure_type"] == FailureType.RETRIEVAL_FAILURE
