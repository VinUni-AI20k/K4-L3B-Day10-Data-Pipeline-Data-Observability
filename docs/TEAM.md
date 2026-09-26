# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm
### 🎯 CẤU HÌNH NHÓM 3 THÀNH VIÊN — PHÂN CHIA CÂN BẰNG 1:1:1

- **Tên Nhóm:** `[Điền tên nhóm]`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-[TenNhom]-DataPipelineDataObservability`

---

## 👥 Danh Sách Thành Viên & Package Sở Hữu

| STT | Họ và tên | MSSV | Email | Vai trò & Package sở hữu | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | [Họ tên TV1] | [MSSV1] | [Email1] | **Data Ingestion & Corruption Owner** (`src/ingestion/`: `crossref.py`, `cleaning.py`, `corruption.py`, Repair) | `report/<MSSV1>_HoTen.md` |
| 2 | [Họ tên TV2] | [MSSV2] | [Email2] | **Observability, Eval & Reporting Owner** (`src/observability/` & `src/evaluation/`: `quality.py` GX 1.x, `testset.py`, `reporting.py`) | `report/<MSSV2>_HoTen.md` |
| 3 | [Họ tên TV3] | [MSSV3] | [Email3] | **RAG, Vector DB & Orchestration Owner** (`src/retrieval/`, `src/pipelines/`: `index.py`, `phase1.py`, `corruption_flow.py`, Live Demo) | `report/<MSSV3>_HoTen.md` |

---

## 📝 Bản Tự Khai Đóng Góp Chi Tiết Từng Thành Viên

### 👤 Thành viên 1: [Họ tên TV1] - [MSSV1]
- **Vai trò:** Data Ingestion & Data Corruption Owner (Tầng Dữ Liệu).
- **Package & Mã nguồn sở hữu trực tiếp:** `src/ingestion/` (`crossref.py`, `cleaning.py`, `corruption.py`).
- **Công việc chi tiết đã hoàn thành:**
  - **CP0:** Hoàn thành module `crossref.py`, xây dựng cơ chế Offline Fallback an toàn, tải và bảo tồn 24 bài báo gốc vào `data/raw/crossref_records.json`.
  - **CP1:** Hoàn thành module `cleaning.py`, loại bỏ thẻ XML JATS (`<jats:p>`), tính toán `age_days`, khử trùng lặp và tạo trường `text_for_embedding` chuẩn 5 phần.
  - **CP4:** Lập trình trọn vẹn 6 kịch bản tiêm lỗi dữ liệu trong `corruption.py` (Drop 20%, blank summary, inject noise, truncate title, stale date, duplicate rows) và ghi nhận `corruption_log.json`.
  - **CP5:** Chịu trách nhiệm logic Idempotent Repair khôi phục dữ liệu sạch đồng nhất từ snapshot gốc.
  - **CP6:** Trình bày phần Ingestion, giải thích 6 dạng lỗi tiêm vào và cơ chế Idempotent Repair trong buổi Live Demo.
- **Điều học được / Đóng góp chính:**
  - Nắm vững kỹ thuật bảo toàn nguồn gốc dữ liệu (Data Lineage), cấu trúc hóa dữ liệu văn bản phục vụ mô hình Embedding và thiết kế cơ chế tự phục hồi Idempotent.

---

### 👤 Thành viên 2: [Họ tên TV2] - [MSSV2]
- **Vai trò:** Observability, Evaluation & Reporting Owner (Tầng Chốt Kiểm Dịch & Đo Lường).
- **Package & Mã nguồn sở hữu trực tiếp:** `src/observability/` (`quality.py`, `reporting.py`) & `src/evaluation/` (`testset.py`).
- **Công việc chi tiết đã hoàn thành:**
  - **CP1:** Xây dựng Data Quality Gate theo chuẩn mới **Great Expectations 1.x (Ephemeral Mode)** trong `quality.py` với 4 Expectations thiết yếu và giám sát vi phạm Freshness SLA (`age_days > 180`).
  - **CP2:** Xây dựng module `testset.py`, tự động sinh 10 câu hỏi benchmark kèm ground-truth bao phủ 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`).
  - **CP3:** Hoàn thiện `reporting.py` tự động xuất báo cáo Markdown `data/reports/phase1_report.md`.
  - **CP4:** Kiểm thử Quality Gate trên dữ liệu bẩn, xác nhận hệ thống kích hoạt cảnh báo vi phạm đỏ (`success = False`).
  - **CP5:** Lập trình hàm sinh báo cáo đối chiếu định lượng `corruption_report.md` với bảng so sánh chi tiết 3 trạng thái: Baseline vs Corrupted vs Repaired.
  - **CP6:** Thuyết trình cơ chế GX 1.x Ephemeral context, Freshness SLA và phân tích bảng số liệu định lượng trong buổi Live Demo.
- **Điều học được / Đóng góp chính:**
  - Làm chủ công cụ Great Expectations 1.x, hiểu sâu cách thiết lập SLA kiểm dịch chặn đứng hiện tượng Silent Failure trước khi dữ liệu đi vào serving layer.

---

### 👤 Thành viên 3: [Họ tên TV3] - [MSSV3]
- **Vai trò:** RAG, Vector Database & Orchestration Owner (Tầng AI & Tích Hợp Hệ Thống).
- **Package & Mã nguồn sở hữu trực tiếp:** `src/retrieval/` (`index.py`), `src/pipelines/` (`phase1.py`, `corruption_flow.py`) và `script/`.
- **Công việc chi tiết đã hoàn thành:**
  - **CP0:** Quản lý kho lưu trữ Git, cấu hình bảo mật `.gitignore` chặn rò rỉ `.env`, thiết lập môi trường và cấu hình `core/config.py`.
  - **CP2:** Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2` và ChromaDB collections trong `retrieval/index.py`, index 24 docs vào collection `papers-baseline`.
  - **CP3:** Ghép nối chu trình sạch trong `phase1.py` và chạy script `python script/run_phase1.py` exit code 0, thu thập `baseline_metrics.json`.
  - **CP4:** Nạp dữ liệu bị tiêm lỗi vào collection `papers-corrupted`, đo lường sự suy giảm chất lượng retrieval và QA của AI (`corrupted_metrics.json`).
  - **CP5:** Ghép nối luồng phục hồi trong `corruption_flow.py` và chạy script `python script/run_corruption_flow.py` exit code 0, thu thập `repaired_metrics.json`.
  - **CP6:** Trưởng nhóm dẫn dắt kịch bản Live Demo (3-5 phút), trực tiếp thao tác terminal và giải thích hiện tượng Silent Failure của RAG Agent.
- **Điều học được / Đóng góp chính:**
  - Làm chủ kỹ thuật cô lập Vector Store Collections trong ChromaDB, tích hợp End-to-End Pipeline và chứng minh tác động trực tiếp của Data Observability tới hiệu năng mô hình AI.
