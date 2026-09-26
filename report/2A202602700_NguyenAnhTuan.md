# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Anh Tuấn             |
| MSSV               | 2A202602700                     |
| Khóa/Lớp         | K4 - Lớp B              |
| Tên nhóm         | Enigma     |
| Vai trò chính    | Trưởng nhóm & Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`) |
| Repository         | https://github.com/hungdq1306/K4-L3B-Day10-Enigma-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Baseline Orchestration | `src/pipelines/phase1.py` | Cleaned data, Chroma index, Testset | `baseline_metrics.json`, `phase1_report.md` | Hoàn thành |
| Corruption & Repair Flow | `src/pipelines/corruption_flow.py` | Clean data, raw snapshot, corruption suite | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` | Hoàn thành |
| Git Coordination & Repo | `docs/TEAM.md`, repo config | Thông tin nhóm | Repo sẵn sàng, sync nhánh main 100% | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Hỗ trợ tích hợp module Ingestion & Clean | Đặng Quang Hưng (`crossref.py`, `cleaning.py`) | Xác minh raw snapshot và schema clean 24 dòng |
| Điều phối Live Demo & Kịch bản bảo vệ | Toàn nhóm | Chuẩn bị kịch bản demo 3-5 phút trước lớp |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết lập hệ thống cấu hình | `src/core/config.py`, `src/core/utils.py` | Load settings chuẩn hóa, hỗ trợ multi-provider | Test `load_settings()` |
| Điều phối Phase 1 Baseline | `src/pipelines/phase1.py`, `script/run_phase1.py` | Baseline pipeline hoàn chỉnh | `python script/run_phase1.py` -> exit code 0 |
| Điều phối Corruption Flow | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Bảng đối chiếu 3 trạng thái | `python script/run_corruption_flow.py` -> exit code 0 |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng pipeline tự động hóa end-to-end kết nối toàn bộ các mắt xích từ Ingestion, Cleaning, Vector Indexing, Observability Quality Gate đến Evaluation và Reporting.

### Cách triển khai
Orchestrate các bước theo thứ tự phụ thuộc chặt chẽ, kiểm soát exception, đảm bảo tính Idempotent khi chạy lại nhiều lần không sinh rác hoặc lỗi crash.

### Cách xác minh
```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả thực tế:**
  - Baseline Hit Rate: 100.0%, F1: 1.0000, GX Quality: True, Freshness: True.
  - Corrupted Hit Rate: 40.0%, F1: 0.5720, GX Quality: False, Freshness: False.
  - Repaired Hit Rate: 100.0%, F1: 1.0000, GX Quality: True, Freshness: True.

## 5. Quyết định kỹ thuật & Điều học được
Thiết kế kiến trúc pipeline dạng module hóa giúp phân tách trách nhiệm giữa các thành viên và dễ dàng mở rộng khi chuyển đổi môi trường hoặc thêm data source mới.

## 6. Cam kết của thành viên
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** Nguyễn Anh Tuấn  
**Ngày xác nhận:** 2026-09-26
