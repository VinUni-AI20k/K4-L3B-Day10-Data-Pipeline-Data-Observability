# 📋 BẢNG PHÂN CÔNG CÔNG VIỆC NHÓM - DAY 10
## Data Pipeline & Data Observability for RAG

- **Tên Nhóm:** `Saphoaqua`
- **Mã Lớp:** `K4-L3B-Day10`
- **Leader:** Nguyễn Đức Đông
- **Thành viên:** Bùi Quốc Việt, Nguyễn Thị Lê Na, Lê Thị Duyên

---

## 👥 Phân Công Vai Trò & Công Việc Chi Tiết

| STT | Thành viên | Vai trò chính | Module phụ trách chính | Nhiệm vụ chi tiết | Lệnh / File kết quả phụ trách |
|:---:|---|---|---|---|---|
| 1 | **Nguyễn Đức Đông** *(Leader)* | **Pipeline Integrator & Leader** | `core/`, `script/`, `src/pipelines/` | - Thiết lập Git Teamwork, cấu hình `.env`, `core/config.py`<br>- Tích hợp toàn bộ luồng Phase 1 (`src/pipelines/phase1.py`) và Phase 2 (`src/pipelines/corruption_flow.py`) thành công.<br>- Điều phối làm việc, chạy script kiểm thử và kiểm tra Git Contributors. | `script/run_phase1.py`<br>`script/run_corruption_flow.py`<br>`core/config.py` |
| 2 | **Bùi Quốc Việt** | **Data Ingestion & Recovery Specialist** | `src/ingestion/` | - Phụ trách bóc tách dữ liệu Crossref API & fallback snapshot offline (`src/ingestion/crossref.py`).<br>- Chuẩn hóa DataFrame, tính `age_days` và `text_for_embedding` (`src/ingestion/cleaning.py`).<br>- Viết kịch bản tiêm 6 loại lỗi dữ liệu (`src/ingestion/corruption.py`) và luồng tự phục hồi (Idempotent Repair). | `src/ingestion/crossref.py`<br>`src/ingestion/cleaning.py`<br>`src/ingestion/corruption.py` |
| 3 | **Nguyễn Thị Lê Na** | **RAG & Vector Store Specialist** | `src/retrieval/` | - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`.<br>- Khởi tạo và nạp 3 không gian vector cô lập trên ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`).<br>- Thiết lập LLM Provider (Groq / Gemini / Mock) và hàm truy vấn RAG context. | `src/retrieval/index.py`<br>`src/retrieval/llm.py`<br>`data/chroma/` |
| 4 | **Lê Thị Duyên** | **Data Observability & Evaluation Specialist** | `src/observability/`<br>`src/evaluation/` | - Thiết lập Chốt kiểm soát chất lượng dữ liệu với **Great Expectations 1.x** (4 Expectations bắt buộc + Freshness SLA 180 ngày) tại `src/observability/quality.py`.<br>- Sinh tập benchmark test set 10 câu hỏi (`src/evaluation/testset.py`).<br>- Đo lường metrics (Hit Rate, Token F1) và xuất báo cáo so sánh 3 trạng thái. | `src/observability/quality.py`<br>`src/evaluation/testset.py`<br>`data/reports/corruption_report.md` |

---

## 🛠️ Hướng Dẫn Thực Hiện Chi Tiết Theo Cá Nhân (Không Mâu Thuẫn - Chạy Song Song)

