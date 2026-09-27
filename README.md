# K4-L3B-Day10 — Data Pipeline & Data Observability for RAG

**Cài đặt và mở web demo trên nhánh `khoi`: [Hướng dẫn từng bước siêu dễ hiểu](docs/README_khoi.md).** Tài liệu gồm cấu hình API key, xử lý lỗi và danh sách file/lệnh commit, push an toàn.

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

## Pipeline hiện tại

- `data/raw/` — Snapshot offline Crossref API (`crossref_response.json`)
- `src/` — Ingestion, cleaning, GX 1.x, MiniLM/Chroma, QA và quản lý lần chạy
- `script/` — Entrypoints: `run_phase1.py`, `run_corruption_flow.py`

## Chạy và kiểm chứng trên PowerShell

Trong bản clone mới, dùng Python 3.11–3.13. Có thể cài theo lock bằng `uv sync --locked`, hoặc tạo venv và cài project bằng `pip install -e .`. ChromaDB yêu cầu >=1.5.9 để đóng client trước khi đóng dấu hash/copy DB. Bộ test hồi quy dùng `unittest` có sẵn trong Python.

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
.venv/Scripts/python.exe -B script/run_phase1.py --run-id my_demo
.venv/Scripts/python.exe -B script/run_corruption_flow.py --run-id my_demo
.venv/Scripts/python.exe -B script/verify_run.py data/runs/my_demo --project-dir .
```

Hai entrypoint dùng mock provider cho so sánh offline, không cần API key. Mô hình `sentence-transformers/all-MiniLM-L6-v2` phải có trong cache; mặc định entrypoint bật chế độ Hugging Face offline. Trên máy mới cần tải model trước khi chạy offline. Trong môi trường có mạng, có thể tải cache bằng:

```powershell
.venv/Scripts/python.exe -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

Nếu máy đặt sẵn `HF_HUB_OFFLINE=1`, hãy bỏ biến đó trong phiên tải model. Giữ `RUN_RAGAS=0` cho quy trình mock được nghiệm thu. Entrypoint giới hạn mặc định các pool số học về 1 luồng, nhưng tôn trọng giá trị người chạy đã đặt.

`--run-id` mặc định là `default`. Có thể thay bằng `--output-dir <thư-mục-riêng>`; hai tùy chọn loại trừ nhau. Chạy baseline trước comparison với cùng lựa chọn.

## Bảo vệ dữ liệu và chạy lặp

- `data/raw/` được đọc và sao chép nguyên byte vào run; không refresh hoặc ghi đè raw gốc. Nếu chỉ có response snapshot, parsed records được tạo trong run riêng.
- Run nằm tại `data/runs/<run-id>/`. Manifest ghi hash raw, benchmark được cung cấp, cấu hình, phiên bản dependency, source và artifact.
- Baseline chạy **cleaning → quality/freshness → benchmark/index → evaluation/report**. Dữ liệu không đạt chỉ tạo diagnostic trong attempt của nó.
- Index xây collection mới có hậu tố riêng; chỉ publish manifest sau encode/add/count/query thành công. Collection tốt cũ được giữ lại. Không có garbage collection tự động.
- Lần chạy hoàn tất được dùng lại sau khi xác minh hash, không tạo thêm tài liệu hoặc ghi lại artifact.
- Lần thất bại giữ output ở `attempt-001`; chạy lại cùng input/source sẽ thử `attempt-002`. Đây là chạy lại toàn stage, không tiếp tục từ giữa một bước.
- Nếu raw, benchmark, source, dependency hoặc cấu hình đổi, hãy dùng run ID mới. Không chỉnh sửa manifest để bỏ qua kiểm tra.
- `.run.lock` ngăn hai writer cùng run. Nếu tiến trình bị kill và để lại lock, kiểm tra tiến trình trước khi xử lý; có thể dùng run ID mới ngay.

Ví dụ cấu trúc:

```text
data/runs/my_demo/
  run_manifest.json
  raw/                         # bản sao nguồn
  inputs/test_set.json          # benchmark đầu vào, nếu đã có
  baseline/attempt-001/         # clean, chroma, embeddings, eval, quality, results, reports
  comparison/attempt-001/       # corrupted + repaired, dùng cùng benchmark
```

