# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** Team VN
- **Mã Nhóm / Lớp:** K4-L3B-DAY10
- **Tên Repository Nộp Bài:** K4-L3B-Day10-TeamVN-DataPipelineDataObservability
- **Repository URL:** https://github.com/haikunn11/K4-L3B-Day10-TeamVN-DataPipelineDataObservability

---

## 1. Danh sách Thành viên & Vai trò

| STT | Họ và tên | MSSV | Email | Vai trò chính | File mã nguồn sở hữu độc quyền | Báo cáo cá nhân |
|---:|---|---|---|---|---|---|
| 1 | **Phạm Đình Hải** | **2A202602482** | phamhaicute9@gmail.com | Data Foundation & Quality Engineer | `src/ingestion/crossref.py`<br>`src/ingestion/cleaning.py`<br>`src/observability/quality.py` | [`report/2A202602482_PhamDinhHai.md`](../report/2A202602482_PhamDinhHai.md) |
| 2 | **Nguyễn Minh Ngọc** | **2A202602530** | nguyenminhngoc234it@gmail.com | Evaluation & Failure Injection Engineer | `src/evaluation/testset.py`<br>`src/ingestion/corruption.py` | [`report/individual_2A202602530_NguyenMinhNgoc.md`](../report/individual_2A202602530_NguyenMinhNgoc.md) |
| 3 | **Vũ Huy Đỗ** *(Lead)* | **2A202602555** | dovh25x@gmail.com | Pipeline Orchestrator & Integration Lead | `src/pipelines/phase1.py`<br>`src/pipelines/corruption_flow.py`<br>`src/observability/reporting.py` | [`report/2A202602555_VuHuyDo.md`](../report/2A202602555_VuHuyDo.md) |

---

## 2. Báo cáo đóng góp cá nhân

### 👤 Phạm Đình Hải - 2A202602482
- **Vai trò:** Data Foundation & Quality Engineer.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế Fallback offline trong `src/ingestion/crossref.py` (tải và phân tích 24 bài báo).
  - Tiền xử lý văn bản, loại bỏ XML/HTML tags, khử trùng lặp theo `paper_id`, tính toán cột `age_days` và chuẩn hóa 5 phần `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** (Ephemeral Context với 4 Expectations thiết yếu) và giám sát Freshness SLA trong `src/observability/quality.py`.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage), cấu hình Ephemeral Context GX 1.x và phát hiện sớm rủi ro Silent Failure trước khi dữ liệu đi vào Vector Index.
  - Chi tiết: [`report/2A202602482_PhamDinhHai.md`](../report/2A202602482_PhamDinhHai.md).

### 👤 Nguyễn Minh Ngọc — 2A202602530
- **Vai trò:** Evaluation & Failure Injection Engineer.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng bộ Benchmark Test Set gồm 10 câu hỏi chuẩn hóa bao phủ 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`) trong `src/evaluation/testset.py`, có ground truth và document IDs cố định.
  - Triển khai Data Corruption Suite mô phỏng đủ 6 dạng lỗi dữ liệu thực tế (drop latest, blank summary, inject noise, truncate title, stale date, duplicate rows) và ghi log kiểm toán trong `src/ingestion/corruption.py`.
  - Bổ sung `tests/test_member2.py` (15 kiểm thử đạt) và `script/verify_member2.py`.
- **Điều học được / Đóng góp chính:**
  - Thiết kế benchmark cố định để đánh giá khách quan xuyên suốt 3 trạng thái; kỹ thuật ghi log trước/sau để kiểm toán dữ liệu.
  - Chi tiết: [`report/individual_2A202602530_NguyenMinhNgoc.md`](../report/individual_2A202602530_NguyenMinhNgoc.md).

### 👤 Vũ Huy Đỗ — 2A202602555
- **Vai trò:** Trưởng nhóm / Pipeline Orchestrator & Integration Lead.
- **Công việc chi tiết đã hoàn thành:**
  - Lắp ráp và điều phối toàn bộ Baseline Pipeline Pha 1 trong `src/pipelines/phase1.py` qua entrypoint `script/run_phase1.py`.
  - Thiết kế và tích hợp chu trình mô phỏng suy giảm và tự phục hồi trong `src/pipelines/corruption_flow.py` qua entrypoint `script/run_corruption_flow.py`.
  - Hiện thực hóa cơ chế **Idempotent Self-Healing / Repair** khôi phục dữ liệu từ raw snapshot tin cậy (`crossref_records.json`), tái tạo clean dataset và vector store collection `papers-repaired`.
  - Xây dựng module tự động xuất báo cáo Markdown Pha 1 (`data/reports/phase1_report.md`) và Bảng đối chiếu định lượng 3 trạng thái (`data/reports/corruption_report.md`) trong `src/observability/reporting.py`.
  - Bổ sung bộ kiểm thử `tests/test_member3.py` kiểm định tính Idempotent và cấu trúc báo cáo.
  - Hoàn thiện tài liệu nhóm `docs/TEAM.md`, báo cáo nhóm `report/group_report.md`, báo cáo cá nhân `report/2A202602555_VuHuyDo.md` và điều hành Live Demo.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc về thiết kế kiến trúc Pipeline tự phục hồi (Self-Healing Data Architecture), nguyên lý bảo toàn Data Lineage và vai trò sống còn của Data Observability trong việc ngăn chặn hiện tượng Silent Failure ở các hệ thống AI/RAG trong thực tế.
  - Chi tiết: [`report/2A202602555_VuHuyDo.md`](../report/2A202602555_VuHuyDo.md).
