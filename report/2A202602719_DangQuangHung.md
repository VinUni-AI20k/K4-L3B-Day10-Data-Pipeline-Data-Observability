# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đặng Quang Hưng             |
| MSSV               | 2A202602719                     |
| Khóa/Lớp         | K4 - Lớp B              |
| Tên nhóm         | Enigma     |
| Vai trò chính    | Data Foundation, Cleaning & Idempotent Repair (`crossref.py`, `cleaning.py`, raw data) |
| Repository         | https://github.com/hungdq1306/K4-L3B-Day10-Enigma-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Raw Data Ingestion & Fallback | `src/ingestion/crossref.py`<br>• `parse_crossref_payload`<br>• `fetch_source_records`<br>• `load_raw_records` | Crossref REST API / Local snapshot `crossref_response.json` | `data/raw/crossref_records.json` (24 bài báo metadata) | Hoàn thành |
| Data Cleaning & Modeling | `src/ingestion/cleaning.py`<br>• `build_clean_dataframe` | `list[PaperRecord]`, `run_date` | `data/clean/papers_clean.csv`, `papers_clean.json` (24 dòng) | Hoàn thành |
| Data Contract & Helper Fields | `src/ingestion/cleaning.py` | Raw fields | `text_for_embedding` (cấu trúc 5 phần), `age_days`, `authors_joined`, `categories_joined` | Hoàn thành |
| Idempotent Repair Logic | `src/ingestion/crossref.py`, `cleaning.py` | Raw snapshot đáng tin cậy | Luồng khôi phục dữ liệu sạch cho `corruption_flow.py` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Thống nhất schema dữ liệu vector index | Nguyễn Hữu Thành (`retrieval/index.py`) | Đảm bảo các cột `text_for_embedding`, `paper_id`, `published`, `authors_joined` khớp 100% với Document contract của ChromaDB |
| Cung cấp trường `age_days` chuẩn hóa | Hà Thị Mỹ Linh (`observability/quality.py`) | Hỗ trợ tính toán SLA Freshness check (`age_days > 180`) chính xác theo run_date |
| Khởi tạo template báo cáo & team info | Cả nhóm (`docs/TEAM.md`, `report/`) | Cập nhật phân công và tạo 4 file báo cáo cá nhân |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Ingestion & Parse Crossref | `src/ingestion/crossref.py` | 24 records parsed chuẩn xác, lưu `crossref_records.json` | Chạy `fetch_source_records()` -> `Đã tải 24 bài báo` |
| Clean & Pre-embed Modeling | `src/ingestion/cleaning.py` | `papers_clean.csv` và `papers_clean.json` | Chạy `build_clean_dataframe()` -> `Clean thành công 24 dòng` |
| Chuẩn hóa `text_for_embedding` | `src/ingestion/cleaning.py` | Text 5 phần: Title, Authors, Published, Categories, Summary | Kiểm tra từng dòng trong DataFrame |

**Output cụ thể tạo ra:**
- File thô: `data/raw/crossref_records.json` chứa 24 đối tượng `PaperRecord` đầy đủ metadata DOI, Title, Abstract, Author, Subject, Published Date, URL.
- File sạch: `data/clean/papers_clean.csv` và `data/clean/papers_clean.json` với 24 dòng dữ liệu không trùng lặp, đã bóc tách JATS XML tags, chuẩn hóa khoảng trắng và tính toán trường `age_days` phục vụ Data Observability.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Dữ liệu metadata thô từ Crossref API thường chứa các thẻ XML tạp chất (`<jats:p>`, `<jats:title>`), khoảng trắng thừa, định dạng ngày tháng phân mảnh (`date-parts: [[2026, 5, 20]]`), tác giả phân tách dạng đối tượng lồng nhau (`given`, `family`).
2. Hiện tượng network flakiness hoặc `429 Too Many Requests` khi gọi API công cộng có thể làm gãy pipeline nếu không có cơ chế fallback đọc từ local snapshot `crossref_response.json`.
3. Cần tạo trường `text_for_embedding` có cấu trúc ngữ nghĩa giàu thông tin để mô hình embedding vector hóa tối ưu, phục vụ RAG retrieval chính xác.

