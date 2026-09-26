# Data Observability & Idempotent Repair Report — 3-State Comparison

- **Report Date:** 2026-09-26 03:57:26 UTC

## 📊 Comparison Matrix (Baseline vs Corrupted vs Repaired)

| Metric / Dimension | Baseline (Clean) | Corrupted (Degraded) | Repaired (Restored) |
| :--- | :---: | :---: | :---: |
| **Total Record Count** | `24` | `23` | `24` |
| **Quality Gate Status (GX 1.x)** | `PASS` | `FAIL` | `PASS` |
| **Data Freshness SLA** | `FRESH` | `FRESH` | `FRESH` |
| **Retrieval Hit Rate** | `100.00%` | `70.00%` | `100.00%` |
| **Mean Token F1** | `0.6676` | `0.4500` | `0.6676` |
| **Judge Accuracy** | `70.00%` | `50.00%` | `70.00%` |
| **Mean Judge Score** | `3.20` | `2.60` | `3.20` |

---
## 🔍 Observations & Findings

1. **Silent Failure Detection:** When synthetic data corruption occurred, the RAG Retrieval Hit Rate dropped to `70.00%`, proving that corrupted vectors silently degrade LLM answer quality.
2. **Observability Gate Alarm:** Great Expectations 1.x correctly detected data quality anomalies and flagged `Quality Gate Status = FAIL` under the corrupted state.
3. **Idempotent Repair Guarantee:** Re-ingesting from raw preserved snapshots (`crossref_records.json`) restored 100% of answer accuracy (`100.00%` Hit Rate) without external API dependencies.
