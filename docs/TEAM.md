# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** Team VN
- **Mã Nhóm / Lớp:** K4-L3B-DAY10
- **Tên Repository Nộp Bài:** K4-L3B-Day10-TeamVN-DataPipelineDataObservability

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
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
