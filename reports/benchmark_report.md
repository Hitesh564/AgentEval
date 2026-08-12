# AgentEval Benchmark Report

## Dataset
- Source traces: 90 evaluated benchmark records from examples/fixtures/test_cases.yaml.
- Unique case IDs: 45.
- Benchmark mode: replay.
- Seed: 13.
- Bootstrap samples: 1000.
- Generated at (UTC): 2026-08-12T13:55:45.588218+00:00.
- Git commit: 67c86e7.
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
- random: accuracy=0.222, macro_f1=0.178, balanced_accuracy=0.176
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
- Threshold calibration fit on a benchmark-derived dataset with 63 calibration examples and 27 holdout examples.
- Fit threshold: 1.000
- Holdout F1: 0.800
- Holdout ROC-AUC: 0.898
- Holdout PR-AUC: 0.982
- Confidence calibration fit available: False.
- Confidence calibration remains pending because the exported benchmark-derived dataset does not include labeled confidence scores.

## Statistical Uncertainty
- Cases / records: 45 / 90
- Bootstrap samples: 1000
- Accuracy: 0.711 [95% CI: 0.589-0.834]
- Macro F1: 0.672 [95% CI: 0.541-0.820]
- Balanced Accuracy: 0.742 [95% CI: 0.608-0.835]

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