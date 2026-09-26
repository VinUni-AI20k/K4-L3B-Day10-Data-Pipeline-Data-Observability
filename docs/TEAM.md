# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Saphoaqua`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-Saphoaqua-DataPipelineDataObservability`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Nguyễn Đức Đông | | dong160805@gmail.com | Trưởng nhóm / Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`) | `report/NguyenDucDong.md` |
| 2 | Nguyễn Thị Lê Na | | | Data Foundation & Ingestion (`crossref.py`, `cleaning.py`, `corruption.py`) | `report/NguyenThiLeNa.md` |
| 3 | Bùi Quốc Việt | | | RAG & Vector Index (`retrieval/index.py`, `llm.py`, ChromaDB) | `report/BuiQuocViet.md` |
| 4 | Lê Thị Duyên | 2A202602411 | | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, reporting) | `report/2A202602411-duyen.md` |

---

## # Cá nhân

### ## Nguyễn Đức Đông
- **Vai trò:** Trưởng nhóm & Điều phối Pipeline.
- **Công việc chi tiết đã hoàn thành:**
  - Cấu hình hệ thống `core/config.py`, `.env`, thiết lập Git teamwork.
  - Tích hợp luồng thực thi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Kiểm tra tính nhất quán của các artifacts và theo dõi Contributor tracking trên GitHub.

### ## Nguyễn Thị Lê Na
- **Vai trò:** Phụ trách Ingestion, Làm sạch & Phục hồi dữ liệu.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế Fallback offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Tiêm lỗi dữ liệu (`src/ingestion/corruption.py`) và thực thi cơ chế Idempotent Repair.

### ## Bùi Quốc Việt
- **Vai trò:** Phụ trách RAG, Vector Database & Embedding.
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`.
  - Nạp và quản lý 3 collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
  - Xây dựng QA Agent truy vấn ngữ cảnh chính xác theo tài liệu.

### ## Lê Thị Duyên
- **Vai trò:** Phụ trách Data Observability & Benchmark Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** và giám sát Freshness SLA trong `src/observability/quality.py`.
  - Xây dựng bộ câu hỏi đánh giá chuẩn trong `src/evaluation/testset.py`.
  - Đo lường và xuất bảng đối chiếu 3 trạng thái vào `data/reports/corruption_report.md`.
