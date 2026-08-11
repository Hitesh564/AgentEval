# AgentEval Benchmark Report

## Summary
- Accuracy: 0.622
- Macro Precision: 0.648
- Macro Recall: 0.563
- Macro F1: 0.510
- Balanced Accuracy: 0.563
- Top-k Accuracy: 0.689
- ECE: 0.600
- Brier Score: 0.582

## Baselines
- random: accuracy=0.200, macro_f1=0.158, balanced_accuracy=0.177
- majority: accuracy=0.267, macro_f1=0.070, balanced_accuracy=0.167
- last_failure: accuracy=0.533, macro_f1=0.389, balanced_accuracy=0.363
- v1: accuracy=0.667, macro_f1=0.472, balanced_accuracy=0.452
- v2: accuracy=0.622, macro_f1=0.510, balanced_accuracy=0.563

## Confusion Matrix
| true \ pred | ambiguous | critic | generator | none | planner | retriever |
| --- | --- | --- | --- | --- | --- | --- |
| ambiguous | 4 | 0 | 0 | 0 | 0 | 0 |
| critic | 0 | 0 | 0 | 0 | 0 | 0 |
| generator | 8 | 8 | 8 | 0 | 0 | 0 |
| none | 0 | 0 | 0 | 24 | 0 | 0 |
| planner | 0 | 0 | 0 | 10 | 8 | 0 |
| retriever | 2 | 0 | 0 | 6 | 0 | 12 |