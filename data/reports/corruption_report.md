# Data Corruption & Repair Comparison Report

_Generated at 2026-09-26T03:14:38.827185+00:00_

## Metrics Comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| retrieval_hit_rate | 1.0000 | 0.6000 | 1.0000 |
| mean_token_f1 | 0.7000 | 0.3788 | 0.7000 |
| judge_accuracy | 0.7000 | 0.3000 | 0.7000 |
| mean_judge_score | 3.8000 | 2.7000 | 3.8000 |

## Data Quality Comparison

| Stage | Success | Row Count |
| --- | --- | ---: |
| Corrupted | False | 23 |
| Repaired | True | 24 |

## Freshness Comparison

| Stage | Stale Rows | Total Rows | Stale Ratio | Is Fresh |
| --- | ---: | ---: | ---: | --- |
| Corrupted | 8 | 23 | 0.3478 | False |
| Repaired | 1 | 24 | 0.0417 | True |
