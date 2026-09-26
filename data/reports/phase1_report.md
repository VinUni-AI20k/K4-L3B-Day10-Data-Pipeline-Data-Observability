# Phase 1 Report — Baseline Data Pipeline

## Source summary

- API: Crossref REST API
- Query: `agentic retrieval augmented generation large language model`
- Raw records: 24
- Clean records: 24
- Run date: 2026-09-26T03:54:28.525154+00:00
- Embedding model: sentence-transformers/all-MiniLM-L6-v2
- Collection: papers-baseline

## Baseline evaluation

| Metric | Value |
|---|---:|
| samples | 10 |
| retrieval_hit_rate | 1.0000 |
| mean_token_f1 | 1.0000 |
| judge_accuracy | 1.0000 |
| mean_judge_score | 5 |

## Data quality (Great Expectations 1.x)

- success=True, rows=24
- Expectations: ExpectTableRowCountToBeBetween, ExpectColumnValuesToNotBeNull, ExpectColumnValuesToBeUnique, ExpectColumnValueLengthsToBeBetween

## Freshness SLA

- is_fresh=True, stale_rows=1/24, latest=2026-07-22, oldest=2026-03-28
- Threshold: age_days > 180 on more than 25% of rows sets `is_fresh=False`.

## Artifacts

- `data/clean/papers_clean.csv` / `papers_clean.json`
- `data/chroma/` collection `papers-baseline`
- `data/eval/test_set.json`
- `data/results/baseline_metrics.json`
- `data/quality/baseline_quality_report.json`
- `data/quality/freshness_report.json`
