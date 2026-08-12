import pytest

from agenteval.benchmark.metrics import (
    BenchmarkRecord,
    classification_metrics,
    top_k_accuracy,
    benchmark_summary,
    render_benchmark_markdown,
)


def test_classification_metrics_and_balanced_accuracy():
    y_true = ["retriever", "planner", "generator", "generator"]
    y_pred = ["retriever", "generator", "generator", "planner"]

    metrics = classification_metrics(y_true, y_pred)
    assert metrics["accuracy"] == pytest.approx(0.5)
    assert metrics["macro_f1"] >= 0.3
    assert metrics["balanced_accuracy"] >= 0.3
    assert set(metrics["confusion_matrix"]["labels"]) == {"generator", "planner", "retriever"}


def test_top_k_accuracy():
    y_true = ["retriever", "planner", "generator"]
    top_k = [["planner", "retriever"], ["planner"], ["critic", "generator"]]
    assert top_k_accuracy(y_true, top_k) == pytest.approx(1.0)


def test_benchmark_summary_includes_baselines_and_step_metrics():
    records = [
        BenchmarkRecord(
            case_id="case_1",
            true_agent="retriever",
            pred_agent="retriever",
            true_step="step_1",
            pred_step="step_1",
            confidence=0.9,
            confidence_calibrated=True,
            top_k_agents=["retriever", "planner"],
            baseline_last_failure="planner",
            baseline_v1="planner",
        ),
        BenchmarkRecord(
            case_id="case_2",
            true_agent="generator",
            pred_agent="planner",
            true_step="step_9",
            pred_step="step_3",
            confidence=0.2,
            confidence_calibrated=True,
            top_k_agents=["planner", "generator"],
            baseline_last_failure="generator",
            baseline_v1="generator",
        ),
    ]

    report = benchmark_summary(records, seed=7)
    assert report["metrics"]["accuracy"] == pytest.approx(0.5)
    assert report["step_metrics"]["accuracy"] == pytest.approx(0.5)
    assert report["agent_step_accuracy"] == pytest.approx(0.5)
    assert report["baseline_metrics"]["majority"]["accuracy"] == pytest.approx(0.5)
    assert report["baseline_metrics"]["random"]["accuracy"] >= 0.0
    assert report["baseline_metrics"]["last_failure"]["accuracy"] >= 0.0
    assert report["top_k_accuracy"] == pytest.approx(1.0)
    assert report["confidence"]["ece"] is not None


def test_render_benchmark_markdown_mentions_key_metrics():
    records = [
        BenchmarkRecord(
            case_id="case_1",
            true_agent="retriever",
            pred_agent="retriever",
            true_step="step_1",
            pred_step="step_1",
            confidence=0.9,
            confidence_calibrated=True,
            top_k_agents=["retriever", "planner"],
        )
    ]
    report = benchmark_summary(records)
    markdown = render_benchmark_markdown(report, title="Demo Report")
    assert "# Demo Report" in markdown
    assert "Macro F1" in markdown
    assert "Balanced Accuracy" in markdown
    assert "Confusion Matrix" in markdown


def test_benchmark_summary_omits_unavailable_confidence():
    records = [
        BenchmarkRecord(
            case_id="case_1",
            true_agent="retriever",
            pred_agent="retriever",
            confidence=0.9,
            confidence_calibrated=False,
        )
    ]
    report = benchmark_summary(records)
    assert report["confidence"]["ece"] is None
    assert report["confidence"]["brier_score"] is None
