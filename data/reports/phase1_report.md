# Phase 1 — Baseline Pipeline Report

Generated at: 2026-09-26T04:27:56.363446+00:00

## Data source and corpus

| Signal | Value |
| --- | --- |
| Source | Crossref REST API |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2026-03-30,has-abstract:true |
| Raw records | 24 |
| Clean records | 24 |
| Chroma collection | `papers-baseline` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Benchmark questions | 10 |

## Baseline RAG evaluation

| Metric | Value |
| --- | ---: |
| Samples | 10 |
| Retrieval hit rate | 1.0000 |
| Mean token F1 | 1.0000 |
| Judge accuracy | 1.0000 |
| Mean judge score | 5 |
| Ragas | Set RUN_RAGAS=1 to enable the slower Ragas pass. |

## Data quality gate

| Signal | Value |
| --- | --- |
| Overall gate | PASS |
| Great Expectations | PASS |
| Expectations evaluated | 6 |

### Expectation details

| Expectation | Status | Observed/element count | Unexpected count |
| --- | --- | ---: | ---: |
| `expect_table_row_count_to_be_between` | PASS | 24 | 0 |
| `expect_column_values_to_not_be_null` | PASS | 24 | 0 |
| `expect_column_values_to_be_unique` | PASS | 24 | 0 |
| `expect_column_values_to_not_be_null` | PASS | 24 | 0 |
| `expect_column_values_to_not_be_null` | PASS | 24 | 0 |
| `expect_column_value_lengths_to_be_between` | PASS | 24 | 0 |

## Freshness monitoring

| Signal | Value |
| --- | ---: |
| Status | PASS |
| Latest published | 2026-07-22 |
| Oldest published | 2026-03-28 |
| Stale threshold (days) | 180 |
| Stale rows | 1 |
| Total rows | 24 |
| Stale ratio | 0.0417 |

## Artifacts

| Artifact | Path |
| --- | --- |
| Raw API response | `data/raw/crossref_response.json` |
| Parsed raw records | `data/raw/crossref_records.json` |
| Clean CSV | `data/clean/papers_clean.csv` |
| Clean JSON | `data/clean/papers_clean.json` |
| Chroma database | `data/chroma` |
| Embedding manifest | `data/embeddings/papers_embeddings.json` |
| Benchmark test set | `data/eval/test_set.json` |
| Baseline answers | `data/results/baseline_answers.json` |
| Baseline metrics | `data/results/baseline_metrics.json` |
| Quality report | `data/quality/baseline_quality_report.json` |
| Freshness report | `data/quality/freshness_report.json` |

## Baseline conclusion

The baseline corpus passed the data quality gate and freshness SLA: **PASS**.
Retrieval hit rate is **1.0000** and mean token F1 is **1.0000** across **10** benchmark questions.
