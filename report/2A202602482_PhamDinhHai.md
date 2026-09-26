# Member Role Report — Day 10: Data Foundation & Quality Gates

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | **Phạm Đình Hải** |
| **MSSV** | **2A202602482** |
| **Khóa/Lớp** | K4 / L3B (Ca Sáng) |
| **Tên nhóm** | Team VN |
| **Vai trò chính** | **Data Foundation & Quality Engineer** |
| **Repository** | `https://github.com/haikunn11/K4-L3B-Day10-TeamVN-DataPipelineDataObservability` |
| **Ngày hoàn thành** | 2026-09-26 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu độc quyền

| Module / Deliverable | File / Hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| **Raw Ingestion & Lineage** | `src/ingestion/crossref.py`<br>- `parse_crossref_payload`<br>- `fetch_source_records`<br>- `load_raw_records` | Query, filter, max_results từ Settings; hoặc Crossref API payload | - `data/raw/crossref_response.json`<br>- `data/raw/crossref_records.json`<br>- List `PaperRecord` (24 bài báo) | **Hoàn thành** |
| **Data Cleaning & Modeling** | `src/ingestion/cleaning.py`<br>- `build_clean_dataframe` | Danh sách `PaperRecord` thô và timestamp `run_date` | - `data/clean/papers_clean.csv`<br>- `data/clean/papers_clean.json`<br>- DataFrame 24 dòng có `text_for_embedding` 5 phần và `age_days` | **Hoàn thành** |
| **Data Observability (GX 1.x)** | `src/observability/quality.py`<br>- `run_data_quality_checks` | DataFrame sạch / bẩn / phục hồi và Settings | - Ephemeral GX 1.x batch validation<br>- 4 Expectations thiết yếu<br>- `data/quality/*_quality_report.json` | **Hoàn thành** |
| **Freshness SLA Monitoring** | `src/observability/quality.py`<br>- `build_freshness_report` | Cleaned DataFrame và ngưỡng SLA (180 ngày) | - `data/quality/freshness_report.json`<br>- Tỷ lệ stale papers & cờ `is_fresh` | **Hoàn thành** |

### Việc hỗ trợ ngoài phạm vi chính
- Cung cấp schema dữ liệu sạch (`paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`, `text_for_embedding`) cho **Thành viên 2** để xây dựng bộ câu hỏi Benchmark Test Set 10 câu qua 4 nhóm nghiệp vụ.
- Cung cấp cơ chế nạp raw snapshot an toàn cho **Thành viên 3** để kích hoạt luồng **Idempotent Self-Healing / Repair Pipeline**.

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File / Artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| **Thu thập Raw Ingestion** | `src/ingestion/crossref.py`<br>`data/raw/crossref_records.json` | Tải và parse thành công 24 bản ghi nghiên cứu scholarly | Lệnh CP0 in ra đúng: `Tín hiệu hoàn thành: Đã tải 24 bài báo` |
| **Tiền xử lý & Làm sạch** | `src/ingestion/cleaning.py`<br>`data/clean/papers_clean.json` | Khử trùng lặp theo `paper_id`, loại bỏ JATS XML tags, tính `age_days` chuẩn UTC, tạo `text_for_embedding` 5 phần | Lệnh CP1 in ra đúng: `Tín hiệu hoàn thành: Clean thành công 24 dòng` |
| **Kiểm định GX 1.x** | `src/observability/quality.py`<br>`data/quality/baseline_quality_report.json` | Chốt kiểm soát Ephemeral Context của GX 1.x vượt qua 100% 4 Expectations thiết yếu trên dữ liệu baseline | Lệnh CP1 in ra đúng: `Tín hiệu hoàn thành: Quality check status = True` |
| **Giám sát Freshness SLA** | `src/observability/quality.py`<br>`data/quality/freshness_report.json` | Tỷ lệ bài báo quá hạn (`age_days > 180`) chỉ chiếm 4.17% (1/24), đạt chuẩn SLA (`is_fresh = True`) | Kiểm tra file `freshness_report.json` có `is_fresh: true, stale_ratio: 0.0417` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Dữ liệu thô phân tán và thiếu ổn định:** Dữ liệu từ Crossref API chứa nhiều thẻ XML học thuật (`<jats:p>`, `<jats:title>`), khoảng trắng bất thường và cấu trúc ngày tháng lồng nhau (`date-parts`). Nếu mạng mất kết nối hoặc dính HTTP 429 Too Many Requests thì pipeline sẽ sụp đổ.
2. **Nguy cơ Silent Failure trong RAG:** Nếu tài liệu bị null tiêu đề, rỗng tóm tắt hoặc bị nhân bản, vector index vẫn được tạo nhưng mô hình RAG sẽ trả lời sai hoàn toàn mà không có exception nào văng ra.
3. **Dữ liệu lỗi thời (Staleness):** Các bài báo quá cũ không phản ánh đúng tri thức mới nhất cần được cảnh báo qua Freshness SLA.

