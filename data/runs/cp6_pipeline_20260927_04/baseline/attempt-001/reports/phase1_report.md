# Phase 1 baseline report

## Source and indexing

- Source: Crossref REST API
- Ingestion mode: immutable local snapshot
- Snapshot: `../../../raw/crossref_records.json`
- Run time (UTC): 2026-09-27T08:53:12.754647+00:00
- Raw records: 24
- Clean records: 24
- Removed during cleaning: 0
- Chroma collection: `papers-baseline-15f5e6657232`
- Indexed documents: 24
- Benchmark questions: 10
- Raw snapshot SHA-256: 87b6413046082aa85518ebd6142aa5fccc88926dcbb65c83de60e9302e62446e
- Frozen test set SHA-256: 19d5ac3b18cab70db178c29a7bac72328f386c375e9df1abe12459fb3b4dd03f

## Stage results

| Stage | Result |
| --- | --- |
| 1. Ingest | 24 records |
| 2. Clean | 24 rows; 0 removed |
| 3. Quality gate before indexing | PASS |
| 4. Index and frozen benchmark | 24 documents; 10 questions |
| 5. Evaluate | 10 answers scored |
| 6. Report | Generated from measured results |

## Evaluation

Answers use the existing extractive QA component, with exact-ID lookup followed by semantic retrieval. Hit Rate measures whether a reference document appears in retrieved results; Token F1 measures answer/reference token-set overlap.
Configured judge provider: mock; model: mock. The existing evaluator may use its heuristic judge fallback; judge scores do not affect Hit Rate or Token F1.
Heuristic judge answers: 10/10. Answers are extractive metadata QA, not an online LLM generation benchmark. Explicit missing paper references abstain.

| Measure | Result |
| --- | ---: |
| Evaluated questions | 10 |
| Retrieval Hit Rate | 100.00% |
| Mean Token F1 | 1.0000 |
| Answer source Hit Rate | 100.00% |
| Grounded Token F1 | 1.0000 |
| Abstention rate | 0.00% |
| Judge accuracy | 100.00% |
| Mean judge score | 5.00/5 |
- Ragas: skipped (Set RUN_RAGAS=1 to enable the slower Ragas pass.)

## Data quality

| Check | Result |
| --- | ---: |
| Quality gate passed | True |
| Great Expectations passed | True |
| Expectations passed | 7/7 |

## Freshness SLA

- Latest publication: 2026-07-22
- Oldest publication: 2026-03-28
- Stale rule: age_days > 180
- Stale records: 1/24
- Stale share: 4.17%
- Maximum allowed stale share: 25.00%
- Invalid age values: 0
- Freshness passed: True
