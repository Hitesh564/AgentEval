# AgentEval Benchmark Report

## Dataset
- Source traces: 90 evaluated benchmark records from examples/fixtures/test_cases.yaml.
- Unique case IDs: 45.
- Benchmark mode: replay.
- Seed: 0.
- Bootstrap samples: 1000.
- Generated at (UTC): 2026-08-13T11:00:17.274507+00:00.
- Git commit: db23329.
- Who&When adapter evaluation is reported separately and is not included in this benchmark run unless explicitly executed.

## Evaluation Protocol
- Version A (baseline) and Version B (current) are derived from stored traces and fixture labels.
- Balanced accuracy averages only over classes with non-zero ground-truth support.
- Macro-F1 follows the same support-aware class set used for the final report.
- Threshold calibration reports use failure score = 1 - health for ROC-AUC and PR-AUC.

## Summary
- Accuracy: 0.733
- Macro Precision: 0.787
- Macro Recall: 0.762
- Macro F1: 0.698
- Balanced Accuracy: 0.762
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
- v2: accuracy=0.733, macro_f1=0.698, balanced_accuracy=0.762

## Ablation Results
| Variant | Accuracy | Macro F1 | Balanced Accuracy | Top-k Accuracy |
| --- | --- | --- | --- | --- |
| last_failure | 0.533 | 0.467 | 0.436 | n/a |
| v1_attribution | 0.667 | 0.566 | 0.542 | 0.689 |
| v2_no_causal_origin | 0.622 | 0.623 | 0.676 | 0.689 |
| v2_full | 0.733 | 0.698 | 0.762 | 0.689 |

## Who&When Results
- Full official Who&When validation was executed in replay mode using the local dataset files.
- Dataset counts:
  - Algorithm-Generated: 126 cases
  - Hand-Crafted: 58 cases
  - Total: 184 cases
- Full-run metrics:
  - Accuracy: 0.408
  - Macro F1: 0.353
  - Balanced Accuracy: 0.351
  - Step Accuracy: 0.147
  - Exact Match: 0.147
  - Top-k Accuracy: 0.408
- Full report artifact: `artifacts/who_when_full_report.json`
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
- Accuracy: 0.733 [95% CI: 0.622-0.844]
- Macro F1: 0.698 [95% CI: 0.564-0.835]
- Balanced Accuracy: 0.762 [95% CI: 0.644-0.849]

## Confusion Matrix
| true \ pred | retriever | planner | generator | none | ambiguous |
| --- | --- | --- | --- | --- | --- |
| retriever | 14 | 0 | 0 | 6 | 0 |
| planner | 0 | 8 | 0 | 10 | 0 |
| generator | 0 | 0 | 16 | 0 | 8 |
| none | 0 | 0 | 0 | 24 | 0 |
| ambiguous | 0 | 0 | 0 | 0 | 4 |

## Per-Class Performance
| Class | Support | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| retriever | 20 | 1.000 | 0.700 | 0.824 |
| planner | 18 | 1.000 | 0.444 | 0.615 |
| generator | 24 | 1.000 | 0.667 | 0.800 |
| none | 24 | 0.600 | 1.000 | 0.750 |
| ambiguous | 4 | 0.333 | 1.000 | 0.500 |

## Limitations
- This report is based on the stored benchmark traces in the repository, not a broad external evaluation set.
- Confidence calibration metrics may apply only to the calibrated subset, so coverage should be checked alongside ECE and Brier score.
- Ablation results are directional; no statistical significance is claimed here.
