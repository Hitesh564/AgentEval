import pytest

from agenteval.benchmark.metrics import (
    BenchmarkRecord,
    classification_metrics,
    top_k_accuracy,
    benchmark_summary,
    bootstrap_metric_intervals,
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
    assert metrics["support"] == {"generator": 2, "planner": 1, "retriever": 1}


def test_classification_metrics_excludes_predicted_only_class_from_bounded_aggregates():
    y_true = ["retriever", "retriever", "planner", "planner"]
    y_pred = ["retriever", "ghost", "planner", "ghost"]

    metrics = classification_metrics(y_true, y_pred)
    assert "ghost" in metrics["confusion_matrix"]["labels"]
    assert metrics["support"]["ghost"] == 0
    assert metrics["balanced_accuracy"] == pytest.approx(0.5)
    assert metrics["macro_f1"] == pytest.approx((2 / 3 + 2 / 3) / 2, rel=1e-6)


def test_classification_metrics_handles_explicit_zero_support_class():
    y_true = ["retriever", "planner"]
    y_pred = ["retriever", "planner"]

    metrics = classification_metrics(y_true, y_pred, labels=["retriever", "planner", "critic"])
    assert metrics["support"]["critic"] == 0
    assert metrics["balanced_accuracy"] == pytest.approx(1.0)
    assert metrics["macro_f1"] == pytest.approx(1.0)
    assert metrics["per_class"][2]["class"] == "critic"
    assert metrics["per_class"][2]["support"] == 0


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
    assert "Per-Class Performance" in markdown
    assert "Support" in markdown
    assert "Statistical Uncertainty" in markdown


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


def test_benchmark_summary_reports_partial_confidence_coverage():
    records = [
        BenchmarkRecord(
            case_id="case_1",
            true_agent="retriever",
            pred_agent="retriever",
            confidence=0.9,
            confidence_calibrated=True,
        ),
        BenchmarkRecord(
            case_id="case_2",
            true_agent="planner",
            pred_agent="generator",
            confidence=0.2,
            confidence_calibrated=False,
        ),
    ]

    report = benchmark_summary(records)
    assert report["confidence"]["ece"] is not None
    assert report["confidence"]["coverage"] == pytest.approx(0.5)
    assert report["confidence"]["calibrated_count"] == 1
    assert report["confidence"]["total_count"] == 2


def test_bootstrap_metric_intervals_is_deterministic():
    y_true = ["retriever", "planner", "generator", "none"]
    y_pred = ["retriever", "planner", "planner", "none"]

    first = bootstrap_metric_intervals(y_true, y_pred, seed=13, n_bootstrap=250)
    second = bootstrap_metric_intervals(y_true, y_pred, seed=13, n_bootstrap=250)

    assert first == second
    assert first["metrics"]["accuracy"]["point"] == pytest.approx(0.75)
    assert first["metrics"]["macro_f1"]["lower"] <= first["metrics"]["macro_f1"]["point"] <= first["metrics"]["macro_f1"]["upper"]
