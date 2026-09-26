# Phase 1 Baseline Report: Data Pipeline & Data Observability

> **Execution Timestamp:** 2026-09-26 04:09:54 UTC  
> **Pipeline Run Status:** COMPLETED  
> **Overall Data Quality Gate:** **PASSED**  

---

## 1. Executive Summary

This report documents the baseline performance and data quality metrics for the RAG data pipeline before any corruption injection.
The pipeline integrates metadata ingestion from Crossref, rigorous data cleaning, Great Expectations 1.x validation gates, Freshness SLA monitoring, ChromaDB vector indexing, and baseline RAG retrieval benchmarking.

- **Total Ingested Records:** 24
- **Vector Store Collection:** `papers-baseline`
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Retrieval Hit Rate:** **100.00%**
- **Mean Token F1:** **1.0000**
- **Judge Accuracy:** **100.00%** (Mean Score: 5.00 / 5.0)
- **Data Quality Gate (GX 1.x):** **PASSED**
- **Freshness SLA Status:** **FRESH** (1/24 stale records, 4.2%)

---

## 2. Ingestion & Data Source Summary

| Parameter | Value |
|:---|:---|
| **Source API** | Crossref REST API |
| **Search Query** | `N/A` |
| **Filter** | `N/A` |
| **Max Results** | 24 |
| **Raw API Response** | `data/raw/crossref_response.json` |
| **Raw Records** | `data/raw/crossref_records.json` |
| **Clean Data Output** | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` |

---

## 3. Data Observability Gate (Great Expectations 1.x)

The data observability gate verifies the cleaned dataset against 4 essential expectations using Ephemeral Context:

| Expectation | Status | Observed / Unexpected |
|:---|:---:|:---|
| `ExpectTableRowCountToBeBetween` | PASS | 24 |
| `ExpectColumnValuesToNotBeNull` | PASS | 0 |
| `ExpectColumnValuesToNotBeNull` | PASS | 0 |
| `ExpectColumnValuesToNotBeNull` | PASS | 0 |
| `ExpectColumnValuesToBeUnique` | PASS | 0 |
| `ExpectColumnValueLengthsToBeBetween` | PASS | 0 |

- **Great Expectations Overall Status:** **PASSED**

---

## 4. Freshness SLA Monitoring

- **Threshold SLA:** 180 days
- **Maximum Permitted Stale Ratio:** 25.0%
- **Total Records:** 24
- **Stale Records (> 180 days):** 1 (4.17%)
- **Latest Published Date:** 2026-07-22
- **Oldest Published Date:** 2026-03-28
- **Freshness Status:** **FRESH (Complies with SLA threshold)**

---

## 5. Baseline Retrieval & Agent Evaluation

The pipeline was benchmarked using the standard 10-question evaluation set covering 4 business problem types (`summary`, `authors`, `date`, `categories`):

| Evaluation Metric | Baseline Score | Target Threshold | Status |
|:---|:---:|:---:|:---:|
| **Evaluation Samples** | 10 | 10 | PASS |
| **Retrieval Hit Rate** | **100.00%** | >= 80% | PASS |
| **Mean Token F1** | **1.0000** | >= 0.85 | PASS |
| **Judge Accuracy** | **100.00%** | >= 80% | PASS |
| **Mean Judge Score** | **5.00 / 5.0** | >= 4.0 / 5.0 | PASS |

---

## 6. Artifact Verification Checklist

- [x] `data/raw/crossref_response.json` (Preserved raw API payload)
- [x] `data/raw/crossref_records.json` (Extracted raw records)
- [x] `data/clean/papers_clean.csv` (Normalized clean CSV)
- [x] `data/clean/papers_clean.json` (Normalized clean JSON)
- [x] `data/chroma/` (ChromaDB persistent collection `papers-baseline`)
- [x] `data/embeddings/papers_embeddings.json` (Embeddings manifest)
- [x] `data/eval/test_set.json` (10-question benchmark dataset)
- [x] `data/quality/baseline_quality_report.json` (GX 1.x quality validation report)
- [x] `data/quality/freshness_report.json` (Freshness SLA report)
- [x] `data/results/baseline_metrics.json` (Retrieval & generation metrics)
- [x] `data/results/baseline_answers.json` (Individual answer predictions)
- [x] `data/reports/phase1_report.md` (Comprehensive Phase 1 report)
