# Phase 1 Baseline Report

## Source and cleaned data

- Source: Crossref REST API
- Records: 24
- Clean rows: 24
- Embedding model: sentence-transformers/all-MiniLM-L6-v2
- Chroma collection: `papers-baseline`

## Baseline metrics

| Metric | Value |
|---|---:|
| `retrieval_hit_rate` | 1.0 |
| `mean_token_f1` | 0.5 |
| `judge_accuracy` | 0.5 |
| `mean_judge_score` | 3 |

## Great Expectations quality gate

- Overall status: **PASS**

| Expectation | Status |
|---|---|
| `row_count` | PASS |
| `paper_id_not_null` | PASS |
| `title_not_null` | PASS |
| `text_for_embedding_not_null` | PASS |
| `paper_id_unique` | PASS |
| `summary_length` | PASS |

## Freshness SLA

- Status: **FRESH**
- Stale rows: 0 / 24
- Stale ratio: 0.0
- Threshold: age_days > 180 and ratio > 0.25

## Conclusion

The baseline pipeline completed ingestion, cleaning, indexing, evaluation, and observability checks.
