# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Alone`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10` (Lớp B, ca sáng)
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-Alone--DataPipelineDataObservability`
- **Hình thức:** Nhóm 1 thành viên; toàn bộ checkpoint CP0–CP5 do một người thực hiện end-to-end.

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Đặng Quang Huy | 2A202602962 | huyvp567@gmail.com | Toàn bộ pipeline: ingestion, cleaning, GX 1.x + freshness, test set, ChromaDB/RAG, orchestration phase1 + corruption/repair, báo cáo | `report/2A202602962_DangQuangHuy.md` |

---

## # Cá nhân

### ## Đặng Quang Huy — 2A202602962

- **Vai trò:** Thành viên duy nhất — Pipeline Integrator, Data Foundation, RAG Index, Observability & Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Ingestion Crossref trong `src/ingestion/crossref.py`: parse payload, retry 429/503, fallback snapshot local, lưu `data/raw/crossref_response.json` và `data/raw/crossref_records.json` (24 bài).
  - Cleaning trong `src/ingestion/cleaning.py`: bỏ JATS tag, dedup `paper_id`, tính `age_days`, ghép `text_for_embedding` 5 phần, xuất `data/clean/papers_clean.csv` và `papers_clean.json`.
  - Quality gate Great Expectations 1.x và Freshness SLA trong `src/observability/quality.py`.
  - Test set 10 câu (summary/authors/date/categories) trong `src/evaluation/testset.py`.
  - Index 3 collection ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) bằng `all-MiniLM-L6-v2`.
  - Orchestration `script/run_phase1.py` và `script/run_corruption_flow.py`: baseline → 6 kịch bản corruption → repair từ raw → bảng đối chiếu 3 trạng thái.
- **Điều học được / Đóng góp chính:**
  - Pipeline idempotent phải giữ raw snapshot làm nguồn phục hồi, không “sửa tay” dữ liệu bẩn.
  - Data quality gate (GX + freshness) bắt được lỗi mà RAG vẫn trả lời — đó là silent failure.
  - So sánh baseline/corrupted/repaired chỉ có ý nghĩa khi giữ nguyên cùng evaluation set.