### 1️⃣ **Nguyễn Đức Đông (Leader / Pipeline Integrator)**
- **Mục tiêu:** Đảm bảo hệ thống môi trường sẵn sàng và ghép nối toàn bộ đường ống dữ liệu.
- **Các bước thực hiện:**
  1. Đảm bảo file `.env` đã được cấu hình đủ `LLM_PROVIDER`, `LLM_MODEL`, `GROQ_API_KEY` / `GOOGLE_API_KEY`.
  2. Kiểm tra `core/config.py` để tất cả đường dẫn artifacts và tham số hệ thống chuẩn xác.
  3. Ghép nối các module từ 3 thành viên còn lại vào `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  4. Chạy script tổng `python script/run_phase1.py` và `python script/run_corruption_flow.py` để xuất báo cáo cuối cùng.

---

### 2️⃣ **Bùi Quốc Việt (Data Ingestion, Cleaning & Corruption)**
- **Mục tiêu:** Thu thập, làm sạch và tạo bộ tiêm lỗi dữ liệu.
- **Các bước thực hiện:**
  1. **Bước 2 (`src/ingestion/crossref.py`):** Hoàn thiện `parse_crossref_payload()`, `fetch_source_records()` và `load_raw_records()`.
     - *Kiểm tra:* `python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Đã tải {len(r)} bài báo')"`
  2. **Bước 3 (`src/ingestion/cleaning.py`):** Hoàn thiện `build_clean_dataframe()` (tính `age_days`, ghép `text_for_embedding`, khử trùng paper_id).
     - *Kiểm tra:* `python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Clean {len(df)} dòng')"`
  3. **Bước 7 (`src/ingestion/corruption.py`):** Triển khai 6 dạng tiêm lỗi (drop 20% bản ghi mới, rỗng summary, rác summary, cắt title, lùi ngày stale, duplicate rows).

---

### 3️⃣ **Nguyễn Thị Lê Na (Vector Database & RAG Retrieval)**
- **Mục tiêu:** Đánh chỉ mục vector trên ChromaDB và xây dựng bộ truy vấn RAG.
- **Các bước thực hiện:**
  1. Kiểm tra cấu hình `src/retrieval/llm.py` và đảm bảo hàm `build_llm()` khởi tạo đúng Provider (Groq / Gemini / OpenAI / Mock).
  2. **Tạo ChromaDB index (`src/retrieval/index.py`):** Viết logic khởi tạo collection, nạp vector embedding từ `all-MiniLM-L6-v2` cho các tài liệu.
  3. Tạo 3 collection cô lập trên ChromaDB: `papers-baseline`, `papers-corrupted`, `papers-repaired` để so sánh chất lượng truy vấn giữa 3 trạng thái.

---

### 4️⃣ **Lê Thị Duyên (Data Observability & Evaluation)**
- **Mục tiêu:** Xây dựng Data Quality Gate Great Expectations 1.x và tạo bộ đánh giá Benchmark.
- **Các bước thực hiện:**
  1. **Bước 4 (`src/observability/quality.py`):**
     - Dùng **GX 1.x Ephemeral Context**:
       ```python
       context = gx.get_context(mode="ephemeral")
       ```
     - Cấu hình 4 Expectations:
       - `ExpectTableRowCountToBeBetween` (5 đến 5000)
       - `ExpectColumnValuesToNotBeNull` (`paper_id`, `title`, `text_for_embedding`)
       - `ExpectColumnValuesToBeUnique` (`paper_id`)
       - `ExpectColumnValueLengthsToBeBetween` (`summary` min 30 chars)
     - Giám sát Freshness SLA: Cảnh báo `is_fresh = False` nếu bài báo có `age_days > 180` vượt quá 25%.
     - *Kiểm tra:* `python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print('Quality check status =', res['success'])"`
  2. **Bước 5 (`src/evaluation/testset.py`):** Hoàn thiện `build_test_set()` tạo 10 câu hỏi Ground Truth phủ 4 nhóm (`summary`, `authors`, `date`, `categories`) xuất ra `data/eval/test_set.json`.

---

## 🚀 Quy Trình Phối Hợp Git & Kiểm Thứ (Parallel Workflow)

1. Mỗi thành viên kéo code mới nhất từ branch `main` về máy local:
   ```bash
   git pull origin main
   ```
2. Mọi thành viên độc lập làm việc trên module thuộc vai trò của mình (File không đụng chạm nhau):
   - **Việt:** chỉ sửa file trong `src/ingestion/`
   - **Lê Na:** chỉ sửa file trong `src/retrieval/`
   - **Duyên:** chỉ sửa file trong `src/observability/` & `src/evaluation/`
   - **Đông:** điều phối `src/pipelines/`, `core/config.py` và `script/`
3. Sau khi chạy test cá nhân đạt kết quả (Pass Signal), commit và push lên repository:
   ```bash
   git add .
   git commit -m "feat(role): hoàn thành module <tên_module>"
   git push origin main
   ```
4. Leader (Nguyễn Đức Đông) chạy toàn tuyến End-to-End:
   ```bash
   python script/run_phase1.py
   python script/run_corruption_flow.py
   ```
