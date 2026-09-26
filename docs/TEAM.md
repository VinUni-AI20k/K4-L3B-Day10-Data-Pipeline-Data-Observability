# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `[Điền tên nhóm]`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3-DAY10-TenNhom-DataPipeline`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Trần Cao Quốc Dinh | 2A202602939 | tdinh7735@gmail.com | Source & Environment Owner (`src/ingestion/crossref.py`, setup môi trường & `.env`) | `report/2A202602939_TranCaoQuocDinh.md` |
| 2 | | | | Data Model & Evaluation-Set Owner (`src/ingestion/cleaning.py`, `src/evaluation/testset.py`) | `report/<MSSV2>_HoTen.md` |
| 3 | | | | Observability Owner (`src/observability/quality.py` GX 1.x, `src/observability/reporting.py`) | `report/<MSSV3>_HoTen.md` |
| 4 | | | | Corruption & Integration Owner (`src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`) | `report/<MSSV4>_HoTen.md` |

*(Nếu nhóm có 3 hoặc 5-6 thành viên, xem bảng phân công chi tiết theo vai trò trong file `CHECKPOINTS.md`)*.

---

## # Cá nhân

### ## Trần Cao Quốc Dinh - 2A202602939
- **Vai trò:** Source & Environment Owner.
- **Công việc chi tiết đã hoàn thành:**
  - Setup môi trường: tạo `.venv` qua `uv`, cấu hình `.env` (chọn đúng `LLM_PROVIDER=anthropic` khớp với API key đang dùng).
  - Triển khai `src/ingestion/crossref.py`: `parse_crossref_payload` (map DOI/title/abstract/authors/subject/dates từ payload Crossref sang `PaperRecord`, bỏ record thiếu field bắt buộc), `fetch_source_records` (gọi Crossref API kèm retry cho `429/503`, fallback đọc snapshot offline `data/raw/crossref_response.json` khi mất mạng), `load_raw_records` (đọc lại raw snapshot phục vụ bước Repair).
- **Trạng thái:** Code đã viết và compile được (`py_compile` pass). Đang chờ hoàn tất cài dependencies (`uv sync`) để chạy lệnh nghiệm thu CP0 thực tế và xác nhận kết quả tải 24 bài báo.
- **Điều học được / Đóng góp chính:**
  - Cơ chế fallback offline giữ pipeline hoạt động được khi mất mạng hoặc bị rate-limit từ nguồn API bên ngoài.
  - Luôn phải chạy đúng interpreter trong virtualenv (`.venv/bin/python`, không phải `python3` hệ thống) để tránh xung đột package đã cài sẵn ở môi trường khác trên máy.

### ## HoVaTen2-MSSV2
- **Vai trò:** Data Model & Evaluation-Set Owner.
- **Công việc chi tiết đã hoàn thành:**
  - Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Sinh bộ câu hỏi đánh giá 4 loại (`summary`, `authors`, `date`, `categories`) trong `src/evaluation/testset.py`.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage) và giữ schema nhất quán trước khi build embedding index.

### ## HoVaTen3-MSSV3
- **Vai trò:** Phụ trách RAG, Vector Database & Embedding.
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`.
  - Nạp và quản lý 3 collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
  - Xây dựng QA Agent truy vấn ngữ cảnh chính xác theo tài liệu.
- **Điều học được / Đóng góp chính:**
  - Cách cô lập các không gian vector để so sánh khách quan giữa dữ liệu sạch và dữ liệu bị lỗi.

### ## HoVaTen4-MSSV4
- **Vai trò:** Phụ trách Data Observability & Benchmark Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** và giám sát Freshness SLA trong `src/observability/quality.py`.
  - Xây dựng bộ câu hỏi đánh giá chuẩn trong `src/evaluation/testset.py`.
  - Đo lường và xuất bảng đối chiếu 3 trạng thái vào `data/reports/corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Cách thiết lập hệ thống cảnh báo sớm chặn đứng hiện tượng Silent Failure trước khi dữ liệu vào serving layer.
