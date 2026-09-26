# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo vai trò cá nhân: Nguyễn Thị Vàng (RAG, Vector Index & Benchmark Evaluation).

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên          | Nguyễn Thị Vàng            |
| MSSV               | 2A202602897                |
| Khóa/Lớp           | K4-L3B                     |
| Tên nhóm           | Latentia                   |
| Vai trò chính      | RAG, Vector Index & Benchmark (`embeddings.py`, `index.py`, `testset.py`, `corruption.py`) |
| Repository         | https://github.com/minhtuann1102/K4-L3B-DAY10-Latentia-DataPipelineDataObservability |
| Ngày hoàn thành    | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| Benchmark Testset Generation | `src/evaluation/testset.py` | Cleaned DataFrame | `data/eval/test_set.json` (10 questions, 4 categories) | Đang hoàn thiện |
| Vector Store Indexing | `src/retrieval/embeddings.py`, `src/retrieval/index.py` | `all-MiniLM-L6-v2`, DataFrame | ChromaDB collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`) | Đang hoàn thiện |
| Synthetic Data Corruption | `src/ingestion/corruption.py` | Cleaned DataFrame | Corrupted DataFrame (6 error types) & corruption metadata | Đang hoàn thiện |
