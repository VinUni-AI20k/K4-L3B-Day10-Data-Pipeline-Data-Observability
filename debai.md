# ĐỀ BÀI LAB DAY 10 - DATA PIPELINE & DATA OBSERVABILITY (LỚP L3B)

## 📌 Tổng Quan Bài Lab
Chào mừng bạn đến với tài liệu hướng dẫn thực hành của bài lab **Day 10 - Data Pipeline & Data Observability**.

💡 **Mục tiêu:** Xây dựng đường ống dữ liệu (Data Pipeline) chuẩn mực cho AI: từ khâu gom dữ liệu thô, làm sạch, thiết lập chốt kiểm soát chất lượng (Data Observability Gate) với Great Expectations 1.x, cho tới việc chủ động tiêm lỗi dữ liệu (Data Corruption) để quan sát sự suy giảm hiệu năng của mô hình AI và kích hoạt cơ chế phục hồi tự động (Idempotent Recovery).

---

## 🚀 Các Bước Thực Hiện Chi Tiết

### Bước 0: Khởi Tạo Repo Nhóm & Thiết Lập Git Teamwork
- **0.1.** Trưởng nhóm Fork & đổi tên repo theo chuẩn: `K4-L3B-DAY10-<TenNhom>-DataPipelineDataObservability`
- **0.2.** Mời thành viên vào repo (Collaborators).
- **0.3.** Clone Repo về máy local.
- **0.4.** Cấu hình Git `user.name` và `user.email` trùng khớp với tài khoản GitHub cá nhân.

---

### Bước 1: Khởi Tạo Môi Trường & Cấu Hình
1. Mở terminal tại thư mục gốc dự án.
2. Kiểm tra phiên bản Python (Yêu cầu Python 3.11, 3.12 hoặc 3.13): `python --version`
3. Kích hoạt môi trường ảo: `.\.venv\Scripts\Activate.ps1`
4. Cài đặt toàn bộ gói thư viện: `python -m pip install -e .`
5. Tạo file `.env` từ `.env.example` và cấu hình API Key (`GROQ_API_KEY` / `GOOGLE_API_KEY`).
6. Kiểm tra kết nối 3 thư viện cốt lõi:
   ```bash
   python -c "import chromadb, great_expectations, sentence_transformers; print('Environment Ready!')"
   ```
   *Tín hiệu hoàn thành:* Console in ra `Environment Ready!`.

---

### Bước 2: Thu Thập Dữ Liệu & Cất Giữ Bản Gốc (`src/ingestion/crossref.py`)
- Thu thập metadata từ Crossref REST API công khai.
- Chuẩn hóa các trường: `paper_id` (DOI), `title`, `summary` (loại bỏ thẻ HTML/XML), `authors`, `categories`, `published`.
- Lưu 2 raw artifacts: `data/raw/crossref_response.json` và `data/raw/crossref_records.json`.
- Hỗ trợ cơ chế Offline Fallback khi mất mạng hoặc dính 429 Too Many Requests.
- **Kiểm tra:**
  ```bash
  python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
  ```
  *Tín hiệu hoàn thành:* Console in ra `Tín hiệu hoàn thành: Đã tải 24 bài báo`.

---

### Bước 3: Làm Sạch Dữ Liệu & Chuẩn Bị Văn Bản Tạo Vector (`src/ingestion/cleaning.py`)
- Chuẩn hóa khoảng trắng, định dạng ngày tháng.
- Tính `age_days = (run_date - published).days`.
- Ghép nối các trường thành `text_for_embedding` hoàn chỉnh.
- Khử trùng lặp bản ghi theo khóa duy nhất `paper_id`.
- **Kiểm tra:**
  ```bash
  python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
  ```
  *Tín hiệu hoàn thành:* Console in ra `Tín hiệu hoàn thành: Clean thành công 24 dòng`.

---

### Bước 4: Thiết Lập Chốt Kiểm Soát Dữ Liệu (Observability Gate) với Great Expectations 1.x (`src/observability/quality.py`)
- Sử dụng chuẩn **Ephemeral Context** trên Great Expectations 1.x:
  ```python
  context = gx.get_context(mode="ephemeral")
  ```
- **4 Expectation Bắt Buộc:**
  1. `ExpectTableRowCountToBeBetween` (5 đến 5000 dòng).
  2. `ExpectColumnValuesToNotBeNull` (`paper_id`, `title`, `text_for_embedding`).
  3. `ExpectColumnValuesToBeUnique` (`paper_id`).
  4. `ExpectColumnValueLengthsToBeBetween` (`summary` min 30 ký tự).
- **Giám Sát Độ Tươi Mới (Freshness Monitoring):** Cảnh báo `is_fresh = False` nếu tỷ lệ bài báo cũ (`age_days > 180`) vượt quá 25%.
- **Kiểm tra:**
  ```bash
  python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print('Tín hiệu hoàn thành: Quality check status =', res['success'])"
  ```
  *Tín hiệu hoàn thành:* Console in ra `Tín hiệu hoàn thành: Quality check status = True`.

---

### Bước 5: Tạo Bộ Đề Đánh Giá Chuẩn (Benchmark Test Set) (`src/evaluation/testset.py`)
- Tự động trích xuất 10 câu hỏi Ground Truth thuộc 4 nhóm (`summary`, `authors`, `date`, `categories`).
- Xuất file `data/eval/test_set.json`.
- **Kiểm tra:**
  ```bash
  python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
  ```
  *Tín hiệu hoàn thành:* Console in ra `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test`.

---

### Bước 6: Chạy Toàn Tuyến Dữ Liệu Sạch (Baseline Pipeline) (`script/run_phase1.py`)
- Xâu chuỗi 6 bước pipeline: Ingest ➔ Clean ➔ Index ChromaDB ➔ Sinh Testset ➔ Đánh giá Baseline RAG (Hit Rate & Token F1) ➔ Great Expectations Quality Gate và xuất báo cáo `data/reports/phase1_report.md`.
- **Thực thi:** `python script/run_phase1.py`

---

### Bước 7: Tiêm Lỗi Dữ Liệu Thực Nghiệm (Data Corruption Suite) (`src/ingestion/corruption.py`)
- Triển khai 6 kịch bản tiêm lỗi: Drop latest records, Blank summary, Inject noise, Truncate title, Stale date, Duplicate rows.
- Ghi log chi tiết vào `data/results/corruption_log.json`.
- **Kiểm tra:**
  ```bash
  python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Tín hiệu hoàn thành: Corrupted {len(c)} dòng')"
  ```

---

### Bước 8: Đo Lường Suy Giảm, Phục Hồi Dữ Liệu & Đối Chiếu 3 Trạng Thái (`script/run_corruption_flow.py`)
- Nạp dữ liệu bẩn ➔ Đo lường suy giảm RAG (Silent Failure) ➔ Kích hoạt Idempotent Repair ➔ Tái đánh giá hệ thống ➔ Xuất bảng đối chiếu 3 trạng thái tại `data/reports/corruption_report.md`.
- **Thực thi:** `python script/run_corruption_flow.py`
