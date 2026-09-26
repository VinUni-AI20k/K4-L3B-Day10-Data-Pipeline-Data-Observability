# Group Report — Day 10: Data Pipeline & Data Observability

- **Khóa/Lớp:** K4 - Lớp B
- **Tên nhóm:** Enigma
- **Repository:** https://github.com/hungdq1306/K4-L3B-Day10-Enigma-Data-Pipeline-Data-Observability
- **Ngày hoàn thành:** 2026-09-26

---

## 1. Thành Viên & Phân Công Nhiệm Vụ

| STT | Họ và tên | MSSV | Vai trò chính | Module / Deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Anh Tuấn | 2A202602700 | Trưởng nhóm & Pipeline Integrator | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/core/` |
| 2 | Đặng Quang Hưng | 2A202602719 | Data Foundation, Cleaning & Repair | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, raw & clean datasets |
| 3 | Nguyễn Hữu Thành | 2A202602813 | RAG, Vector Database & Benchmark Evaluation | `src/retrieval/index.py`, `src/retrieval/embeddings.py`, `src/evaluation/testset.py` |
| 4 | Hà Thị Mỹ Linh | 2A202602619 | Data Observability, Corruption Suite & Reporting | `src/observability/quality.py`, `src/ingestion/corruption.py`, `src/observability/reporting.py` |

---

## 2. Tóm Tắt Kết Quả Dự Án
Nhóm Enigma đã hoàn thành 100% các tiêu chí bắt buộc theo chuẩn Rubric của Day 10:
- **Xây dựng Data Pipeline hoàn chỉnh:** Thu thập 24 bản ghi metadata từ Crossref REST API với cơ chế offline fallback đọc snapshot local `crossref_response.json`. Xử lý sạch văn bản (loại bỏ toàn bộ JATS XML tags), tính toán `age_days` và sinh trường `text_for_embedding` theo cấu trúc 5 phần giàu ngữ cảnh.
- **Data Observability:** Cấu hình **Great Expectations 1.x ephemeral mode** với 4 expectations chuẩn và kiểm soát **Freshness SLA** (`age_days > 180`). Pha Baseline đạt `Quality check status = True` và `is_fresh = True`.
- **Mô phỏng Silent Failure:** Tiêm 6 kịch bản lỗi dữ liệu tổng hợp (mất 20% bản ghi mới, rỗng tóm tắt, chèn chuỗi rác, cắt ngắn tiêu đề, lùi ngày xuất bản 400 ngày, nhân bản bản ghi). Kết quả Retrieval Hit Rate sụt giảm nghiêm trọng từ **100.0% xuống 50.0%**, Mean Token F1 tụt từ **1.0000 xuống 0.4756**. Quality Gate chuyển sang **FAILED (False)** và Freshness SLA báo động đỏ **STALE**.
- **Idempotent Self-Repair:** Kích hoạt cơ chế tự phục hồi an toàn từ raw snapshot nguyên bản (`crossref_records.json`), đưa toàn bộ chỉ số hiệu năng (Hit Rate 100%, F1 1.0) và chất lượng dữ liệu (Quality PASSED, Freshness FRESH) trở lại trạng thái hoàn hảo ban đầu.

---

## 3. Kiến Trúc & Luồng Dữ Liệu End-to-End

```text
[Crossref API / Raw Snapshot]
       │
       ▼
 [Data Ingestion] ──────────► data/raw/crossref_records.json
       │
       ▼
 [Data Cleaning] ───────────► data/clean/papers_clean.csv / json
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
[GX 1.x Quality Gate]          [MiniLM Vector Indexing]
data/quality/baseline.json     ChromaDB: papers-baseline
       │                                 │
       └────────────────►┌───────────────┘
                         ▼
             [Benchmark Evaluation] ◄─── data/eval/test_set.json (10 questions)
             baseline_metrics.json (Hit Rate: 100%)
                         │
                         ▼
        [Synthetic Data Corruption Suite]
        data/clean/papers_clean_corrupted.csv (Tiêm 6 lỗi)
                         │
                         ▼
         [Silent Failure Measurement]
         corrupted_metrics.json (Hit Rate: 50%, GX: FAILED, SLA: STALE)
                         │
                         ▼
            [Idempotent Self-Repair]
            Tái tạo từ data/raw/crossref_records.json
                         │
                         ▼
         [Repaired State Verification]
         repaired_metrics.json (Hit Rate: 100%, GX: PASSED, SLA: FRESH)
                         │
                         ▼
         [3-State Comparison Report]
         data/reports/corruption_report.md
