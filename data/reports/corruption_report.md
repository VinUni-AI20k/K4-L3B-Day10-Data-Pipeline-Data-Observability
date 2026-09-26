# Data Corruption, Repair & Recovery Report

## Performance Comparison

| Metric | Baseline | Corrupted | Repaired |
| :--- | ---: | ---: | ---: |
| Retrieval Hit Rate | 1.0000 | 0.6000 | 1.0000 |
| Mean Token F1 | 1.0000 | 0.5817 | 1.0000 |
| Judge Accuracy | 1.0000 | 0.6000 | 1.0000 |
| Mean Judge Score | 5.00 | 3.20 | 5.00 |

## Data Quality and Freshness

| Check | Corrupted | Repaired |
| :--- | :--- | :--- |
| Quality Gate | FAIL | PASS |
| Freshness SLA | FRESH | FRESH |
| Stale rows | 3/21 | 1/24 |

## Recovery Evidence

The repaired dataset was regenerated from `data/raw/crossref_records.json`, then re-indexed in a separate ChromaDB collection.
