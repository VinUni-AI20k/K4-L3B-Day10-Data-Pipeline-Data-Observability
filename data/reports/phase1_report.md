# Phase 1 Report - Baseline Pipeline

_Generated at: 2026-09-26T03:50:47.771706+00:00_

## 1. Source Summary

- **source_api**: Crossref REST API
- **source_query**: agentic retrieval augmented generation large language model
- **source_filter**: from-pub-date:2026-03-30,has-abstract:true
- **max_results**: 24
- **records_fetched**: 24
- **records_clean**: 24

## 2. Retrieval / Evaluation Metrics

| Metric | Value |
| :--- | ---: |
| Samples | 10 |
| Retrieval Hit Rate | 100.0% |
| Mean Token F1 | 0.520 |
| Judge Accuracy | 50.0% |
| Mean Judge Score | 3.000 |

## 3. Data Quality Gate

- **Status (success)**: `True`

## 4. Freshness SLA

- **is_fresh**: `True`
- **latest_published**: 2026-07-22
- **oldest_published**: 2026-03-28
- **stale_rows / total_rows**: 1 / 24

