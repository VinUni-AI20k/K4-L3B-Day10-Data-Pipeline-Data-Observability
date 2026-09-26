# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `sunset`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3-DAY10-sunset-DataPipelineDataObservability`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Trần Công Thiện | 2A202602579 | trancongthien.ai@gmail.com | Trưởng nhóm / Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`) | `report/2A202602579_TranCongThien.md` |
| 2 | Phùng Gia Bảo | 2A202602386 | baophung0401@gmail.com | Data Foundation & Recovery (`crossref.py`, `cleaning.py`, raw data) | `report/2A202602386_PhungGiaBao.md` |
| 3 | Trần Thanh Thái | 2A202602454 | tranthai2309hg@gmail.com | RAG & Vector Index (`retrieval/index.py`, `embeddings.py`, ChromaDB) | `report/2A202602454_TranThanhThai.md` |
| 4 | Dương Hữu Đạt | 2A202602544 | duongdat6672@gmail.com | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, reporting) | `report/2A202602544_DuongHuuDat.md` |

*(Nếu nhóm có 3 hoặc 5-6 thành viên, xem bảng phân công chi tiết theo vai trò trong file `CHECKPOINTS.md`)*.

---

## # Cá nhân

### ## Trần Công Thiện - 2A202602579
- **Vai trò:** Trưởng nhóm & Điều phối Pipeline.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống `core/config.py` và đường dẫn artifacts `core/utils.py`.
  - Kết nối luồng thực thi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Kiểm tra tính nhất quán của các artifacts và theo dõi Contributor tracking trên GitHub nhánh `main`.
  - Hỗ trợ fix các lỗi dependencies và debug luồng RAGAS.

### ## Phùng Gia Bảo - 2A202602386
- **Vai trò:** Data Foundation & Recovery.
- **Công việc chi tiết đã hoàn thành:**
  - Triển khai `src/ingestion/crossref.py` để kéo và parse dữ liệu từ API.
  - Xây dựng luồng làm sạch dữ liệu `src/ingestion/cleaning.py`, xử lý format date để tính toán tuổi đời của record.
  - Quản lý logic corruption và sửa chữa dữ liệu `src/ingestion/corruption.py`.

### ## Trần Thanh Thái - 2A202602454
- **Vai trò:** RAG & Vector Index.
- **Công việc chi tiết đã hoàn thành:**
  - Viết module tạo embeddings text và kết nối với ChromaDB ở `src/retrieval/index.py`.
  - Triển khai RAG Retriever và định nghĩa Prompt Template cho Agent trong `src/retrieval/agent.py`.
  - Tích hợp framework LLM API của OpenAI/Gemini trong `src/retrieval/llm.py`.

### ## Dương Hữu Đạt - 2A202602544
- **Vai trò:** Observability & Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Khởi tạo Data Context bằng Great Expectations và định nghĩa Data Quality Gate trong `src/observability/quality.py`.
  - Xây dựng framework sinh câu hỏi đánh giá `src/evaluation/testset.py`.
  - Thiết kế các template xuất file Markdown (Baseline/Corruption Comparison) trong `src/observability/reporting.py`.
