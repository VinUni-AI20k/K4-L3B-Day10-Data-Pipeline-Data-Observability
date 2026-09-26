# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo vai trò cá nhân: Nguyễn Minh Thắng (Data Foundation & Observability).

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên          | Nguyễn Minh Thắng          |
| MSSV               | 2A202602706                |
| Khóa/Lớp           | K4-L3B                     |
| Tên nhóm           | Latentia                   |
| Vai trò chính      | Data Foundation & Quality Gate (`crossref.py`, `cleaning.py`, `quality.py`) |
| Repository         | https://github.com/minhtuann1102/K4-L3B-DAY10-Latentia-DataPipelineDataObservability |
| Ngày hoàn thành    | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| Ingestion & Offline Fallback | `src/ingestion/crossref.py` | Crossref API / `data/raw/crossref_response.json` | `data/raw/crossref_records.json` (List[PaperRecord]) | Đang hoàn thiện |
| Data Cleaning & Pre-embedding | `src/ingestion/cleaning.py` | List[PaperRecord] | `papers_clean.csv`, `papers_clean.json` có `text_for_embedding` & `age_days` | Đang hoàn thiện |
| Data Observability (GX 1.x & Freshness) | `src/observability/quality.py` | Cleaned/Corrupted DataFrame | GX Expectation Suite validation result, Freshness SLA report | Đang hoàn thiện |