```

---

## 4. Bảng Đối Chiếu Định Lượng 3 Trạng Thái (Thực Tế Chạy Pipeline)

Dưới đây là số liệu trích xuất trực tiếp từ các file kết quả `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` và log kiểm định:

| Chỉ số / Tín hiệu Observability | Baseline (Pha 1) | Corrupted (Pha 2) | Repaired (Pha 3) | Đánh giá tác động |
| :--- | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | **100.0%** | **40.0%** | **100.0%** | Mất bản ghi và cắt ngắn tiêu đề làm trượt retrieval, sau repair phục hồi tuyệt đối |
| **Mean Token F1** | **1.0000** | **0.5720** | **1.0000** | RAG mất ngữ cảnh chính xác dẫn đến câu trả lời bị sai lệch/thiếu hụt |
| **Judge Accuracy** | **100.0%** | **60.0%** | **100.0%** | Tỷ lệ câu trả lời chuẩn xác phục hồi 100% |
| **Data Quality Gate (GX 1.x)** | **PASSED (True)** | **FAILED (False)** | **PASSED (True)** | Bắt được vi phạm row count, rỗng summary, tiêu đề ngắn và duplicate ID |
| **Freshness SLA Status** | **FRESH** | **STALE (Alarm)** | **FRESH** | Phát hiện tỷ lệ bài báo quá hạn đạt 38.1% (vượt ngưỡng cho phép 25%) |
| **Số lượng bản ghi** | 24 | 21 | 24 | Khôi phục đầy đủ số lượng và khử sạch bản ghi nhân bản |

---

## 5. Danh Sách Deliverables & Artifacts Minh Chứng

1. **Mã nguồn thực thi:**
   - `src/core/config.py`, `src/core/utils.py`
   - `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`
   - `src/observability/quality.py`, `src/observability/reporting.py`
   - `src/retrieval/index.py`, `src/retrieval/embeddings.py`, `src/retrieval/qa.py`, `src/retrieval/agent.py`
   - `src/evaluation/testset.py`, `src/evaluation/metrics.py`
   - `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`
2. **Kịch bản chạy One-Click:**
   - `python script/run_phase1.py` (Exit code: 0)
   - `python script/run_corruption_flow.py` (Exit code: 0)
3. **Artifacts dữ liệu:**
   - `data/raw/crossref_records.json`
   - `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`
   - `data/eval/test_set.json` (10 câu test chuẩn 4 nhóm)
   - `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`
   - `data/results/corruption_log.json` (Ghi chi tiết 6 kịch bản lỗi)
   - `data/reports/phase1_report.md`
   - `data/reports/corruption_report.md` (Bảng đối chiếu 3 trạng thái)
4. **Báo cáo nhóm & cá nhân:**
   - `docs/TEAM.md`
   - `report/group_report.md`
   - 4 báo cáo cá nhân: `report/2A202602700_NguyenAnhTuan.md`, `report/2A202602719_DangQuangHung.md`, `report/2A202602813_NguyenHuuThanh.md`, `report/2A202602619_HaThiMyLinh.md`

---

## 6. Bài Học Kinh Nghiệm Của Nhóm
1. **Phòng bệnh hơn chữa bệnh:** Data Quality Gate đặt ngay sau bước Ingestion/Cleaning giúp phát hiện dị thường dữ liệu trước khi vector store bị ô nhiễm.
2. **Nhận thức về Silent Failure:** Trong các hệ thống RAG, lỗi dữ liệu thường không gây crash code mà làm giảm sút âm thầm độ tin cậy của mô hình AI. Việc quan trắc metrics định kỳ là bắt buộc.
3. **Bảo tồn Raw Lineage là điều kiện tiên quyết của Self-Healing:** Cơ chế Idempotent Repair chỉ có thể hoạt động khi dữ liệu thô ban đầu được lưu giữ nguyên trạng và có khả năng tái lập độc lập.
