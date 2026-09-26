# Báo Cáo Cá Nhân — Nguyễn Đức Đông

- **Họ và tên:** Nguyễn Đức Đông
- **MSSV:** 
- **Email:** dong160805@gmail.com
- **Vai trò trong nhóm:** Leader & Pipeline Integrator (`core/`, `script/`, `src/pipelines/`)

---

## 🛠️ Công Việc Đã Hoàn Thành Chi Tiết

1. **Khởi tạo & Cấu hình Hệ thống (Bước 0 & 1):**
   - Thiết lập Git Teamwork, phân công 4 vai trò không mâu thuẫn trong [PHAN_CONG_NHOM.md](file:///c:/Users/msi/Documents/Lap_VinUni/Lap10/K4-L3B-Day10-Saphoaqua-DataPipelineDataObservability/PHAN_CONG_NHOM.md).
   - Khởi tạo virtual environment `.venv` (Python 3.11.9) và cài đặt dependencies (`chromadb`, `great-expectations`, `sentence-transformers`, `ragas`, v.v.).
   - Cấu hình file `.env` tích hợp Groq LLM API (`LLM_PROVIDER=groq`, `LLM_MODEL=llama-3.3-70b-versatile`).
   - Cập nhật `src/core/config.py` và `src/retrieval/llm.py` hỗ trợ Groq provider.

2. **Xây dựng & Tích hợp Pipeline Phase 1 (`src/pipelines/phase1.py` & `script/run_phase1.py`):**
   - Tích hợp 6 module: Ingest ➔ Clean ➔ Vector Indexing ChromaDB ➔ Benchmark TestSet ➔ Baseline Evaluation ➔ Great Expectations Quality Gate.
   - Xuất file báo cáo [phase1_report.md](file:///c:/Users/msi/Documents/Lap_VinUni/Lap10/K4-L3B-Day10-Saphoaqua-DataPipelineDataObservability/data/reports/phase1_report.md) và kết quả [baseline_metrics.json](file:///c:/Users/msi/Documents/Lap_VinUni/Lap10/K4-L3B-Day10-Saphoaqua-DataPipelineDataObservability/data/results/baseline_metrics.json).

3. **Xây dựng Pipeline Corruption & Recovery Phase 2 (`src/pipelines/corruption_flow.py` & `script/run_corruption_flow.py`):**
   - Ghép nối luồng Data Corruption Suite ➔ Đo lường suy giảm ➔ Idempotent Repair từ snapshot thô ➔ Re-indexing & Re-evaluation.
   - Xuất bảng so sánh 3 trạng thái tại [corruption_report.md](file:///c:/Users/msi/Documents/Lap_VinUni/Lap10/K4-L3B-Day10-Saphoaqua-DataPipelineDataObservability/data/reports/corruption_report.md) (Baseline vs Corrupted vs Repaired).

---

## 💡 Bài Học & Đóng Góp Chính

- Hiểu rõ kiến trúc **Idempotent Data Pipeline** cho AI/RAG.
- Thiết lập thành công chốt kiểm soát chất lượng dữ liệu tự động với **Great Expectations 1.x** nhằm ngăn chặn hiện tượng Silent Failure.
- Chứng minh khả năng tự phục hồi dữ liệu từ preserved raw snapshots mà không cần phụ thuộc lại API ngoài.
