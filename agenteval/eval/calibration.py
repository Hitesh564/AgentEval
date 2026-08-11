from dataclasses import dataclass, asdict, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Any
from datetime import datetime, timezone
import math


@dataclass(frozen=True)
class CalibrationResult:
    metric: str
    threshold: float
    precision: float
    recall: float
    f1: float
    roc_auc: Optional[float]
    pr_auc: Optional[float]
    split: str
    dataset: str
    calibration_version: str
    date: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clip_prob(value: float) -> float:
    return max(1e-6, min(1.0 - 1e-6, float(value)))


def _logit(value: float) -> float:
    clipped = _clip_prob(value)
    return math.log(clipped / (1.0 - clipped))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def precision_recall_f1(y_true: Sequence[int], y_pred: Sequence[int]) -> Dict[str, float]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def balanced_accuracy(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    tpr = tp / (tp + fn) if (tp + fn) else 0.0
    tnr = tn / (tn + fp) if (tn + fp) else 0.0
    return (tpr + tnr) / 2.0


def roc_auc_score(y_true: Sequence[int], y_score: Sequence[float]) -> Optional[float]:
    pos = [s for s, t in zip(y_score, y_true) if t == 1]
    neg = [s for s, t in zip(y_score, y_true) if t == 0]
    if not pos or not neg:
        return None

    better = 0.0
    ties = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                better += 1.0
            elif p == n:
                ties += 1.0
    total = len(pos) * len(neg)
    return (better + 0.5 * ties) / total


def pr_auc_score(y_true: Sequence[int], y_score: Sequence[float]) -> Optional[float]:
    pairs = sorted(zip(y_score, y_true), reverse=True)
    positives = sum(y_true)
    if positives == 0:
        return None

    precision_points: List[float] = []
    recall_points: List[float] = []
    tp = 0
    fp = 0
    for _, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / positives
        precision_points.append(precision)
        recall_points.append(recall)

    area = 0.0
    prev_recall = 0.0
    prev_precision = 1.0
    for precision, recall in zip(precision_points, recall_points):
        area += (recall - prev_recall) * ((precision + prev_precision) / 2.0)
        prev_recall = recall
        prev_precision = precision
    return area


def expected_calibration_error(
    y_true: Sequence[int],
    y_prob: Sequence[float],
    *,
    n_bins: int = 10,
) -> Dict[str, Any]:
    if len(y_true) != len(y_prob):
        raise ValueError("Labels and probabilities must have the same length")
    if not y_true:
        return {"ece": 0.0, "bins": []}

    clipped = [_clip_prob(p) for p in y_prob]
    bins: List[Dict[str, Any]] = []
    ece = 0.0
    for bin_idx in range(n_bins):
        low = bin_idx / n_bins
        high = (bin_idx + 1) / n_bins
        if bin_idx == n_bins - 1:
            members = [
                (y, p)
                for y, p in zip(y_true, clipped)
                if low <= p <= high
            ]
        else:
            members = [
                (y, p)
                for y, p in zip(y_true, clipped)
                if low <= p < high
            ]
        count = len(members)
        if not count:
            continue
        accuracy = sum(y for y, _ in members) / count
        confidence = sum(p for _, p in members) / count
        gap = abs(accuracy - confidence)
        ece += (count / len(y_true)) * gap
        bins.append({
            "bin": bin_idx,
            "lower": low,
            "upper": high,
            "count": count,
            "accuracy": accuracy,
            "confidence": confidence,
            "gap": gap,
        })
    return {"ece": ece, "bins": bins}


def brier_score(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    if len(y_true) != len(y_prob):
        raise ValueError("Labels and probabilities must have the same length")
    if not y_true:
        return 0.0
    return sum((float(p) - float(y)) ** 2 for y, p in zip(y_true, y_prob)) / len(y_true)


def reliability_diagram(y_true: Sequence[int], y_prob: Sequence[float], *, n_bins: int = 10) -> List[Dict[str, Any]]:
    return expected_calibration_error(y_true, y_prob, n_bins=n_bins)["bins"]


def _pava_blocks(scores: Sequence[float], labels: Sequence[float]) -> List[Dict[str, float]]:
    """Pool-adjacent-violators algorithm that retains score intervals."""
    blocks: List[Dict[str, float]] = []
    for score, label in zip(scores, labels):
        block = {
            "start": float(score),
            "end": float(score),
            "sum_weight": 1.0,
            "sum_value": float(label),
        }
        block["mean"] = block["sum_value"] / block["sum_weight"]
        blocks.append(block)
        while len(blocks) >= 2 and blocks[-2]["mean"] > blocks[-1]["mean"]:
            right = blocks.pop()
            left = blocks.pop()
            merged_weight = left["sum_weight"] + right["sum_weight"]
            merged_value = left["sum_value"] + right["sum_value"]
            merged = {
                "start": left["start"],
                "end": right["end"],
                "sum_weight": merged_weight,
                "sum_value": merged_value,
            }
            merged["mean"] = merged_value / merged_weight if merged_weight else 0.0
            blocks.append(merged)
    return blocks


@dataclass(frozen=True)
class ConfidenceCalibration:
    method: str
    version: str
    status: str
    temperature: Optional[float] = None
    isotonic_breakpoints: Optional[List[Tuple[float, float]]] = None
    fit_metrics: Dict[str, Any] = field(default_factory=dict)

    def predict(self, raw_score: float) -> float:
        if self.method == "identity":
            return float(raw_score)
        score = _clip_prob(raw_score)
        if self.method == "temperature_scaling" and self.temperature is not None:
            return _clip_prob(_sigmoid(_logit(score) / max(self.temperature, 1e-6)))
        if self.method == "isotonic" and self.isotonic_breakpoints:
            if score <= self.isotonic_breakpoints[0][0]:
                return _clip_prob(self.isotonic_breakpoints[0][1])
            for idx in range(1, len(self.isotonic_breakpoints)):
                left_x, left_y = self.isotonic_breakpoints[idx - 1]
                right_x, right_y = self.isotonic_breakpoints[idx]
                if score <= right_x:
                    if right_x == left_x:
                        return _clip_prob(right_y)
                    ratio = (score - left_x) / (right_x - left_x)
                    return _clip_prob(left_y + ratio * (right_y - left_y))
            return _clip_prob(self.isotonic_breakpoints[-1][1])
        return score

    def calibrate(self, raw_score: float) -> Dict[str, Any]:
        probability = self.predict(raw_score)
        return {
            "raw_score": raw_score,
            "calibrated_probability": probability,
            "status": self.status,
            "method": self.method,
            "version": self.version,
            "fit_metrics": self.fit_metrics,
        }

    @classmethod
    def identity(cls, version: str = "unavailable") -> "ConfidenceCalibration":
        return cls(method="identity", version=version, status="fallback")

    @classmethod
    def fit_temperature_scaling(
        cls,
        raw_scores: Sequence[float],
        labels: Sequence[int],
        *,
        version: str,
        search_grid: Optional[Sequence[float]] = None,
    ) -> "ConfidenceCalibration":
        if len(raw_scores) != len(labels):
            raise ValueError("Scores and labels must have the same length")
        if not raw_scores:
            return cls.identity(version=version)
        if search_grid is None:
            search_grid = [round(0.25 + 0.05 * i, 2) for i in range(96)]

        best_temp = 1.0
        best_loss = float("inf")
        for temperature in search_grid:
            probs = [_clip_prob(_sigmoid(_logit(score) / max(temperature, 1e-6))) for score in raw_scores]
            loss = 0.0
            for y, p in zip(labels, probs):
                loss += -(y * math.log(p) + (1 - y) * math.log(1 - p))
            loss /= len(labels)
            if loss < best_loss:
                best_loss = loss
                best_temp = float(temperature)

        probs = [_clip_prob(_sigmoid(_logit(score) / max(best_temp, 1e-6))) for score in raw_scores]
        report = expected_calibration_error(labels, probs)
        return cls(
            method="temperature_scaling",
            version=version,
            status="complete",
            temperature=best_temp,
            fit_metrics={
                "brier_score": brier_score(labels, probs),
                "ece": report["ece"],
                "bins": report["bins"],
            },
        )

    @classmethod
    def fit_isotonic(
        cls,
        raw_scores: Sequence[float],
        labels: Sequence[int],
        *,
        version: str,
    ) -> "ConfidenceCalibration":
        if len(raw_scores) != len(labels):
            raise ValueError("Scores and labels must have the same length")
        if not raw_scores:
            return cls.identity(version=version)

        sorted_pairs = sorted(zip(raw_scores, labels), key=lambda pair: pair[0])
        sorted_scores = [float(score) for score, _ in sorted_pairs]
        sorted_labels = [float(label) for _, label in sorted_pairs]

        blocks = _pava_blocks(sorted_scores, sorted_labels)
        if not blocks:
            blocks = [
                {"start": 0.0, "end": 0.0, "mean": 0.0},
                {"start": 1.0, "end": 1.0, "mean": 1.0},
            ]
        breakpoints = [(block["end"], block["mean"]) for block in blocks]
        probs = [cls(method="isotonic", version=version, status="complete", isotonic_breakpoints=breakpoints).predict(score) for score in raw_scores]
        report = expected_calibration_error(labels, probs)
        return cls(
            method="isotonic",
            version=version,
            status="complete",
            isotonic_breakpoints=breakpoints,
            fit_metrics={
                "brier_score": brier_score(labels, probs),
                "ece": report["ece"],
                "bins": report["bins"],
            },
        )

    def summary(self, raw_scores: Sequence[float], labels: Sequence[int]) -> Dict[str, Any]:
        calibrated = [self.predict(score) for score in raw_scores]
        report = expected_calibration_error(labels, calibrated)
        return {
            "method": self.method,
            "version": self.version,
            "status": self.status,
            "calibrated_probability": calibrated,
            "brier_score": brier_score(labels, calibrated),
            "ece": report["ece"],
            "reliability_diagram": report["bins"],
        }


def select_threshold(values: Sequence[float], labels: Sequence[int]) -> Tuple[float, Dict[str, float]]:
    if len(values) != len(labels):
        raise ValueError("Values and labels must have the same length")
    if not values:
        return 0.5, {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    candidates = sorted(set(values))
    if 0.0 not in candidates:
        candidates.insert(0, 0.0)
    if 1.0 not in candidates:
        candidates.append(1.0)

    best_threshold = candidates[0]
    best_metrics = {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    best_f1 = -1.0

    for threshold in candidates:
        preds = [1 if value < threshold else 0 for value in values]
        metrics = precision_recall_f1(labels, preds)
        f1 = metrics["f1"]
        if f1 > best_f1 or (f1 == best_f1 and threshold < best_threshold):
            best_f1 = f1
            best_threshold = threshold
            best_metrics = metrics

    return best_threshold, best_metrics


def calibrate_threshold(
    metric: str,
    values: Sequence[float],
    labels: Sequence[int],
    *,
    dataset: str,
    split: str,
    calibration_version: str,
) -> CalibrationResult:
    threshold, pr = select_threshold(values, labels)
    roc = roc_auc_score(labels, values)
    pr_auc = pr_auc_score(labels, values)
    return CalibrationResult(
        metric=metric,
        threshold=threshold,
        precision=pr["precision"],
        recall=pr["recall"],
        f1=pr["f1"],
        roc_auc=roc,
        pr_auc=pr_auc,
        split=split,
        dataset=dataset,
        calibration_version=calibration_version,
        date=datetime.now(timezone.utc).isoformat(),
    )
