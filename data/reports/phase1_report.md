# Phase 1 Baseline Data Pipeline & Observability Report

## 1. Data Ingestion Summary
- **Source API:** Crossref REST API
- **Total Records Ingested:** 24
- **Raw Artifacts:** Saved to `data/raw/crossref_response.json` & `data/raw/crossref_records.json`

## 2. Baseline RAG Performance Metrics
- **Retrieval Hit Rate:** 100.00%
- **Mean Token F1 Score:** 0.5000
- **LLM Judge Accuracy:** 50.00%

## 3. Data Observability & Freshness SLA
- **Great Expectations 1.x Quality Check:** PASSED (True)
- **Freshness SLA Status:** FRESH (True)
- **Stale Rows Ratio (>180 days):** 4.17% (1/24)

---
*Report generated automatically by Day 10 Baseline Pipeline.*