### Cách triển khai
1. **Trong `crossref.py`**:
   - `parse_crossref_payload`: Duyệt qua `items`, bóc tách `DOI` làm `paper_id`, dùng regex `re.sub(r"<[^>]+>", " ", abstract)` để loại bỏ toàn bộ XML tags, nối họ tên tác giả `given + family`, chuẩn hóa ngày xuất bản thành chuẩn ISO `YYYY-MM-DD`.
   - `fetch_source_records`: Kiểm tra cờ `settings.refresh_source`. Khi gọi API, nếu gặp lỗi mạng hoặc status != 200, tự động fallback đọc từ local snapshot `settings.paths.raw_api_response`. Kết quả sau khi parse được serialize và lưu vào `settings.paths.raw_records_json` để đảm bảo Data Lineage.
   - `load_raw_records`: Hỗ trợ đọc cả dạng raw API response lẫn file JSON list records đã parse, ánh xạ trở lại thành `list[PaperRecord]`.
2. **Trong `cleaning.py`**:
   - `build_clean_dataframe`: Khử trùng lặp theo `paper_id` (`drop_duplicates(subset=['paper_id'], keep='first')`), lọc bỏ dòng rỗng, tính `age_days = (run_date.date() - pub_date).days`.
   - Sinh trường `text_for_embedding` theo cấu trúc 5 phần chuẩn:
     ```text
     Title: <title>
     Authors: <authors_joined>
     Published: <published>
     Categories: <categories_joined>
     Summary: <summary>
     ```

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `payload` từ Crossref API hoặc snapshot `data/raw/crossref_response.json` |
| Output                         | `list[PaperRecord]`, DataFrame 24 dòng lưu ra `papers_clean.csv/json` |
| Module phụ thuộc             | `core.config.Settings`, `core.utils` |
| Module sử dụng output        | `observability.quality` (chạy GX 1.x), `retrieval.index` (nạp ChromaDB), `evaluation.testset` |
| Điều kiện lỗi cần xử lý | Mất mạng, mã lỗi 429/503 từ Crossref, thẻ XML lồng nhau trong abstract, ngày tháng thiếu ngày/tháng |

### Cách xác minh

```bash
# 1. Kiểm tra môi trường
.venv\Scripts\python.exe -c "import chromadb, great_expectations, sentence_transformers; print('Môi trường sẵn sàng')"

# 2. Kiểm tra Ingestion raw records
.venv\Scripts\python.exe -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"

# 3. Kiểm tra Clean dataframe 24 dòng
.venv\Scripts\python.exe -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
```

- **Kết quả thực tế:**
  ```text
  Môi trường sẵn sàng
  Tín hiệu hoàn thành: Đã tải 24 bài báo
  Tín hiệu hoàn thành: Clean thành công 24 dòng
  ```
- **Artifact:** `data/raw/crossref_records.json`, `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương thức biểu diễn tài liệu trong cột `text_for_embedding` phục vụ mô hình embedding `all-MiniLM-L6-v2`.
- **Các phương án đã cân nhắc:**
  - *Phương án A:* Chỉ dùng trường `summary` (hoặc ghép `title + summary`).
  - *Phương án B:* Thiết kế cấu trúc 5 phần có gắn nhãn ngữ cảnh rõ ràng: `Title`, `Authors`, `Published`, `Categories`, `Summary`.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Mô hình embedding và retrieval khi tìm kiếm các câu hỏi về tác giả (Authors query), danh mục nghiên cứu (Categories query) hoặc ngày xuất bản (Date query) cần các từ khóa nhãn này để tối ưu hóa khoảng cách cosine tương đồng giữa query và chunk văn bản. Nếu chỉ để tóm tắt thuần túy, các câu hỏi về metadata sẽ bị trượt (Retrieval Miss).
- **Bằng chứng:** Trong bộ benchmark 10 câu hỏi của nhóm có 4 nhóm câu hỏi nghiệp vụ (`summary`, `authors`, `date`, `categories`). Cấu trúc 5 phần giúp Hit Rate đạt mức tối đa.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ModuleNotFoundError: No module named 'core'
  UnicodeEncodeError: 'charmap' codec can't encode characters in position 6-7: character maps to <undefined>
  ```
- **Lệnh hoặc bước tái hiện:** Chạy lệnh một dòng bằng `python -c` trên Windows PowerShell.
- **Nguyên nhân gốc:**
  1. Thư mục `src` chưa được liên kết vào virtual environment `.venv` ở chế độ editable (`pip install -e . --no-deps`).
  2. Windows PowerShell console mặc định sử dụng code page cp1252, khi in các chuỗi ký tự tiếng Việt có dấu (`Môi trường sẵn sàng`) bị crash bởi `charmap` codec.
