# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `[Điền tên nhóm]`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3-DAY10-TenNhom-DataPipeline`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | | | | Trưởng nhóm / Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`) | `report/<MSSV1>_HoTen.md` |
| 2 | Nguyễn Minh Ngọc | 2A202602530 | | Evaluation & Failure Injection Engineer (`evaluation/testset.py`, `ingestion/corruption.py`; theo ảnh phân công nhóm) | [Báo cáo cá nhân](../report/2A202602530_NguyenMinhNgoc.md) |
| 3 | | | | RAG & Vector Index (`retrieval/index.py`, `embeddings.py`, ChromaDB) | `report/<MSSV3>_HoTen.md` |
| 4 | | | | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, reporting) | `report/<MSSV4>_HoTen.md` |

*(Nếu nhóm có 3 hoặc 5-6 thành viên, xem bảng phân công chi tiết theo vai trò trong file `CHECKPOINTS.md`)*.

---

## # Cá nhân

### ## HoVaTen1-MSSV1
- **Vai trò:** Trưởng nhóm & Điều phối Pipeline.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống `core/config.py` và đường dẫn artifacts `core/utils.py`.
  - Kết nối luồng thực thi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Kiểm tra tính nhất quán của các artifacts và theo dõi Contributor tracking trên GitHub nhánh `main`.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc về thiết kế Idempotent Pipeline và quản lý trạng thái luồng dữ liệu đa tầng.

### ## Nguyễn Minh Ngọc — 2A202602530
- **Vai trò:** Evaluation & Failure Injection Engineer (theo ảnh phân công nhóm).
- **Công việc chi tiết đã hoàn thành:**
  - Tạo benchmark 10 câu thuộc 4 nhóm trong `src/evaluation/testset.py`, có ground truth và document IDs.
  - Triển khai đủ 6 kịch bản corruption trong `src/ingestion/corruption.py`, cập nhật trường dẫn xuất và ghi log trước/sau.
  - Bổ sung `tests/test_member2.py` (15 kiểm thử đạt) và `script/verify_member2.py` để tái hiện bằng chứng offline.
  - Sinh `data/eval/test_set.json`, `data/results/corruption_log.json`, `data/results/member2_validation.json` từ snapshot fixture; chưa đo RAG end-to-end.
- **Điều học được / Đóng góp chính:**
  - Benchmark cố định giúp so sánh công bằng giữa baseline, corrupted và repaired; log theo document ID giúp truy vết từng lỗi.
  - Chi tiết kết quả, giới hạn tích hợp và nội dung cần tự xác nhận: [báo cáo cá nhân](../report/2A202602530_NguyenMinhNgoc.md).

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
