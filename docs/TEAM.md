# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** Team VN
- **Mã Nhóm / Lớp:** K4-L3B-DAY10
- **Tên Repository Nộp Bài:** K4-L3B-Day10-TeamVN-DataPipelineDataObservability

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | | | | Trưởng nhóm / Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`) | `report/<MSSV1>_HoTen.md` |
| 2 | Nguyễn Minh Ngọc | 2A202602530 | | Evaluation & Failure Injection Engineer (`evaluation/testset.py`, `ingestion/corruption.py`; theo ảnh phân công nhóm) | [Báo cáo cá nhân](../report/2A202602530_NguyenMinhNgoc.md) |
| 3 | | | | RAG & Vector Index (`retrieval/index.py`, `embeddings.py`, ChromaDB) | `report/<MSSV3>_HoTen.md` |
| 4 | | | | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, reporting) | `report/<MSSV4>_HoTen.md` |

*(Nếu nhóm có 3 hoặc 5-6 thành viên, xem bảng phân công chi tiết theo vai trò trong file `CHECKPOINTS.md`)*.
| 1 | **Phạm Đình Hải** | **2A202602482** | | Data Foundation & Quality Engineer (`crossref.py`, `cleaning.py`, `quality.py`) | [`report/2A202602482_PhamDinhHai.md`](../report/2A202602482_PhamDinhHai.md) |
| 2 | `[Họ và tên TV2]` | `[MSSV2]` | | Evaluation & Failure Injection Engineer (`testset.py`, `corruption.py`) | `report/<MSSV2>_<HoTen2>.md` |
| 3 | `[Họ và tên TV3]` | `[MSSV3]` | | Trưởng nhóm / Pipeline Orchestrator (`phase1.py`, `corruption_flow.py`, `reporting.py`) | `report/<MSSV3>_<HoTen3>.md` |

---

## # Cá nhân

### ## Phạm Đình Hải - 2A202602482
- **Vai trò:** Data Foundation & Quality Engineer.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế Fallback offline trong `src/ingestion/crossref.py`.
  - Tiền xử lý văn bản, khử trùng lặp, tính toán cột `age_days` và chuẩn hóa 5 phần `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** (Ephemeral Context với 4 Expectations thiết yếu) và giám sát Freshness SLA trong `src/observability/quality.py`.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage), cấu hình Ephemeral Context GX 1.x và phát hiện sớm rủi ro Silent Failure trước khi dữ liệu đi vào Vector Index.

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
### ## HoVaTen2-MSSV2
- **Vai trò:** Evaluation & Failure Injection Engineer.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng bộ đề thi đánh giá RAG gồm 10 câu hỏi chuẩn hóa qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`) trong `src/evaluation/testset.py`.
  - Triển khai Data Corruption Suite mô phỏng đủ 6 dạng lỗi dữ liệu thực tế và xuất log chi tiết trong `src/ingestion/corruption.py`.
- **Điều học được / Đóng góp chính:**
  - Cách thiết kế bộ benchmark khách quan và kỹ thuật tiêm lỗi để kiểm thử độ bền của hệ thống RAG.

### ## HoVaTen3-MSSV3
- **Vai trò:** Trưởng nhóm & Điều phối Pipeline.
- **Công việc chi tiết đã hoàn thành:**
  - Kết nối luồng thực thi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Thực thi cơ chế Idempotent Repair tự động khôi phục dữ liệu từ raw snapshot tin cậy.
  - Lập báo cáo đối chiếu định lượng 3 trạng thái trong `src/observability/reporting.py`, hoàn thiện báo cáo nhóm và điều hành Live Demo.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc về thiết kế Idempotent Pipeline và kiến trúc tự phục hồi (Self-healing Data Observability).
