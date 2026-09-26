# Data Corruption & Repair Report

> Generated: 2026-09-26T03:11:12.493507+00:00

---

## Overview

This report demonstrates the impact of synthetic data corruption on a RAG pipeline
and validates that idempotent repair restores performance to the original baseline.

---

## 1. Metrics Comparison: Baseline vs Corrupted vs Repaired

| Metric | Baseline | Corrupted | Δ Corrupted | Repaired | Δ Repaired |
|---|---|---|---|---|---|
| Retrieval Hit Rate | 100.0% | 80.0% | -20.0% | 100.0% | +0.0% |
| Mean Token F1      | 68.8%  | 61.1%  | -7.7%  | 68.8%  | +0.0% |
| Judge Accuracy     | 80.0% | 60.0% | -20.0% | 80.0% | +0.0% |

> **Δ** = difference relative to Baseline (negative = degradation, near 0 = recovery).

---

## 2. Data Quality Gate Results

| State | Quality Gate Passed | Freshness OK |
|---|---|---|
| Baseline  | ✅ (reference) | ✅ (reference) |
| Corrupted | ❌ | ✅ |
| Repaired  | ✅ | ✅ |

---

## 3. Degradation Analysis (Silent Failure)

When the data corruption is injected, the RAG pipeline continues to serve requests
without runtime errors — this is the **Silent Failure** pattern. The Quality Gate
detects the anomalies *before* they propagate to end users.

**Corrupted state observations:**

- Retrieval Hit Rate dropped by 20.0pp (100.0% → 80.0%)
- Mean Token F1 dropped by 7.7pp (68.8% → 61.1%)
- Great Expectations quality gate **FAILED** on corrupted data (expected behaviour).

---

## 4. Recovery Analysis (Idempotent Repair)

The repair step re-builds the clean dataset **from the original raw records** (not from the corrupted state), guaranteeing idempotency.

**Repaired state observations:**

- ✅ Retrieval Hit Rate recovered to 100.0% (baseline: 100.0%)
- ✅ Mean Token F1 recovered to 68.8% (baseline: 68.8%)
- ✅ Great Expectations quality gate **PASSED** after repair.
- ✅ Freshness SLA restored after repair.

---

## 5. Freshness SLA Details

| Field | Corrupted | Repaired |
|---|---|---|
| Is Fresh | ✅ | ✅ |
| Latest Published | 2026-06-12 | 2026-07-22 |
| Stale Rows | 3 | 1 |

---

_End of Corruption & Repair Report_
