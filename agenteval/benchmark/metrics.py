import math
import random
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from agenteval.eval.calibration import brier_score, expected_calibration_error


@dataclass(frozen=True)
class BenchmarkRecord:
    case_id: str
    true_agent: str
    pred_agent: str
    true_step: Optional[str] = None
    pred_step: Optional[str] = None
    confidence: Optional[float] = None
    confidence_calibrated: bool = False
    top_k_agents: Optional[List[str]] = None
    baseline_last_failure: Optional[str] = None
    baseline_v1: Optional[str] = None


def confusion_matrix(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    if len(y_true) != len(y_pred):
        raise ValueError("Labels and predictions must have the same length")
    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))
    label_to_idx = {label: idx for idx, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for truth, pred in zip(y_true, y_pred):
        if truth not in label_to_idx or pred not in label_to_idx:
            continue
        matrix[label_to_idx[truth]][label_to_idx[pred]] += 1
    return {"labels": list(labels), "matrix": matrix}


def _class_counts(y_true: Sequence[str], y_pred: Sequence[str], label: str) -> Tuple[int, int, int]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
    return tp, fp, fn


def classification_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    if len(y_true) != len(y_pred):
        raise ValueError("Labels and predictions must have the same length")
    if not y_true:
        return {
            "accuracy": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "balanced_accuracy": 0.0,
            "per_class_f1": {},
            "confusion_matrix": {"labels": [], "matrix": []},
        }

    labels = list(labels) if labels is not None else sorted(set(y_true) | set(y_pred))
    per_class_f1: Dict[str, float] = {}
    precisions: List[float] = []
    recalls: List[float] = []
    recalls_for_balanced: List[float] = []

    for label in labels:
        tp, fp, fn = _class_counts(y_true, y_pred, label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_class_f1[label] = f1
        precisions.append(precision)
        recalls.append(recall)
        recalls_for_balanced.append(recall)

    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
    macro_precision = sum(precisions) / len(precisions) if precisions else 0.0
    macro_recall = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = sum(per_class_f1.values()) / len(per_class_f1) if per_class_f1 else 0.0
    balanced = sum(recalls_for_balanced) / len(recalls_for_balanced) if recalls_for_balanced else 0.0
    return {
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "balanced_accuracy": balanced,
        "per_class_f1": per_class_f1,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels),
    }


def top_k_accuracy(y_true: Sequence[str], top_k_predictions: Sequence[Sequence[str]]) -> float:
    if len(y_true) != len(top_k_predictions):
        raise ValueError("Labels and top-k predictions must have the same length")
    if not y_true:
        return 0.0
    hits = 0
    for truth, candidates in zip(y_true, top_k_predictions):
        if truth in candidates:
            hits += 1
    return hits / len(y_true)


def majority_baseline(y_true: Sequence[str]) -> List[str]:
    if not y_true:
        return []
    majority = Counter(y_true).most_common(1)[0][0]
    return [majority for _ in y_true]


def random_baseline(y_true: Sequence[str], *, seed: int = 0) -> List[str]:
    if not y_true:
        return []
    rng = random.Random(seed)
    labels = sorted(set(y_true))
    return [rng.choice(labels) for _ in y_true]


def last_failure_baseline(records: Sequence[BenchmarkRecord]) -> List[str]:
    preds: List[str] = []
    for record in records:
        if record.baseline_last_failure:
            preds.append(record.baseline_last_failure)
        else:
            preds.append(record.pred_agent)
    return preds


def baseline_suite(records: Sequence[BenchmarkRecord], *, seed: int = 0) -> Dict[str, List[str]]:
    true_agents = [record.true_agent for record in records]
    return {
        "random": random_baseline(true_agents, seed=seed),
        "majority": majority_baseline(true_agents),
        "last_failure": last_failure_baseline(records),
        "v1": [record.baseline_v1 or record.pred_agent for record in records],
        "v2": [record.pred_agent for record in records],
    }


def confidence_metrics(y_true: Sequence[str], y_pred: Sequence[str], confidence: Sequence[Optional[float]]) -> Dict[str, Any]:
    correctness = [1 if t == p else 0 for t, p in zip(y_true, y_pred)]
    usable_confidence = [float(c) for c in confidence]
    report = expected_calibration_error(correctness, usable_confidence)
    return {
        "ece": report["ece"],
        "brier_score": brier_score(correctness, usable_confidence),
        "reliability_diagram": report["bins"],
    }


def benchmark_summary(
    records: Sequence[BenchmarkRecord],
    *,
    seed: int = 0,
) -> Dict[str, Any]:
    y_true = [record.true_agent for record in records]
    y_pred = [record.pred_agent for record in records]
    top_k = [record.top_k_agents or [] for record in records]
    confidence = [record.confidence for record in records]
    calibrated_confidence = [record.confidence for record in records if record.confidence is not None and record.confidence_calibrated]
    metrics = classification_metrics(y_true, y_pred)
    step_records = [
        record for record in records
        if record.true_step is not None and record.pred_step is not None
    ]
    if step_records:
        step_metrics = classification_metrics(
            [record.true_step for record in step_records],
            [record.pred_step for record in step_records],
        )
        agent_step_accuracy = sum(
            1 for record in step_records
            if record.true_agent == record.pred_agent and record.true_step == record.pred_step
        ) / len(step_records)
    else:
        step_metrics = {
            "accuracy": None,
            "macro_precision": None,
            "macro_recall": None,
            "macro_f1": None,
            "balanced_accuracy": None,
            "per_class_f1": {},
            "confusion_matrix": {"labels": [], "matrix": []},
        }
        agent_step_accuracy = None
    baselines = baseline_suite(records, seed=seed)
    baseline_metrics = {
        name: classification_metrics(y_true, preds, labels=metrics["confusion_matrix"]["labels"])
        for name, preds in baselines.items()
    }
    top_k_acc = top_k_accuracy(y_true, top_k) if any(top_k) else None
    confidence_report = confidence_metrics(y_true, y_pred, calibrated_confidence) if calibrated_confidence and len(calibrated_confidence) == len(records) else {
        "ece": None,
        "brier_score": None,
        "reliability_diagram": [],
    }
    return {
        "metrics": metrics,
        "step_metrics": step_metrics,
        "agent_step_accuracy": agent_step_accuracy,
        "baseline_metrics": baseline_metrics,
        "baselines": baselines,
        "top_k_accuracy": top_k_acc,
        "confidence": confidence_report,
        "records": [record.__dict__ for record in records],
    }


def render_benchmark_markdown(report: Dict[str, Any], *, title: str = "AgentEval Benchmark Report") -> str:
    metrics = report["metrics"]
    baseline_metrics = report["baseline_metrics"]
    lines = [
        f"# {title}",
        "",
        "## Summary",
        f"- Accuracy: {metrics['accuracy']:.3f}",
        f"- Macro Precision: {metrics['macro_precision']:.3f}",
        f"- Macro Recall: {metrics['macro_recall']:.3f}",
        f"- Macro F1: {metrics['macro_f1']:.3f}",
        f"- Balanced Accuracy: {metrics['balanced_accuracy']:.3f}",
    ]
    step_metrics = report.get("step_metrics") or {}
    if step_metrics.get("accuracy") is not None:
        lines.extend([
            f"- Step Accuracy: {step_metrics['accuracy']:.3f}",
            f"- Agent-Step Accuracy: {report.get('agent_step_accuracy', 0.0):.3f}",
        ])
    if report.get("top_k_accuracy") is not None:
        lines.append(f"- Top-k Accuracy: {report['top_k_accuracy']:.3f}")
    if report["confidence"]["ece"] is not None:
        lines.append(f"- ECE: {report['confidence']['ece']:.3f}")
        lines.append(f"- Brier Score: {report['confidence']['brier_score']:.3f}")
    lines.extend(["", "## Baselines"])
    for name, metric in baseline_metrics.items():
        lines.append(f"- {name}: accuracy={metric['accuracy']:.3f}, macro_f1={metric['macro_f1']:.3f}, balanced_accuracy={metric['balanced_accuracy']:.3f}")
    lines.extend(["", "## Confusion Matrix"])
    labels = metrics["confusion_matrix"]["labels"]
    matrix = metrics["confusion_matrix"]["matrix"]
    lines.append("| true \\ pred | " + " | ".join(labels) + " |")
    lines.append("|" + " --- |" * (len(labels) + 1))
    for label, row in zip(labels, matrix):
        lines.append("| " + label + " | " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)
