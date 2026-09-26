# Corruption & Self-Healing Evaluation Report

## 1. 3-State Performance Comparison Table

| Metric / Signal | 1. Baseline | 2. Corrupted | 3. Repaired | Impact & Recovery Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **`retrieval_hit_rate`** | **1.0000** | **0.8000** 🔻 | **1.0000** 🔺 | Drops due to missing latest records (20% dropped); fully recovers after repair. |
| **`mean_token_f1`** | **1.0000** | **0.7720** 🔻 | **1.0000** 🔺 | Degrades sharply because summaries were blanked & corrupted with noise payloads. |
| **`judge_accuracy`** | **1.0000** | **0.8000** 🔻 | **1.0000** 🔺 | Model correctness plummets when retrieved evidence is degraded (Silent Failure). |
| **`mean_judge_score`** | **5** | **4.10** 🔻 | **5** 🔺 | Overall qualitative score drops significantly on corrupted data. |
| **Data Quality Gate** | **PASS** | **FAIL** 🚨 | **PASS** ✅ | GX caught primary key collisions, missing content, and truncated titles. |
| **Freshness SLA** | **PASS** | **FAIL** ⚠️ | **PASS** ✅ | SLA violation detected when stale date exceeded 25% threshold. |

---

## 2. Silent Failure & Observability Analysis

### The Silent Failure Mechanism
When data corruption was introduced into the pipeline:
1. **No runtime exceptions were thrown** by the retrieval engine or embedding models. The application continued to serve queries without crashing.
2. However, the retrieval quality degraded significantly: `retrieval_hit_rate` fell from **1.0000** to **0.8000**, and answer token F1 dropped from **1.0000** to **0.7720**.
3. Without automated Data Observability, this degradation would remain undetected in production, directly harming end-user trust.

### Observability Gates as Circuit Breakers
The Great Expectations 1.x suite and Freshness SLA successfully acted as automated circuit breakers:
- **`ExpectColumnValuesToBeUnique`** detected the 2 duplicated `paper_id` rows.
- **`ExpectColumnValueLengthsToBeBetween`** detected the 2 blanked summaries (`length < 30`).
- **`Freshness SLA`** flagged `is_fresh = False` because stale records reached **31.82%**, exceeding the 25% allowance threshold.

---

## 3. Idempotent Repair & Self-Healing Verification

- **Repair Mechanism:** The system executed `repair_from_raw_snapshot()`, reconstructing the clean dataset strictly from the immutable raw source snapshot (`data/raw/crossref_records.json`).
- **Determinism (Idempotence):** The repair step executed deterministically without requiring external API access or risking HTTP 429 rate limits.
- **Verification Evidence:**
  - Repaired Data Quality Gate: **PASS** (100% checks passed).
  - Repaired Freshness SLA: **PASS** (stale ratio returned to compliant levels).
  - Repaired Retrieval Hit Rate: **1.0000** (100% restored).
  - Repaired Mean Token F1: **1.0000** (100% restored).

---

## 4. Generated Artifacts

| State | Artifact | Path |
| :--- | :--- | :--- |
| **Baseline** | Metrics & Answers | `data/results/baseline_metrics.json`, `data/results/baseline_answers.json` |
| **Corrupted** | Corrupted Clean Data | `data/clean/papers_clean_corrupted.json`, `data/clean/papers_clean_corrupted.csv` |
| **Corrupted** | Corruption Audit Log | `data/results/corruption_log.json` |
| **Corrupted** | Quality & Metrics | `data/quality/corrupted_quality_report.json`, `data/results/corrupted_metrics.json` |
| **Repaired** | Repaired Clean Data | `data/clean/papers_clean_repaired.json`, `data/clean/papers_clean_repaired.csv` |
| **Repaired** | Quality & Metrics | `data/quality/repaired_quality_report.json`, `data/results/repaired_metrics.json` |
| **Comparison** | Final 3-State Report | `data/reports/corruption_report.md` |