- **Cách xử lý:**
  1. Cài đặt package nội bộ vào `.venv`: `.venv\Scripts\python.exe -m pip install -e . --no-deps`.
  2. Thiết lập biến môi trường `$env:PYTHONIOENCODING="utf-8"` trước khi thực thi script trên Windows.
- **Cách xác minh sau khi sửa:** Chạy lại cả 3 lệnh kiểm chứng thành công với exit code 0.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:** Dữ liệu thô từ Crossref API được tải về và lưu giữ nguyên vẹn tại `crossref_response.json` (bảo đảm Data Lineage). Sau đó qua `cleaning.py` để khử XML, chuẩn hóa schema, tính `age_days` và ghép `text_for_embedding`. Dữ liệu sạch được truyền vào `MiniLMEmbeddings` để sinh vector 384 chiều và lưu vào ChromaDB collection `papers-baseline`.
2. **Evaluation set và ground-truth document IDs:** Bộ test set 10 câu hỏi chứa câu hỏi, `ground_truth` và `gold_paper_id`. Khi chạy Retrieval, nếu `gold_paper_id` nằm trong top-k tài liệu trích xuất thì tính là Hit (`retrieval_hit_rate`). LLM sau đó sinh câu trả lời và so sánh độ trùng khớp token (`mean_token_f1`).
3. **Quality checks vs Freshness monitoring:** Quality checks (Great Expectations) kiểm định tính toàn vẹn của cấu trúc dữ liệu (số dòng, non-null, unique ID, độ dài chuỗi). Freshness SLA kiểm định tính cập nhật về mặt thời gian (`age_days > 180`). Một bảng dữ liệu có thể hoàn toàn sạch về schema nhưng vẫn vi phạm Freshness nếu bài báo quá cũ.
4. **Vì sao phải dùng cùng test set cho 3 trạng thái:** Để đảm bảo tính khách quan và nhất quán (Controlled Experiment). Nếu thay đổi câu hỏi giữa các pha, sự thay đổi của metric sẽ do câu hỏi chứ không phản ánh đúng tác động của dữ liệu bẩn và phục hồi.
5. **Repair được xem là thành công:** Khi pipeline khôi phục dữ liệu sạch từ bản lưu thô (`crossref_records.json`), chạy lại quality gate đạt `success = True`, và các chỉ số `retrieval_hit_rate`, `mean_token_f1` phục hồi về mức ngang bằng hoặc xấp xỉ baseline ban đầu.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |       0.4 |      1.0 | Dữ liệu bị tiêm lỗi khiến hit rate giảm mạnh do mất text và stale date, sau repair phục hồi hoàn toàn |
| `mean_token_f1`      |     0.82 |      0.35 |     0.82 | Khả năng trả lời đúng của Agent phụ thuộc trực tiếp vào context sạch |
| Quality checks         |   PASSED |    FAILED |   PASSED | GX 1.x bắt được vi phạm rỗng và trùng lặp |
| Freshness status       |    FRESH |     STALE |    FRESH | Cảnh báo quá hạn kích hoạt chính xác khi lùi ngày |

### Kết luận từ số liệu
1. Tiêm lỗi cắt ngắn tóm tắt và làm cũ ngày xuất bản lập tức làm gãy Quality Gate và kéo tụt Hit Rate của RAG.
2. Cơ chế Idempotent Repair tái tạo lại DataFrame từ raw snapshot nguyên bản, giúp đưa toàn bộ chỉ số về trạng thái hoàn hảo ban đầu mà không tạo ra bản ghi rác.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Data Lineage là phòng tuyến đầu tiên:** Luôn bảo tồn raw data nguyên bản trước bất kỳ thao tác biến đổi nào. Nếu không có raw snapshot, việc repair khi có lỗi là bất khả thi.
2. **Tính Idempotent trong Data Engineering:** Bất kỳ thao tác ingest hay clean nào khi chạy nhiều lần với cùng input đều phải cho ra cùng output, không được gây trùng lặp bản ghi.
3. **Data Quality quyết định AI Quality (Garbage In - Garbage Out):** Mô hình RAG dù thông minh đến đâu cũng sẽ trả lời sai (Silent Failure) nếu dữ liệu đầu vào bị ô nhiễm.

### Nếu có thêm thời gian
Xây dựng một module tự động kiểm tra checksum SHA-256 của các raw snapshot để phát hiện ngay sự thay đổi trái phép của tệp dữ liệu gốc trước khi đưa vào pipeline.

## 10. Cam kết của thành viên
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đặng Quang Hưng  
**Ngày xác nhận:** 2026-09-26
