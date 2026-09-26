# Baseline Phase 1 Pipeline & Data Observability Report

## 1. Data Ingestion Summary
- **Source API**: Crossref REST API
- **Query**: `agentic retrieval augmented generation large language model`
- **Total Records Ingested**: 24
- **Raw Snapshot**: `F:\hhh\K4-L3B-Day10-Data-Pipeline-Data-Observability\data\raw\crossref_records.json`

## 2. Data Observability & Quality Gates (Great Expectations 1.x)
- **Overall Quality Status**: **✅ PASSED**
- **Evaluated Expectations**: 6
- **Successful Expectations**: 6
- **Unsuccessful Expectations**: 0

### Key Expectations Applied:
1. `ExpectTableRowCountToBeBetween(5, 5000)`: Đảm bảo số lượng bản ghi tối thiểu.
2. `ExpectColumnValuesToNotBeNull`: Áp dụng trên `paper_id`, `title`, `text_for_embedding`.
3. `ExpectColumnValuesToBeUnique`: Đảm bảo không trùng lặp `paper_id`.
4. `ExpectColumnValueLengthsToBeBetween`: Đảm bảo độ dài `summary` $\ge 30$ ký tự.

## 3. Freshness SLA Monitoring
- **Freshness Status**: **✅ FRESH**
- **Threshold**: `180` ngày
- **Total Rows Evaluated**: 24
- **Stale Rows (Quá hạn)**: 1
- **Stale Ratio**: 4.17% (Ngưỡng cảnh báo: $\ge 25\%$)
- **Oldest Published Date**: `2026-03-28`
- **Latest Published Date**: `2026-07-22`

## 4. Baseline Evaluation & RAG Benchmarks
- **Evaluated Test Questions**: 10

| Metric | Score | Target / Note |
| :--- | :--- | :--- |
| **Retrieval Hit Rate** | `1.0000` (100.0%) | Tỷ lệ tìm thấy đúng bài báo trong top-K |
| **Mean Token F1** | `1.0000` | Độ trùng khớp từ vựng giữa câu trả lời và ground truth |
| **Judge Accuracy** | `1.0000` (100.0%) | Tỷ lệ câu trả lời được LLM Judge chấm đúng |
| **Mean Judge Score** | `5.00 / 5.0` | Điểm trung bình của LLM Judge |

## 5. Artifact Verification Checklist
- [x] `data/clean/papers_clean.csv` & `data/clean/papers_clean.json`
- [x] `data/chroma/` (Vector Store Indexed)
- [x] `data/eval/test_set.json`
- [x] `data/results/baseline_metrics.json` & `data/results/baseline_answers.json`
- [x] `data/quality/baseline_quality_report.json` & `data/quality/freshness_report.json`
- [x] `data/reports/phase1_report.md`