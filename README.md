# K4-L3B-Day10 — Data Pipeline & Data Observability for RAG

> **Hình thức:** Teamwork | **Thời lượng:** 240 phút  
> **Lịch học (Lớp B - Ca Sáng):** Thứ 7 (26/09/2026) 09:00 – 13:00  
> ⏰ **Hạn nộp LMS:** 23:59:59 cùng ngày

---

## 🧭 Đọc gì, theo thứ tự nào?

| # | Tài liệu | Mô tả |
|:---:|---|---|
| 1️⃣ | **Codelab trên VLearn LMS** | Hướng dẫn từng bước + nộp bài (mở trên trình duyệt) |
| 2️⃣ | [CHECKPOINTS.md](docs/CHECKPOINTS.md) | Phân bổ thời gian 240 phút & deliverables từng mốc |
| 3️⃣ | [RUBRIC.md](docs/RUBRIC.md) | Tiêu chí chấm điểm (100 chuẩn + 10 bonus) |
| 4️⃣ | [SUBMISSION.md](docs/SUBMISSION.md) | Nội quy, deadline, bảo mật & checklist nộp bài |
| 5️⃣ | [TEAM.md](docs/TEAM.md) | Điền thông tin nhóm & báo cáo cá nhân |

---

## Repo có sẵn gì? (Scaffolded Baseline)

- `data/raw/` — Snapshot offline Crossref API (`crossref_response.json`)
- `src/` — Khung pipeline thu thập, embedding MiniLM, đánh giá metrics (có `TODO(student)`)
- `script/` — Entrypoints: `run_phase1.py`, `run_corruption_flow.py`

## Thiết lập môi trường

Yêu cầu Python 3.11–3.13. Chọn một trong hai cách cài đặt:

```bash
uv sync
```

hoặc:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

Trên macOS/Linux, dùng `source .venv/bin/activate` thay cho lệnh kích hoạt ở trên.

Tạo file cấu hình cục bộ từ `.env.example`:

```bash
copy .env.example .env
```

Trên macOS/Linux, dùng `cp .env.example .env`. Không commit `.env` hoặc API key. Baseline vẫn có thể đánh giá bằng heuristic fallback khi LLM provider chưa có credentials; muốn demo Agent với provider thật thì phải cấu hình key tương ứng.

Các provider hỗ trợ: `gemini`/`google`, `openai`, `anthropic`, `openrouter`, `ollama`, `custom`, `mock`.

## Chạy Checkpoint 0–3

Chạy baseline từ thư mục gốc của repository:

```bash
python script/run_phase1.py
```

Để tải lại nguồn Crossref hoặc tạo lại evaluation set, đặt biến môi trường tương ứng trước khi chạy:

```text
REFRESH_SOURCE=true
REFRESH_TEST_SET=true
```

Mặc định pipeline ưu tiên snapshot `data/raw/crossref_records.json`, sau đó tạo clean CSV/JSON, quality và freshness reports, ChromaDB collection `papers-baseline`, evaluation set, metrics, demo answers và `data/reports/phase1_report.md`.

Pipeline dừng trước bước indexing nếu baseline không vượt qua Quality Gate. Cảnh báo freshness được giữ nguyên trong báo cáo và không sửa dữ liệu để ép trạng thái đạt.

## Học viên cần làm gì?

1. Hoàn thiện **Data Quality Gate** (Great Expectations 1.x) trong `src/observability/quality.py`
2. Tích hợp **Freshness Check** (`age_days`) vào Quality Gate
3. Chạy **Baseline → Corruption → Repair** → xuất bảng đối chiếu 3 trạng thái
4. **Live Demo** trên bảng & nộp link repo lên VLearn LMS