Copy toàn bộ thư mục run khi bàn giao Chroma, gồm `chroma.sqlite3` và tất cả thư mục segment được manifest đóng dấu. Đường dẫn DB trong embedding manifest là tương đối với file manifest. `verify_run.py` đọc SQLite bằng `mode=ro&immutable=1`, đối chiếu inventory, document IDs, segment, metrics và report mà không mở client ghi DB.

## Diễn giải kết quả

Benchmark chính vẫn gồm 10 câu/4 loại và có DOI. QA trả lời từ metadata; DOI/tiêu đề định danh không có trong corpus sẽ từ chối thay vì lấy bài khác. Các challenge ngoài corpus được chấm riêng trong `*_challenges.json`.

`mean_token_f1` giữ định nghĩa token-set overlap. `mean_grounded_token_f1` bằng 0 nếu nguồn trả lời không thuộc DOI chuẩn. Metrics ghi rõ `answer_backend`, `judge_provider` và số lần heuristic fallback; điểm mock judge không phải bằng chứng chất lượng LLM online. Việc dùng DOI trong benchmark vẫn hạn chế kết luận về retrieval ngữ nghĩa.

## Bộ kết quả bàn giao đã chọn

Run dùng cho web demo: [`cp6_pipeline_20260927_04`](data/runs/cp6_pipeline_20260927_04/run_manifest.json).

- [Baseline report](data/runs/cp6_pipeline_20260927_04/baseline/attempt-001/reports/phase1_report.md)
- [Bảng ba trạng thái](data/runs/cp6_pipeline_20260927_04/comparison/attempt-001/reports/corruption_report.md)
- [Báo cáo sửa lỗi và nghiệm thu](docs/KHOI_FIX_AND_HANDOVER_2026-09-27.md)

Theo xác nhận của người dùng, tài liệu đóng góp nhóm đã hoàn thành trên `main`; hướng dẫn này chỉ bàn giao demo của nhánh `khoi`. Người nộp bài tự thực hiện phần trình bày/Q&A và nộp LMS.

## Checkpoint 6 — demo với LLM online

**Demo chính hiện là trang web:** có data flow, biểu đồ/bảng benchmark, so sánh dữ liệu và khung chat theo ba corpus.

```powershell
.venv/Scripts/python.exe -B demo/app.py
```

Mở **http://127.0.0.1:8765**. Hướng dẫn thao tác và trình bày: [demo/README.md](demo/README.md). Mọi file mới/output của web nằm trong `demo/`. Các lệnh CLI bên dưới được giữ để kiểm chứng và xem bằng chứng lịch sử.

[Kịch bản trình bày 3–5 phút và Q&A](docs/CP6_LIVE_DEMO_GUIDE.md). Theo xác nhận của người dùng, tài liệu đóng góp nhóm đã được xử lý trên `main` và không thuộc lượt demo này.

[Báo cáo nghiệm thu Gemini](docs/CP6_GEMINI_ACCEPTANCE_2026-09-27.md): 12 case online đã hoàn tất, trong đó case cuối được retry riêng; nguồn gốc hai lượt được lưu đầy đủ. [Bảng kết quả online](data/live_demos/cp6_gemini_20260927_02/online_report.md).

```powershell
.venv/Scripts/python.exe -B script/run_live_demo.py --demo-id cp6_live_next --run-id cp6_pipeline_20260927_04 --provider gemini --model gemini-3.5-flash-lite
```

Script đọc Gemini key từ `.env`, chạy hai entrypoint pipeline và gọi Gemini tool agent online cho bốn case trên ba trạng thái. Chọn demo ID mới cho mỗi lần gọi API; nếu source thay đổi, chọn run ID mới. Script hỗ trợ `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY` và không sửa `.env`. OpenRouter vẫn là tùy chọn qua `--provider openrouter`.

Benchmark offline 10 câu và bốn case online được ghi riêng. Các câu online có trace gọi tool, số lần gọi và kiểm tra theo context/raw; lỗi API không được chuyển thành mock. Chroma online sử dụng bản copy để giữ nguyên run đã đóng dấu.

Run `khoi_handover_20260927_01` và ZIP cũ là bằng chứng lịch sử của source trước CP6, không nằm trong gói push demo tối thiểu. Run `cp6_pipeline_20260927_04` dành cho source demo mới. Không dùng lại run ID cũ sau khi source thay đổi.
