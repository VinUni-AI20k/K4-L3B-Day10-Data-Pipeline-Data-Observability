# Phase 2 Corruption & Repair Report: Tri-State Evaluation Analysis

> **Generated At:** 2026-09-26 03:33:21 UTC  
> **Evaluation Mode:** Tri-State Benchmark (Baseline vs Corrupted vs Repaired)  
> **Pipeline Status:** SUCCESS (Self-Healing Idempotent Repair Verified)  

---

## 1. Executive Summary

This report delivers a rigorous quantitative and qualitative comparison of the RAG data pipeline across **three operational states**:
1. **Baseline**: Clean data, fully indexed and benchmarked.
2. **Corrupted**: Injected with 6 synthetic corruption scenarios (drop latest, blank summary, inject noise, truncate title, stale date, duplicate rows).
3. **Repaired**: Restored via idempotent recovery (`repair_from_raw_snapshot`) from the immutable raw snapshot.

---

## 2. Tri-State Performance Comparison Table

| Metric / Signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | 100.00% | 70.00% | 100.00% | -30.00% | 100.0% | Suy giảm mạnh do rơi rớt 20% bài mới nhất, phục hồi toàn diện |
| `mean_token_f1` | 1.0000 | 0.8000 | 1.0000 | -0.2000 | 100.0% | Nhiễu và rỗng summary làm rớt F1; phục hồi 100% sau repair |
| `judge_accuracy` | 100.00% | 80.00% | 100.00% | -20.00% | 100.0% | LLM Judge phát hiện câu trả lời suy giảm, khôi phục tối đa |
| `mean_judge_score` | 5.00 / 5.0 | 4.20 / 5.0 | 5.00 / 5.0 | -0.80 | 100.0% | Điểm số chất lượng câu trả lời lấy lại phong độ nguyên bản |
| `Quality Gate (GX 1.x)` | **PASSED** | **FAILED** | **PASSED** | Vi phạm 2 expectations | 100% | Bắt trúng lỗi trùng lặp và rỗng summary |
| `Freshness SLA` | **FRESH** | **STALE** | **FRESH** | 38.1% quá hạn | 100% | Báo động chính xác khi tỷ lệ quá hạn vượt ngưỡng 25% |
| `Total Records` | 24 | 21 | 24 | -3 dòng (sau drop + dup) | 100% | Số dòng và cấu trúc được tái lập hoàn hảo |

---

## 3. Data Observability & Quality Signals Detail

### Great Expectations 1.x Validation Results
- **Baseline Quality Status:** PASSED (6/6 Expectations met)
- **Corrupted Quality Status:** **FAILED** (Failed Expectations: `ExpectColumnValuesToBeUnique, ExpectColumnValueLengthsToBeBetween`)
  - `ExpectColumnValuesToBeUnique (paper_id)`: FAILED do kịch bản duplicate rows.
  - `ExpectColumnValueLengthsToBeBetween (summary, min=30)`: FAILED do kịch bản blank summary.
- **Repaired Quality Status:** **PASSED** (6/6 Expectations met sau khi phục hồi)

### Freshness SLA Monitoring
- **Threshold SLA:** Quá hạn nếu `age_days > 180` chiếm tỷ lệ > 25%.
- **Baseline:** Stale ratio = 4.2% -> **FRESH**
- **Corrupted:** Stale ratio = 38.1% (vượt ngưỡng 25%) -> **STALE** (Alert triggered!)
- **Repaired:** Stale ratio = 4.2% -> **FRESH** (SLA restored)

---

## 4. Causal Analysis & Silent Failure Evidence

1. **[Data Corruption] -> [Quality/Freshness Signals] -> [Agent Metric Degradation]:**
   - Tiêm kịch bản `drop_latest_records` (bỏ rơi 20% bài báo mới nhất) dẫn tới việc ChromaDB thiếu các văn bản mục tiêu của câu hỏi kiểm thử gần đây -> `retrieval_hit_rate` sụt giảm từ **100.00%** xuống **70.00%**.
   - Tiêm kịch bản `blank_summary` và `inject_noise` dẫn tới context truy xuất bị mất thông tin hoặc ngập rác -> `mean_token_f1` rơi từ **1.0000** xuống **0.8000**.
   - Hiện tượng **Silent Failure**: Nếu không có Great Expectations và Freshness SLA canh gác, hệ thống vẫn phản hồi nhưng đưa ra câu trả lời sai lệch hoặc kém chất lượng mà không có cảnh báo hệ thống. Nhờ có Quality Gate, hệ sinh thái Data Observability đã lập tức gắn cờ cảnh báo đỏ `FAILED` / `STALE`.

2. **[Idempotent Repair Action] -> [Quality Recovery] -> [Agent Metric Full Recovery]:**
   - Kích hoạt `repair_from_raw_snapshot()`: Trích xuất lại từ bản gốc `data/raw/crossref_records.json` (Lineage Anchor bất biến).
   - Tái thực thi quy trình làm sạch chuẩn, tính toán lại `age_days`, khử trùng lặp và sinh lại `text_for_embedding`.
   - Kết quả: Toàn bộ 6/6 Expectations của Great Expectations đều đạt chuẩn `PASSED`, Freshness SLA trở về mức `FRESH` (4.2%), và các chỉ số RAG Retrieval Hit Rate (100.00%) lẫn Token F1 (1.0000) phục hồi hoàn toàn **100%**.

---

## 5. Deliverables & Lineage Verification Checklist

- [x] `data/clean/papers_clean_corrupted.csv` & `.json` (Dữ liệu bị làm bẩn)
- [x] `data/embeddings/papers_embeddings_corrupted.json` (Vector embeddings bẩn)
- [x] `data/results/corruption_log.json` (Nhật ký 6 kịch bản tiêm lỗi)
- [x] `data/results/corrupted_metrics.json` & `corrupted_answers.json` (Chỉ số suy giảm)
- [x] `data/quality/corrupted_quality_report.json` (Báo cáo vi phạm GX)
- [x] `data/clean/papers_clean_repaired.csv` & `.json` (Dữ liệu phục hồi an toàn)
- [x] `data/embeddings/papers_embeddings_repaired.json` (Vector embeddings phục hồi)
- [x] `data/results/repaired_metrics.json` & `repaired_answers.json` (Chỉ số sau phục hồi)
- [x] `data/reports/corruption_report.md` (Báo cáo đối chiếu 3 trạng thái hoàn chỉnh)
