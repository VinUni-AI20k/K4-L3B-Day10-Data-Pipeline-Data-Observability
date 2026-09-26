# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo vai trò cá nhân: Nguyễn Minh Tuấn (Techlead & Pipeline Integrator).

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên          | Nguyễn Minh Tuấn           |
| MSSV               | 2A202602420                |
| Khóa/Lớp           | K4-L3B                     |
| Tên nhóm           | Latentia                   |
| Vai trò chính      | Techlead & Pipeline Integrator (`core/`, `pipelines/`, `script/`) |
| Repository         | https://github.com/minhtuann1102/K4-L3B-DAY10-Latentia-DataPipelineDataObservability |
| Ngày hoàn thành    | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| Pipeline Orchestration Phase 1 | `src/pipelines/phase1.py`, `script/run_phase1.py` | Cấu hình `Settings`, raw data | Clean artifacts, baseline ChromaDB, `baseline_metrics.json`, `phase1_report.md` | Đang hoàn thiện |
| Corruption & Repair Flow | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Clean data, raw snapshot | `corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` | Đang hoàn thiện |
| Core config & utilities | `src/core/config.py`, `src/core/utils.py` | Biến môi trường `.env` | Pydantic Settings instance, path helpers | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Quản lý Git & code integration | Toàn đội (Thắng, Vàng) | Đảm bảo code chạy end-to-end, branch `main` sạch sẽ, phân chia commit |
| Hỗ trợ debug Great Expectations 1.x | Nguyễn Minh Thắng (`quality.py`) | Chuẩn hóa cú pháp ephemeral context GX 1.x không bị lỗi deprecated |