### Cách triển khai
- **Ingestion Fallback:** Hàm `fetch_source_records` ưu tiên gọi Crossref API; nếu thất bại hoặc cấu hình offline, hàm tự động fallback đọc snapshot cục bộ `data/raw/crossref_response.json` hoặc `crossref_records.json`, đảm bảo tính tái lập (Reproducibility) và Data Lineage 100%.
- **Cleaning & Embedding Modeling:** Hàm `build_clean_dataframe` dùng Regex loại bỏ toàn bộ tag XML, chuẩn hóa Unicode whitespace, tính toán số ngày tuổi `age_days = (run_date.astimezone(UTC).date() - published_date).days`, và cấu trúc hóa chuỗi `text_for_embedding` theo 5 phần:
  ```text
  Title: {title}
  Authors: {authors_joined}
  Published: {published}
  Categories: {categories_joined}
  Summary: {summary}
  ```
- **Great Expectations 1.x:** Khởi tạo `gx.get_context(mode="ephemeral")`, đăng ký pandas data source, dataframe asset và batch definition. Áp dụng 4 Expectation classes từ `great_expectations.expectations`:
  1. `ExpectTableRowCountToBeBetween(min_value=15, max_value=50)`
  2. `ExpectColumnValuesToNotBeNull` cho `paper_id`, `title`, `text_for_embedding`
  3. `ExpectColumnValuesToBeUnique` cho `paper_id`
  4. `ExpectColumnValueLengthsToBeBetween` cho `title` (>=8 chars) và `summary` (>=20 chars)

### Lệnh xác minh độc lập
```powershell
# 1. Kiểm chứng Ingestion:
$env:PYTHONPATH='src'; $env:PYTHONIOENCODING='utf-8'; python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"

# 2. Kiểm chứng Cleaning:
$env:PYTHONPATH='src'; $env:PYTHONIOENCODING='utf-8'; python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"

# 3. Kiểm chứng Data Quality Gate:
$env:PYTHONPATH='src'; $env:PYTHONIOENCODING='utf-8'; python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); status=res['success']; print(f'Tín hiệu hoàn thành: Quality check status = {status}')"
```

---

## 5. Một quyết định kỹ thuật quan trọng
- **Bối cảnh:** Sử dụng thư viện Great Expectations cho Data Observability trong môi trường production / testing nhẹ.
- **Các phương án cân nhắc:**
  1. *Phương án A:* Dùng cấu hình file `great_expectations.yml` truyền thống trên đĩa (GX cũ).
  2. *Phương án B:* Dùng cú pháp Ephemeral Context mới của **Great Expectations 1.x** (`mode="ephemeral"`).
- **Phương án đã chọn:** **Phương án B (GX 1.x Ephemeral Context)**.
- **Lý do:** Tránh việc sinh rác hàng chục file YAML cấu hình trong Git, không bị phụ thuộc vào đường dẫn thư mục cố định trên máy local, tốc độ thực thi tức thì trên bộ nhớ RAM và tuân thủ 100% tiêu chí chấm điểm nghiêm ngặt của Rubric (trừ 10 điểm nếu dùng cú pháp cũ).

---

## 6. Một lỗi hoặc blocker đã xử lý
- **Triệu chứng:** Khi tính toán cột `age_days`, xảy ra lỗi `TypeError: can't subtract offset-naive and offset-aware datetimes` do `run_date` có múi giờ UTC (`datetime.now(timezone.utc)`) trong khi ngày parse từ chuỗi `published` là naive datetime.
- **Nguyên nhân gốc:** Sự không đồng nhất giữa đối tượng datetime có tzinfo và naive datetime trong thư viện Python chuẩn.
- **Cách xử lý:** Chuẩn hóa toàn bộ ngày tháng về dạng `date` thuần túy theo UTC (`run_date.astimezone(UTC).date()` và `datetime.strptime(pub_str, "%Y-%m-%d").date()`), sau đó thực hiện phép trừ giữa hai đối tượng `date` để tính chính xác số ngày chênh lệch.
- **Cách xác minh sau khi sửa:** Chạy kiểm chứng hàm `build_clean_dataframe` với cả datetime có tzinfo và không có tzinfo đều chạy mượt mà, trả về kết quả 24 dòng sạch với `age_days` chuẩn xác.

---

## 7. Hiểu biết về luồng end-to-end
1. **Dữ liệu đi từ Crossref đến Vector Index:** Dữ liệu thô từ Crossref API được tải và snapshot thành JSON bảo toàn lineage -> module `cleaning.py` loại bỏ rác XML, ghép chuỗi văn bản giàu ngữ cảnh 5 phần `text_for_embedding` -> chuyển qua `sentence-transformers/all-MiniLM-L6-v2` để tính toán vector 384 chiều -> nạp vào ChromaDB Persistent Client.
2. **Quality Checks vs Freshness Monitoring:** Quality checks kiểm tra tính toàn vẹn của cấu trúc schema và dữ liệu (không null, duy nhất, độ dài, số dòng); Freshness monitoring giám sát khía cạnh thời gian (Data Staleness), đảm bảo mô hình không sử dụng tri thức đã lỗi thời quá hạn SLA (>180 ngày).
3. **Cơ chế Repair thành công:** Khi phát hiện vi phạm qua Quality Gate, hệ thống tự động loại bỏ collection bẩn, nạp lại từ snapshot thô tin cậy ban đầu `crossref_records.json`, tái tạo DataFrame sạch và index lại vào collection `papers-repaired`, đưa Quality Gate trở lại trạng thái `success=True`.

---

## 8. Cam kết của thành viên
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Đình Hải  
**MSSV:** 2A202602482  
**Ngày xác nhận:** 2026-09-26  
