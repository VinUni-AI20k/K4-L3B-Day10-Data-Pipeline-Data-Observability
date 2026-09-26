# Phase 1 Baseline Report

> Generated: 2026-09-26T03:09:25.111981+00:00

---

## 1. Data Source Summary

| Field | Value |
|---|---|
| Source API | Crossref REST API |
| Query | `agentic retrieval augmented generation large language model` |
| Raw records fetched | 24 |
| Clean records | 24 |

---

## 2. Baseline Evaluation Metrics

| Metric | Value |
|---|---|
| Retrieval Hit Rate | 100.0% |
| Mean Token F1 | 68.8% |
| Judge Accuracy | 80.0% |
| Mean Judge Score | 3.600 / 5 |
| Samples evaluated | 10 |

---

## 3. Data Quality Gate (Great Expectations)

**Overall status:** ✅ PASSED

| Expectation | Success | Details |
|---|---|---|
| `ExpectTableRowCountToBeBetween` | ✅ | {'observed_value': 24} |
| `ExpectColumnValuesToNotBeNull` | ✅ | {'element_count': 24, 'unexpected_count': 0, 'unexpected_percent': 0.0, 'partial |
| `ExpectColumnValuesToBeUnique` | ✅ | {'element_count': 24, 'unexpected_count': 0, 'unexpected_percent': 0.0, 'partial |
| `ExpectColumnValuesToNotBeNull` | ✅ | {'element_count': 24, 'unexpected_count': 0, 'unexpected_percent': 0.0, 'partial |
| `ExpectColumnValuesToNotBeNull` | ✅ | {'element_count': 24, 'unexpected_count': 0, 'unexpected_percent': 0.0, 'partial |
| `ExpectColumnValueLengthsToBeBetween` | ✅ | {'element_count': 24, 'unexpected_count': 0, 'unexpected_percent': 0.0, 'partial |

---

## 4. Freshness SLA

| Field | Value |
|---|---|
| Is Fresh | ✅ Yes |
| Latest Published | 2026-07-22 |
| Oldest Published | 2026-03-28 |
| Stale Rows (>180 days) | 1 / 24 |
| Stale Ratio | 4.2% |

---

_End of Phase 1 Report_
