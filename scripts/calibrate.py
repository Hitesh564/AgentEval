import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from agenteval.eval.calibration import (
    ConfidenceCalibration,
    ThresholdCalibrationArtifact,
    brier_score,
    calibrate_threshold,
    expected_calibration_error,
    precision_recall_f1,
    pr_auc_score,
    roc_auc_score,
)
from agenteval.utils.miniyaml import load_structured_data


@dataclass(frozen=True)
class CalibrationExample:
    case_id: str
    health: float
    failure_label: int
    confidence_score: Optional[float] = None
    confidence_label: Optional[int] = None


def _load_raw_examples(path: str) -> List[Dict[str, Any]]:
    data = load_structured_data(path)
    if isinstance(data, dict) and "examples" in data:
        data = data["examples"]
    if not isinstance(data, list):
        raise ValueError("Calibration file must contain a list of examples or an {examples: [...]} object")
    return data


def _parse_bool_label(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return 1 if float(value) > 0.5 else 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "failure", "failed", "bad"}:
        return 1
    return 0


def load_examples(path: str) -> List[CalibrationExample]:
    raw = _load_raw_examples(path)
    examples: List[CalibrationExample] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        health = item.get("health", item.get("value", item.get("score")))
        label = item.get("failure_label", item.get("label", item.get("target")))
        if health is None or label is None:
            continue
        confidence_score = item.get("confidence_score", item.get("confidence_value"))
        confidence_label = item.get("confidence_label", item.get("confidence_target"))
        examples.append(
            CalibrationExample(
                case_id=str(item.get("case_id", item.get("id", f"case_{idx}"))),
                health=float(health),
                failure_label=_parse_bool_label(label),
                confidence_score=float(confidence_score) if confidence_score is not None else None,
                confidence_label=_parse_bool_label(confidence_label) if confidence_label is not None else None,
            )
        )
    return examples


def split_examples(
    examples: Sequence[CalibrationExample],
    *,
    calibration_ratio: float = 0.7,
    seed: int = 0,
) -> Tuple[List[CalibrationExample], List[CalibrationExample]]:
    if not 0.0 < calibration_ratio < 1.0:
        raise ValueError("calibration_ratio must be between 0 and 1")
    shuffled = list(examples)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    split_idx = max(1, min(len(shuffled) - 1, int(round(len(shuffled) * calibration_ratio)))) if len(shuffled) > 1 else len(shuffled)
    return shuffled[:split_idx], shuffled[split_idx:]


def _evaluate_threshold(values: Sequence[float], labels: Sequence[int], threshold: float) -> Dict[str, Any]:
    preds = [1 if value < threshold else 0 for value in values]
    pr = precision_recall_f1(labels, preds)
    failure_scores = [1.0 - float(v) for v in values]
    return {
        "threshold": threshold,
        "precision": pr["precision"],
        "recall": pr["recall"],
        "f1": pr["f1"],
        "roc_auc": roc_auc_score(labels, failure_scores),
        "pr_auc": pr_auc_score(labels, failure_scores),
    }


