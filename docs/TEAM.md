# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Latentia`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-Latentia-DataPipelineDataObservability`

---

## 👥 Danh Sách Thành Viên

| STT | Họ và tên | MSSV | GitHub | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|---|
| 1 | Nguyễn Minh Tuấn | 2A202602420 | `minhtuann1102` | `nguyenminhtuan07082004@gmail.com` | **Techlead & Pipeline Integrator** (`core/`, `pipelines/`, `script/run_phase1.py`, `script/run_corruption_flow.py`) | [2A202602420_NguyenMinhTuan.md](../report/2A202602420_NguyenMinhTuan.md) |
| 2 | Nguyễn Minh Thắng | 2A202602706 | `nmthang2004-tn` | `nmthang2004@gmail.com` | **Data Foundation & Quality Gate** (`crossref.py`, `cleaning.py`, Great Expectations 1.x & Freshness SLA `quality.py`) | [2A202602706_NguyenMinhThang.md](../report/2A202602706_NguyenMinhThang.md) |
| 3 | Nguyễn Thị Vàng | 2A202602897 | `vanganh230` | `vanganh230@gmail.com` | **RAG, Vector Index & Benchmark** (`embeddings.py`, `index.py`, `testset.py`, `corruption.py`) | [2A202602897_NguyenThiVang.md](../report/2A202602897_NguyenThiVang.md) |

---

## 📋 Phân Công Chi Tiết & Báo Cáo Đóng Góp Cá Nhân

### 1. Nguyễn Minh Tuấn (MSSV: 2A202602420)
- **Vai trò:** Trưởng nhóm (Techlead) & Điều phối Pipeline.
- **Phạm vi sở hữu (Ownership):**
  - Khởi tạo môi trường, chuẩn hóa biến môi trường và cấu hình hệ thống tại `src/core/config.py`, `src/core/utils.py`.
  - Tích hợp và điều phối luồng end-to-end trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Quản trị Git repository, theo dõi Contributor Insights, điều phối live demo và nghiệm thu bài nộp LMS.
- **Điều học được / Đóng góp chính:**
  - Nắm vững kiến trúc Idempotent Data Pipeline, xử lý tính nhất quán đa trạng thái (Baseline vs Corrupted vs Repaired) trong hệ thống RAG phục vụ sản xuất.

---

### 2. Nguyễn Minh Thắng (MSSV: 2A202602706)
- **Vai trò:** Kỹ sư Dữ liệu (Data Foundation & Observability).
- **Phạm vi sở hữu (Ownership):**
  - Xây dựng module Ingestion `src/ingestion/crossref.py` hỗ trợ API Fetching và Offline Fallback snapshot.
  - Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Thiết lập Data Quality Gate bằng **Great Expectations 1.x** (ephemeral context với 4 expectations) và giám sát Freshness SLA trong `src/observability/quality.py`.
- **Điều học được / Đóng góp chính:**
  - Thành thạo Great Expectations 1.x Fluent API, kỹ thuật Data Lineage và bảo đảm tính toàn vẹn dữ liệu trước khi đẩy vào Vector Database.

---

### 3. Nguyễn Thị Vàng (MSSV: 2A202602897)
- **Vai trò:** Kỹ sư AI & Đánh giá Benchmark (RAG & Evaluation).
- **Phạm vi sở hữu (Ownership):**
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2` và nạp chỉ mục ChromaDB (`src/retrieval/embeddings.py`, `src/retrieval/index.py`).
  - Xây dựng bộ test benchmark 10 câu hỏi đa dạng qua 4 nhóm nghiệp vụ trong `src/evaluation/testset.py`.
  - Triển khai 6 kịch bản Synthetic Data Corruption trong `src/ingestion/corruption.py` để mô phỏng hiện tượng Silent Failure.
- **Điều học được / Đóng góp chính:**
  - Hiểu rõ tác động của dữ liệu bẩn tới vector representation và sự sụt giảm chất lượng câu trả lời RAG, cách đo lường Hit Rate và Token F1.
