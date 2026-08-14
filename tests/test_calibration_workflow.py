import json

from scripts.calibrate import CalibrationExample, run_calibration_workflow


def test_calibration_workflow_fits_and_evaluates_holdout(tmp_path):
    examples = [
        CalibrationExample(case_id="a", health=0.1, failure_label=1, confidence_score=0.9, confidence_label=1),
        CalibrationExample(case_id="b", health=0.2, failure_label=1, confidence_score=0.8, confidence_label=1),
        CalibrationExample(case_id="c", health=0.8, failure_label=0, confidence_score=0.2, confidence_label=0),
        CalibrationExample(case_id="d", health=0.9, failure_label=0, confidence_score=0.1, confidence_label=0),
    ]

    threshold_path = tmp_path / "threshold.json"
    confidence_path = tmp_path / "confidence.json"
    result = run_calibration_workflow(
        examples,
        calibration_ratio=0.5,
        seed=1,
        threshold_output=str(threshold_path),
        confidence_output=str(confidence_path),
    )

    assert result["split"]["calibration_size"] == 2
    assert result["split"]["holdout_size"] == 2
    assert result["threshold"]["fit"]["threshold"] is not None
    assert result["threshold"]["holdout"] is not None
    assert result["confidence"]["fit"] is not None
    assert result["confidence"]["holdout"] is not None
    assert threshold_path.exists()
    assert confidence_path.exists()

    with open(threshold_path, "r", encoding="utf-8") as handle:
        threshold_artifact = json.load(handle)
    with open(confidence_path, "r", encoding="utf-8") as handle:
        confidence_artifact = json.load(handle)

    assert threshold_artifact["threshold"] is not None
    assert confidence_artifact["method"] in {"temperature_scaling", "isotonic"}