def run_calibration_workflow(
    examples: Sequence[CalibrationExample],
    *,
    calibration_ratio: float = 0.7,
    seed: int = 0,
    threshold_output: Optional[str] = None,
    confidence_output: Optional[str] = None,
    report_output: Optional[str] = None,
    confidence_method: str = "temperature",
    confidence_version: str = "calibration-workflow",
) -> Dict[str, Any]:
    calibration_set, holdout_set = split_examples(examples, calibration_ratio=calibration_ratio, seed=seed)
    if not calibration_set:
        raise ValueError("Calibration set is empty")

    cal_health = [example.health for example in calibration_set]
    cal_labels = [example.failure_label for example in calibration_set]
    threshold_result = calibrate_threshold(
        metric="overall_health",
        values=cal_health,
        labels=cal_labels,
        dataset="manual-calibration",
        split="calibration",
        calibration_version="threshold-workflow-v1",
    )
    threshold_artifact = ThresholdCalibrationArtifact(
        metric=threshold_result.metric,
        threshold=threshold_result.threshold,
        precision=threshold_result.precision,
        recall=threshold_result.recall,
        f1=threshold_result.f1,
        roc_auc=threshold_result.roc_auc,
        pr_auc=threshold_result.pr_auc,
        split=threshold_result.split,
        dataset=threshold_result.dataset,
        dataset_version="unknown",
        calibration_version=threshold_result.calibration_version,
        timestamp=threshold_result.date,
        configuration={"calibration_ratio": calibration_ratio, "seed": seed},
    )
    if threshold_output:
        threshold_artifact.save_json(threshold_output)

    threshold_holdout = None
    if holdout_set:
        threshold_holdout = _evaluate_threshold(
            [example.health for example in holdout_set],
            [example.failure_label for example in holdout_set],
            threshold_artifact.threshold,
        )

    confidence_calibration: Optional[ConfidenceCalibration] = None
    confidence_holdout: Optional[Dict[str, Any]] = None
    cal_conf_scores = [example.confidence_score for example in calibration_set if example.confidence_score is not None and example.confidence_label is not None]
    cal_conf_labels = [example.confidence_label for example in calibration_set if example.confidence_score is not None and example.confidence_label is not None]
    if cal_conf_scores and cal_conf_labels:
        if confidence_method == "temperature":
            confidence_calibration = ConfidenceCalibration.fit_temperature_scaling(
                cal_conf_scores,
                cal_conf_labels,
                version=confidence_version,
            )
        elif confidence_method == "isotonic":
            confidence_calibration = ConfidenceCalibration.fit_isotonic(
                cal_conf_scores,
                cal_conf_labels,
                version=confidence_version,
            )
        else:
            raise ValueError("confidence_method must be 'temperature' or 'isotonic'")
        if confidence_output:
            confidence_calibration.save_json(confidence_output)

        holdout_conf_scores = [example.confidence_score for example in holdout_set if example.confidence_score is not None and example.confidence_label is not None]
        holdout_conf_labels = [example.confidence_label for example in holdout_set if example.confidence_score is not None and example.confidence_label is not None]
        if holdout_conf_scores and holdout_conf_labels:
            calibrated = [confidence_calibration.predict(score) for score in holdout_conf_scores]
            confidence_holdout = {
                "ece": expected_calibration_error(holdout_conf_labels, calibrated)["ece"],
                "brier_score": brier_score(holdout_conf_labels, calibrated),
                "reliability_diagram": expected_calibration_error(holdout_conf_labels, calibrated)["bins"],
            }

    return {
        "split": {
            "calibration_size": len(calibration_set),
            "holdout_size": len(holdout_set),
            "calibration_ratio": calibration_ratio,
        },
        "threshold": {
            "fit": threshold_result.to_dict(),
            "holdout": threshold_holdout,
            "artifact_path": threshold_output,
        },
        "confidence": {
            "fit": confidence_calibration.to_dict() if confidence_calibration is not None else None,
            "holdout": confidence_holdout,
            "artifact_path": confidence_output,
        },
        "limitations": [
            "- The workflow only reports holdout metrics when the supplied dataset includes labeled holdout examples.",
            "- Confidence calibration is skipped if the input file does not provide confidence scores and labels.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit threshold and confidence calibration artifacts.")
    parser.add_argument("--input", required=True, help="Path to labeled calibration examples (.json/.yaml)")
    parser.add_argument("--threshold-output", default="artifacts/threshold_calibration.json", help="Path to save the threshold artifact")
    parser.add_argument("--confidence-output", default="artifacts/confidence_calibration.json", help="Path to save the confidence artifact")
    parser.add_argument("--report-output", default="artifacts/calibration_report.json", help="Path to save the full calibration report")
    parser.add_argument("--calibration-ratio", type=float, default=0.7, help="Fraction of examples used for fitting")
    parser.add_argument("--seed", type=int, default=0, help="Deterministic shuffle seed")
    parser.add_argument("--confidence-method", choices=["temperature", "isotonic"], default="temperature", help="Confidence calibration method")
    parser.add_argument("--confidence-version", default="calibration-workflow", help="Version string for confidence calibration")
    args = parser.parse_args()

    examples = load_examples(args.input)
    if not examples:
        raise SystemExit("No valid calibration examples found in the input file.")

    result = run_calibration_workflow(
        examples,
        calibration_ratio=args.calibration_ratio,
        seed=args.seed,
        threshold_output=args.threshold_output,
        confidence_output=args.confidence_output,
        report_output=args.report_output,
        confidence_method=args.confidence_method,
        confidence_version=args.confidence_version,
    )

    if args.report_output:
        Path(args.report_output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.report_output, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
