# Corruption and Repair Report

## Metric comparison

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| `judge_accuracy` | 0.5 | 0.4 | 0.5 |
| `mean_judge_score` | 3 | 2.7 | 3 |
| `mean_token_f1` | 0.5 | 0.4 | 0.5 |
| `retrieval_hit_rate` | 1.0 | 0.9 | 1.0 |
| `samples` | 10 | 10 | 10 |

## Quality gate comparison

| Stage | Quality gate | Freshness |
|---|---|---|
| Baseline | PASS | FRESH |
| Corrupted | FAIL | FRESH |
| Repaired | PASS | FRESH |

## Interpretation

The corrupted dataset is generated from the clean baseline using the six logged scenarios. The repaired dataset is rebuilt from the trusted raw records, then indexed and evaluated again.
