# Corruption Flow Report — Baseline vs Corrupted vs Repaired

The same evaluation set is used across all three states so the comparison is valid.

## Performance comparison

| Metric | Baseline | Corrupted | Repaired | Corrupted − Baseline | Repaired − Corrupted |
|---|---:|---:|---:|---:|---:|
| retrieval_hit_rate | 1.0000 | 0.6000 | 1.0000 | -0.4000 | +0.4000 |
| mean_token_f1 | 1.0000 | 0.9000 | 1.0000 | -0.1000 | +0.1000 |
| judge_accuracy | 1.0000 | 0.9000 | 1.0000 | -0.1000 | +0.1000 |
| mean_judge_score | 5 | 4.6000 | 5 | -0.4000 | +0.4000 |
| samples | 10 | 10 | 10 | +0.0000 | +0.0000 |

## Data quality and freshness

| Signal | Corrupted | Repaired |
|---|---|---|
| GX success | False | True |
| row_count | 22 | 24 |
| is_fresh | False | True |
| stale_rows | 14/22 | 1/24 |

## Interpretation

- Corrupted data trips the Great Expectations gate (duplicate IDs, blank/short summaries, truncated titles) and the freshness SLA.
- Retrieval hit rate and token F1 drop because documents are missing, titles no longer match, and summaries are blank or noisy. That is silent failure: the agent still answers, but the answers are worse.
- Repair rebuilds the clean dataframe from the raw Crossref snapshot, so the quality gate and retrieval metrics recover.

## Artifacts

- `data/results/corruption_log.json`
- `data/results/corrupted_metrics.json`
- `data/results/repaired_metrics.json`
- `data/quality/corrupted_quality_report.json`
- `data/clean/papers_clean_corrupted.json`
- `data/clean/papers_clean_repaired.json`
