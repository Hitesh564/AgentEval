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


def _merge_labels(
    labels: Optional[Sequence[str]],
    y_true: Sequence[str],
    y_pred: Sequence[str],
) -> List[str]:
    ordered: List[str] = []
    seen = set()
    source = list(labels) if labels is not None else []
    source.extend(list(y_true))
    source.extend(list(y_pred))
    for label in source:
        if label in seen:
            continue
        seen.add(label)
        ordered.append(label)
    return ordered


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

    labels = _merge_labels(labels, y_true, y_pred)
    support_counts = {label: sum(1 for truth in y_true if truth == label) for label in labels}
    per_class: List[Dict[str, Any]] = []
    per_class_f1: Dict[str, float] = {}
    per_class_precision: Dict[str, float] = {}
    per_class_recall: Dict[str, float] = {}
    supported_labels = [label for label in labels if support_counts[label] > 0]

    for label in labels:
        tp, fp, fn = _class_counts(y_true, y_pred, label)
        support = support_counts[label]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / support if support else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_class_f1[label] = f1
        per_class_precision[label] = precision
        per_class_recall[label] = recall
        per_class.append({
            "class": label,
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        })

    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
    if supported_labels:
        macro_precision = sum(per_class_precision[label] for label in supported_labels) / len(supported_labels)
        macro_recall = sum(per_class_recall[label] for label in supported_labels) / len(supported_labels)
        macro_f1 = sum(per_class_f1[label] for label in supported_labels) / len(supported_labels)
        balanced = macro_recall
    else:
        macro_precision = 0.0
        macro_recall = 0.0
        macro_f1 = 0.0
        balanced = 0.0
    return {
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "balanced_accuracy": balanced,
        "support": support_counts,
        "supported_labels": supported_labels,
        "per_class": per_class,
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
    calibrated_coverage = len(calibrated_confidence) / len(records) if records else 0.0
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
    confidence_report = confidence_metrics(
        [true for true, record in zip(y_true, records) if record.confidence is not None and record.confidence_calibrated],
        [pred for pred, record in zip(y_pred, records) if record.confidence is not None and record.confidence_calibrated],
        calibrated_confidence,
    ) if calibrated_confidence else {
        "ece": None,
        "brier_score": None,
        "reliability_diagram": [],
    }
    confidence_report["coverage"] = calibrated_coverage if calibrated_confidence else 0.0
    confidence_report["calibrated_count"] = len(calibrated_confidence)
    confidence_report["total_count"] = len(records)
    return {
        "metrics": metrics,
        "step_metrics": step_metrics,
        "agent_step_accuracy": agent_step_accuracy,
        "baseline_metrics": baseline_metrics,
        "baselines": baselines,
        "top_k_accuracy": top_k_acc,
        "confidence": confidence_report,
        "label_distribution": {label: metrics["support"].get(label, 0) for label in metrics["confusion_matrix"]["labels"]},
        "records": [record.__dict__ for record in records],
    }


def render_benchmark_markdown(report: Dict[str, Any], *, title: str = "AgentEval Benchmark Report") -> str:
    def _fmt_optional(value: Optional[float]) -> str:
        return f"{value:.3f}" if value is not None else "n/a"

    metrics = report["metrics"]
    baseline_metrics = report["baseline_metrics"]
    lines = [
        f"# {title}",
        "",
        "## Dataset",
    ]
    dataset_lines = report.get("dataset_lines") or []
    if dataset_lines:
        lines.extend(dataset_lines)
    else:
        lines.append("- Dataset metadata unavailable in this run.")

    lines.extend([
        "",
        "## Evaluation Protocol",
    ])
    protocol_lines = report.get("protocol_lines") or [
        "- Metrics are computed on stored traces after diagnosis.",
        "- Balanced accuracy, macro precision, macro recall, and macro F1 are averaged over classes with non-zero ground-truth support.",
        "- Confusion matrices include the union of true and predicted labels.",
        "- Confidence calibration is reported only when calibrated confidences are available for all benchmark records.",
    ]
    lines.extend(protocol_lines)

    lines.extend([
        "",
        "## Summary",
        f"- Accuracy: {metrics['accuracy']:.3f}",
        f"- Macro Precision: {metrics['macro_precision']:.3f}",
        f"- Macro Recall: {metrics['macro_recall']:.3f}",
        f"- Macro F1: {metrics['macro_f1']:.3f}",
        f"- Balanced Accuracy: {metrics['balanced_accuracy']:.3f}",
    ])
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
        if report["confidence"].get("coverage") is not None:
            lines.append(f"- Calibrated Coverage: {report['confidence']['coverage']:.1%}")
            lines.append(f"- Calibrated Samples: {report['confidence'].get('calibrated_count', 0)}/{report['confidence'].get('total_count', 0)}")
    lines.extend([
        "",
        "## Label Distribution",
    ])
    label_distribution = report.get("label_distribution") or metrics.get("support", {})
    if label_distribution:
        for label, count in label_distribution.items():
            lines.append(f"- {label}: {count}")
    else:
        lines.append("- Unavailable.")
    lines.extend(["", "## Baselines"])
    for name, metric in baseline_metrics.items():
        lines.append(f"- {name}: accuracy={metric['accuracy']:.3f}, macro_f1={metric['macro_f1']:.3f}, balanced_accuracy={metric['balanced_accuracy']:.3f}")
    if report.get("ablation"):
        lines.extend(["", "## Ablation Results"])
        ablation = report["ablation"]
        lines.append("| Variant | Accuracy | Macro F1 | Balanced Accuracy | Top-k Accuracy |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in ablation:
            lines.append(
                f"| {row['variant']} | {row['accuracy']:.3f} | {row['macro_f1']:.3f} | {row['balanced_accuracy']:.3f} | {_fmt_optional(row.get('top_k_accuracy'))} |"
            )
    if report.get("who_when"):
        lines.extend(["", "## Who&When Results"])
        for line in report["who_when"]:
            lines.append(line)
    if report.get("calibration"):
        lines.extend(["", "## Calibration Results"])
        for line in report["calibration"]:
            lines.append(line)
    lines.extend(["", "## Confusion Matrix"])
    labels = metrics["confusion_matrix"]["labels"]
    matrix = metrics["confusion_matrix"]["matrix"]
    lines.append("| true \\ pred | " + " | ".join(labels) + " |")
    lines.append("|" + " --- |" * (len(labels) + 1))
    for label, row in zip(labels, matrix):
        lines.append("| " + label + " | " + " | ".join(str(v) for v in row) + " |")
    lines.extend(["", "## Per-Class Performance"])
    lines.append("| Class | Support | Precision | Recall | F1 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in metrics.get("per_class", []):
        lines.append(
            f"| {row['class']} | {row['support']} | {row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} |"
        )
    lines.extend(["", "## Limitations"])
    limitations = report.get("limitations") or [
        "- The benchmark is evaluated on stored fixtures and selected traces rather than a broad external dataset.",
        "- Confidence metrics are only available for the calibrated subset, so coverage should be checked alongside ECE and Brier score.",
        "- Who&When evaluation depends on adapter assumptions about history roles and single-parent session chaining.",
    ]
    lines.extend(limitations)
    return "\n".join(lines)
