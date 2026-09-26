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
| Baseline Orchestration | `src/pipelines/phase1.py` | Cleaned data, Chroma index, Testset | `baseline_metrics.json`, `phase1_report.md` | Đang hoàn thiện |
| Corruption & Repair Flow | `src/pipelines/corruption_flow.py` | Clean data, raw snapshot, corruption log | `corrupted_metrics.json`, `repaired_metrics.json` | Đang hoàn thiện |
| Git Coordination & Repo | `docs/TEAM.md`, repo config | Thông tin nhóm | Repo sẵn sàng, sync nhánh main | Đã hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Hỗ trợ tích hợp module Ingestion & Clean | Đặng Quang Hưng (`crossref.py`, `cleaning.py`) | Xác minh raw snapshot và schema clean 24 dòng |
| Điều phối Live Demo & Slide | Toàn nhóm | Chuẩn bị kịch bản demo 3-5 phút |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết lập hệ thống cấu hình | `src/core/config.py`, `src/core/utils.py` | Load settings chuẩn hóa, hỗ trợ multi-provider | Test load_settings() |
| Điều phối Phase 1 Baseline | `script/run_phase1.py` | Baseline pipeline hoàn chỉnh | `python script/run_phase1.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng pipeline tự động hóa end-to-end kết nối toàn bộ các mắt xích từ Ingestion, Cleaning, Vector Indexing, Observability Quality Gate đến Evaluation và Reporting.

### Cách triển khai
Orchestrate các bước theo thứ tự phụ thuộc chặt chẽ, kiểm soát exception, đảm bảo tính Idempotent khi chạy lại nhiều lần không sinh rác hoặc lỗi crash.

### Cách xác minh
```bash
python script/run_phase1.py
```

## 5. Quyết định kỹ thuật & Điều học được
Thiết kế kiến trúc pipeline dạng module hóa giúp phân tách trách nhiệm giữa các thành viên và dễ dàng mở rộng khi chuyển đổi môi trường hoặc thêm data source mới.

## 6. Cam kết của thành viên
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** Nguyễn Anh Tuấn  
**Ngày xác nhận:** 2026-09-26
