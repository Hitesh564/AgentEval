# AgentEval Benchmark Report

## Dataset
- Source traces: 90 evaluated benchmark records from examples/fixtures/test_cases.yaml.
- Benchmark mode: replay.
- Who&When adapter evaluation is reported separately and is not included in this benchmark run unless explicitly executed.

## Evaluation Protocol
- Version A (baseline) and Version B (current) are derived from stored traces and fixture labels.
- Balanced accuracy averages only over classes with non-zero ground-truth support.
- Macro-F1 follows the same support-aware class set used for the final report.
- Threshold calibration reports use failure score = 1 - health for ROC-AUC and PR-AUC.

## Summary
- Accuracy: 0.711
- Macro Precision: 0.777
- Macro Recall: 0.742
- Macro F1: 0.672
- Balanced Accuracy: 0.742
- Top-k Accuracy: 0.689

## Label Distribution
- retriever: 20
- planner: 18
- generator: 24
- none: 24
- ambiguous: 4

## Baselines
- random: accuracy=0.200, macro_f1=0.190, balanced_accuracy=0.213
- majority: accuracy=0.267, macro_f1=0.084, balanced_accuracy=0.200
- last_failure: accuracy=0.533, macro_f1=0.467, balanced_accuracy=0.436
- v1: accuracy=0.667, macro_f1=0.566, balanced_accuracy=0.542
- v2: accuracy=0.711, macro_f1=0.672, balanced_accuracy=0.742

## Ablation Results
| Variant | Accuracy | Macro F1 | Balanced Accuracy | Top-k Accuracy |
| --- | --- | --- | --- | --- |
| last_failure | 0.533 | 0.467 | 0.436 | n/a |
| v1_attribution | 0.667 | 0.566 | 0.542 | 0.689 |
| v2_no_causal_origin | 0.622 | 0.612 | 0.676 | 0.689 |
| v2_full | 0.711 | 0.672 | 0.742 | 0.689 |

## Who&When Results
- Not executed in this benchmark run.
- The Who&When adapter evaluates both agent and step attribution when run directly via `python -m agenteval.adapters.who_when_adapter`.
- Adapter assumptions: history is converted to single-parent session chains and step IDs are derived from history order.

## Calibration Results
- Dedicated calibration workflow available at `python -m scripts.calibrate`.
- This benchmark run does not fit a new calibrator; it only reports whether calibrated confidence values were available in the evaluated records.

## Confusion Matrix
| true \ pred | retriever | planner | generator | none | ambiguous |
| --- | --- | --- | --- | --- | --- |
| retriever | 12 | 0 | 0 | 6 | 2 |
| planner | 0 | 8 | 0 | 10 | 0 |
| generator | 0 | 0 | 16 | 0 | 8 |
| none | 0 | 0 | 0 | 24 | 0 |
| ambiguous | 0 | 0 | 0 | 0 | 4 |

## Per-Class Performance
| Class | Support | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| retriever | 20 | 1.000 | 0.600 | 0.750 |
| planner | 18 | 1.000 | 0.444 | 0.615 |
| generator | 24 | 1.000 | 0.667 | 0.800 |
| none | 24 | 0.600 | 1.000 | 0.750 |
| ambiguous | 4 | 0.286 | 1.000 | 0.444 |

## Limitations
- This report is based on the stored benchmark traces in the repository, not a broad external evaluation set.
- Confidence calibration metrics may apply only to the calibrated subset, so coverage should be checked alongside ECE and Brier score.
- Ablation results are directional; no statistical significance is claimed here.