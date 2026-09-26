# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | Bar |
| Repository | https://github.com/masao1112/K4-L3B-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đào Quang Thái Anh | 2A202602987 | Lead & Observability / Orchestration | `src/observability/quality.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/run_phase1.py`, `script/run_corruption_flow.py` |
| 2 | Dương Đức Vương | 2A202602944 | Data Engineering | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py` |
| 3 | Nguyễn Thành Tiến | 2A202603003 | Data Acquisition & Benchmarking | `src/evaluation/testset.py`, `src/ingestion/crossref.py` |

---

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành trọn vẹn luồng pipeline end-to-end cho bài toán Data Pipeline & Data Observability theo kiến trúc 6 bước chuẩn, bao gồm cả luồng tiêm lỗi tổng hợp (synthetic corruption testing) và phục hồi dữ liệu từ nguồn bất biến (idempotent repair):

1. **Baseline Pipeline**: Thu thập và nạp thành công 24 bản ghi nghiên cứu từ Crossref REST API; làm sạch, tính toán siêu dữ liệu thời gian (`age_days`) và sinh văn bản nhúng chuẩn hóa `text_for_embedding`; lưu trữ tại `data/clean/papers_clean.csv` và `data/clean/papers_clean.json`. Toàn bộ dữ liệu được index vào ChromaDB collection `papers-baseline` với mô hình nhúng API/Local. Bộ benchmark gồm 10 câu hỏi thuộc 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`) đạt tuyệt đối: **Retrieval Hit Rate 1.0000**, **Mean Token F1 1.0000**, **Judge Accuracy 1.0000** và **Mean Judge Score 5.00/5.00**. Hệ thống Great Expectations 1.x vượt qua 6/6 tiêu chuẩn chất lượng (PASS) và Freshness SLA đạt chuẩn (chỉ 1/24 bản ghi quá hạn 180 ngày, tỷ lệ 4.17% < 25%).
2. **Corruption Impact**: Quá trình tiêm 6 loại lỗi thực nghiệm (loại bỏ 20% bản ghi mới nhất, xóa rỗng tóm tắt, chèn nhiễu chuỗi, cắt ngắn tiêu đề, sửa lùi ngày phát hành thành 365 ngày trước và nhân bản bản ghi) đã kích hoạt cảnh báo nghiêm trọng tại Data Quality Gate (FAIL - vi phạm tính unique của `paper_id` và độ dài `summary` $\ge 30$ ký tự). Về phía RAG Agent, lỗi gây ra hiện tượng **Silent Failure** điển hình: không phát sinh exception lúc runtime nhưng hiệu năng suy giảm đột biến: Hit Rate tụt xuống **0.6000** (-40%), Token F1 tụt xuống **0.5817** (-41.83%), Judge Score tụt còn **3.20/5.00**.
3. **Repair & Recovery**: Cơ chế phục hồi được thiết kế theo nguyên lý idempotent data rebuild từ snapshot nguồn bất biến (`data/raw/crossref_records.json`), tái tạo clean dataset và đánh chỉ mục lại vào collection cô lập `papers-repaired`. Toàn bộ chất lượng dữ liệu và hiệu năng Agent được khôi phục 100% về mức baseline ban đầu (Hit Rate 1.0000, Token F1 1.0000, Quality Gate PASS 6/6).

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
+-------------------------------------------------------------------------------+
|                             Crossref REST API                                 |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Ingestion: data/raw/crossref_records.json (24 raw papers snapshot)           |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Cleaning & Modeling: data/clean/papers_clean.csv & .json                      |
| (Loại HTML tags, chuẩn hóa text_for_embedding, tính toán age_days)            |
+-------------------------------------------------------------------------------+
           |                                              |
           v                                              v
+-----------------------+              +----------------------------------------+
| Observability Gate    |              | Indexing (ChromaDB):                   |
| Great Expectations 1.x|              | collection "papers-baseline"           |
| & Freshness SLA Check |              | Vector embeddings (API / MiniLM)       |
+-----------------------+              +----------------------------------------+
           |                                              |
           \-----------------------\  /-------------------/
                                   v  v
+-------------------------------------------------------------------------------+
| Evaluation Benchmark (data/eval/test_set.json - 10 câu hỏi cố định)          |
| -> Baseline Metrics: Hit Rate = 1.0000 | Token F1 = 1.0000 | Score = 5.00     |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Synthetic Corruption Flow: data/clean/papers_clean_corrupted.csv & .json      |
| -> Observability Gate: Quality FAIL (Unique & Length violations)              |
| -> Vector Store: collection "papers-corrupted"                                |
| -> Re-Evaluation: Hit Rate = 0.6000 | Token F1 = 0.5817 | Score = 3.20         |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Idempotent Repair Flow: Rebuild từ data/raw/crossref_records.json             |
| -> Vector Store: collection "papers-repaired"                                 |
| -> Re-Evaluation & Observability: Phục hồi hoàn toàn (Hit Rate = 1.0000, PASS)|
+-------------------------------------------------------------------------------+
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| **Ingestion** | Crossref REST API query | Fetch dữ liệu qua HTTP client, xử lý exponential backoff retry khi gặp rate-limit/timeout, trích xuất metadata và lưu raw snapshot | `data/raw/crossref_records.json`, `data/raw/crossref_response.json` | Nguyễn Thành Tiến |
| **Cleaning** | `data/raw/crossref_records.json` | Parse authors, loại bỏ thẻ XML/HTML trong abstract, chuẩn hóa title, tính `age_days` theo UTC, sinh `text_for_embedding` chuẩn hóa | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Dương Đức Vương |
| **Embedding/Index** | Cleaned DataFrame | Khởi tạo vector client ChromaDB, nhúng ngữ nghĩa (embedding) và index tài liệu vào các collection độc lập (`papers-baseline`, `papers-corrupted`, `papers-repaired`) | `data/chroma/`, `data/embeddings/papers_embeddings*.json` | Đào Quang Thái Anh |
| **Evaluation** | `papers_clean.json`, ChromaDB Index | Thiết kế test suite 10 câu hỏi đa dạng nhóm nghiệp vụ, thực thi QA agent truy vấn top-4 chunks, tính Retrieval Hit Rate, Token F1 và LLM Judge Score | `data/eval/test_set.json`, `data/results/*_answers.json`, `data/results/*_metrics.json` | Nguyễn Thành Tiến |
| **Observability** | Clean/Corrupted/Repaired DataFrames | Khởi tạo Great Expectations 1.x Ephemeral context thực thi 6 data expectations; đo Freshness SLA theo ngưỡng 180 ngày và tỷ lệ stale | `data/quality/*_quality_report.json`, `data/quality/*_freshness_report.json` | Đào Quang Thái Anh |
| **Corruption/Repair** | `papers_clean.csv`, Raw snapshot | Tiêm 6 loại lỗi có chủ đích, ghi nhật ký `corruption_log.json`; xây dựng hàm `repair_from_raw_snapshot` tái tạo dữ liệu sạch bất biến | `data/clean/*_corrupted.*`, `data/clean/*_repaired.*`, `data/results/corruption_log.json` | Dương Đức Vương |
| **Orchestration** | Pipeline configuration & CLI | Xâu chuỗi 6 bước pipeline Pha 1 và luồng 5 bước Corruption -> Repair -> Comparison; điều phối báo cáo so sánh tự động | `script/run_phase1.py`, `script/run_corruption_flow.py`, `data/reports/*.md` | Đào Quang Thái Anh |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng | Ghi chú |
| --- | --- | --- |
| `LLM_PROVIDER` | `gemini` | Hỗ trợ fallback linh hoạt `openai`, `anthropic`, `mock` |
| `LLM_MODEL` | `gemini-2.5-flash` | Mô hình LLM sinh lời giải và LLM Judge |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | Fallback `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | `24` | Đạt tiêu chuẩn tối thiểu $\ge 20$ bài báo |
| Retrieval `top_k` | `4` | Số lượng văn bản context trích xuất cho mỗi câu hỏi |
| Freshness threshold | `180` ngày | Ngưỡng đánh giá độ trễ xuất bản của tài liệu |
| Ngưỡng vi phạm SLA Freshness | `25%` | Tỷ lệ bản ghi quá hạn tối đa cho phép trước khi báo STALE |
| Random seed | Cố định deterministic | Đảm bảo tính lặp lại (reproducibility) |

### Lệnh cài đặt

Nhóm sử dụng môi trường chuẩn với `pip` và file `pyproject.toml`:

```bash
python -m pip install -e .
```

Hoặc khi sử dụng trình quản lý gói `uv`:

```bash
uv sync
```

### Lệnh chạy

1. **Khởi chạy Baseline Pipeline (Pha 1)**:
```bash
python script/run_phase1.py
```
*(Nếu dùng uv: `uv run python script/run_phase1.py`)*

2. **Khởi chạy luồng Synthetic Corruption -> Repair -> Comparison**:
```bash
python script/run_corruption_flow.py
```
*(Nếu dùng uv: `uv run python script/run_corruption_flow.py`)*

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| `python script/run_phase1.py` | Thành công | 2026-09-26 | `data/reports/phase1_report.md`, `data/results/baseline_metrics.json` |
| `python script/run_corruption_flow.py` | Thành công | 2026-09-26 | `data/reports/corruption_report.md`, `data/results/corruption_log.json` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter | `query=agentic retrieval augmented generation large language model`, filter `from-pub-date:2026-03-30,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-26 |
| Số record nhận được | 24 records |
| Cơ chế retry/backoff | Thư viện `tenacity` với chiến lược exponential backoff (thử lại 3 lần, delay cơ sở 1.5s) khi gặp mã lỗi HTTP 429 hoặc 5xx |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | String | Có | Mã định danh duy nhất (DOI của bài báo) | Bắt buộc có từ trường `DOI` của Crossref; nếu thiếu bản ghi sẽ bị loại bỏ |
| `title` | String | Có | Tiêu đề chính thức của bài báo | Chuẩn hóa khoảng trắng; loại bỏ nếu rỗng |
| `summary` | String | Có | Tóm tắt nội dung (abstract) trích xuất | Loại bỏ thẻ `<jats:p>`, `<jats:sec>`, unescape HTML; yêu cầu tối thiểu 30 ký tự |
| `authors` | List[String] | Không | Danh sách tên tác giả định dạng `Given Family` | Ghép `given` và `family`; fallback thành `Unknown Author` nếu rỗng |
| `categories` | List[String] | Không | Phân loại nghiên cứu/chuyên ngành | Trích xuất từ `subject`; fallback danh mục mặc định `Artificial Intelligence` |
| `published` | String (ISO Date) | Có | Ngày phát hành định dạng `YYYY-MM-DD` | Parse từ `published-online` hoặc `published-print`; fallback ngày hiện tại |
| `abs_url` / `pdf_url` | String (URL) | Không | Đường link bài báo và liên kết tải PDF | Trích xuất từ `URL` hoặc DOI prefix |
| `age_days` | Integer | Có | Số ngày tính từ ngày xuất bản đến thời điểm chạy | `(run_date.date() - published_date).days` |
| `text_for_embedding` | String | Có | Văn bản hợp nhất phục vụ mô hình embedding | Định dạng trường hợp nhất chuẩn mực cấu trúc |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Loại bỏ các thẻ định dạng XML/HTML (`<jats:p>`, `<jats:title>`, `<jats:sec>`) trong abstract | **Validity & Cleanliness** | 24/24 | Regex làm sạch chuỗi, đối chiếu text trong `papers_clean.json` |
| Chuẩn hóa định dạng tác giả thành `Given Name Family Name` | **Consistency** | 24/24 | Kiểm tra trường `authors_joined` không chứa ký tự lạ |
| Loại bỏ khoảng trắng thừa, ký tự xuống dòng liên tiếp | **Conformity** | 24/24 | String strip & regex replace `\s+` |
| Tính toán `age_days` từ ngày xuất bản thực tế đến ngày chạy pipeline | **Currency & Freshness** | 24/24 | So sánh với `published`, xác thực `age_days >= 0` |
| Sinh chuỗi tài liệu `text_for_embedding` chuẩn hóa có tiền tố phân đoạn | **Completeness** | 24/24 | Kiểm định qua Great Expectations `ExpectColumnValuesToNotBeNull` |

**Cách thức tạo `text_for_embedding`, document ID và `age_days`:**
- **Document ID (`paper_id`)**: Sử dụng chính DOI hợp thức của bài báo từ Crossref (ví dụ: `10.1145/3637528.3671801`), đóng vai trò khóa chính duy nhất đảm bảo tính idempotent khi nạp vector store.
- **`age_days`**: Được tính bằng hiệu số giữa ngày thực thi pipeline (`run_date`, gán timezone chuẩn UTC) và ngày công bố chính thức (`published`): `(run_date.date() - published_dt.date()).days`. Giá trị này là cơ sở định lượng để đánh giá độ trễ kiến thức trong Freshness SLA.
- **`text_for_embedding`**: Hợp nhất có cấu trúc các metadata quan trọng nhất theo mẫu:
  ```text
  Title: {title}
  Authors: {authors_joined}
  Published: {published}
  Categories: {categories_joined}
  Summary: {summary}
  ```
  Cách tổ chức này giúp mô hình vector embedding nắm bắt được đồng thời ngữ cảnh tiêu đề, chuyên ngành nghiên cứu và nội dung tóm tắt chi tiết.

---

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế | Ghi chú |
| --- | --- | --- |
| Số câu hỏi | `10` câu hỏi | Thiết kế độc lập bám sát thực tế các kịch bản RAG |
| Các `question_type` | 4 nhóm: `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu) | Phủ đầy đủ các khía cạnh tra cứu thông tin học thuật |
| Ground-truth document ID | DOI tương ứng của bài báo trong tập clean | Ví dụ: `10.1145/3637528.3671801` đối với `q_summary_01` |
| Embedding model | `gemini-embedding-001` / `sentence-transformers/all-MiniLM-L6-v2` | Kích thước vector chuẩn, độ tương đồng cosine |
| Vector store / Collection | ChromaDB PersistentClient (`data/chroma/`) | Tách riêng các collection: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | `4` | Lấy 4 ngữ cảnh có độ tương đồng ngữ nghĩa cao nhất |
| LLM provider / model | `gemini` / `gemini-2.5-flash` | Thực thi trả lời và chấm điểm tự động |
| Test set dùng chung | `data/eval/test_set.json` | Hash SHA-256 cố định xuyên suốt 3 pha |

**Tại sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired?**
Trong thực nghiệm khoa học dữ liệu, việc giữ cố định Evaluation Test Set là nguyên tắc tối thượng nhằm đảm bảo tính **kiểm soát biến số (controlled experiment)**. Bằng cách cố định 10 câu hỏi, ground truth và ground-truth document IDs, mọi sự biến thiên trong các chỉ số đo lường (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) hoàn toàn xuất phát từ chất lượng của corpus dữ liệu và vector index, thay vì do sự thay đổi độ khó hay ngữ nghĩa của tập câu hỏi đánh giá.

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | :---: | --- |
| Raw response/records | `data/raw/crossref_records.json` | Có | 24 bản ghi snapshot từ Crossref |
| Cleaned dataset | `data/clean/papers_clean.csv`, `papers_clean.json` | Có | Dữ liệu sạch, schema đầy đủ |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | Vector store ChromaDB đã index 24 tài liệu |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu hỏi benchmark chuẩn hóa |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Đầy đủ 4 chỉ số chất lượng |
| Quality/freshness | `data/quality/baseline_quality_report.json`, `freshness_report.json` | Có | Báo cáo Great Expectations và SLA |
| Baseline report | `data/reports/phase1_report.md` | Có | Báo cáo tổng hợp pha 1 |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | **1.0000** (100.0%) | 10/10 câu hỏi trích xuất chính xác tài liệu ground-truth trong top-4 |
| `mean_token_f1` | **1.0000** | Độ trùng khớp từ vựng giữa câu trả lời và ground truth đạt tuyệt đối |
| `judge_accuracy` | **1.0000** (100.0%) | 10/10 câu trả lời được LLM Judge thẩm định là chính xác và trung thực |
| `mean_judge_score` | **5.00 / 5.0** | Điểm số đánh giá chất lượng phản hồi tối đa |
| Ragas | N/A | Tạm bỏ qua (`RUN_RAGAS=0`) để tối ưu hóa thời gian thực thi pipeline |

---

## 8. Data quality và freshness

### Quality checks (Great Expectations 1.x)

| Check (Expectation) | Quality dimension | Ngưỡng / Kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `ExpectTableRowCountToBeBetween` | **Completeness** | $5 \le \text{rows} \le 5000$ | **PASS** (Observed: 24) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`paper_id`) | **Completeness** | Null count = 0 | **PASS** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`title`) | **Completeness** | Null count = 0 | **PASS** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`text_for_embedding`) | **Completeness** | Null count = 0 | **PASS** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` (`paper_id`) | **Uniqueness** | Trùng lặp = 0 | **PASS** (0 duplicates) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (`summary`) | **Validity** | Min length $\ge 30$ ký tự | **PASS** (100% đạt) | `baseline_quality_report.json` |

### Freshness SLA

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | Tập dữ liệu sạch `data/clean/papers_clean.csv` qua cột `age_days` |
| Timestamp mới nhất | `2026-07-22` |
| Timestamp cũ nhất | `2026-03-28` |
| Ngưỡng freshness | `180` ngày |
| Số bản ghi quá hạn (stale) | `1 / 24` (4.17%) |
| Ngưỡng vi phạm SLA | $\ge 25\%$ |
| Trạng thái baseline | **✅ FRESH** |
| Lý do | Tỷ lệ bản ghi quá hạn (4.17%) nằm sâu dưới ngưỡng cảnh báo 25%, đảm bảo độ tươi mới cao |

---

## 9. Corruption scenarios và repair

### Các kịch bản tiêm lỗi (Corruption Scenarios)

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế đến RAG | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| `drop_latest_records` | Loại bỏ 20% bản ghi mới nhất theo ngày phát hành | 5 records (`10.1145/3637528.3671812`, `.3671808`, `.3671804`, `.3671807`, `.3671802`) | Freshness `latest_published` giảm mạnh; tổng số dòng giảm từ 24 xuống 19 | Gây retrieval miss cho các câu hỏi nhắm vào tài liệu mới (`q_summary_02`, `q_date_01`, `q_date_02`, `q_authors_01`) | Re-ingest từ raw snapshot bất biến |
| `blank_summary` | Xóa rỗng chuỗi tóm tắt (`summary = ""`) | 2 records (`10.1145/3637528.3671801`, `.3671803`) | Great Expectations cảnh báo vi phạm độ dài tối thiểu $\ge 30$ | RAG Agent truy xuất được doc nhưng nhận context rỗng, trả về câu trả lời rỗng (`q_summary_01` score 1) | Re-extract abstract từ raw snapshot |
| `inject_noise` | Nối chuỗi rác `@@###CORRUPTED_TEXT###@@` vào tóm tắt | 2 records (`10.1145/3637528.3671805`, `.3671806`) | Giảm độ sạch text; có thể làm lệch vector embedding | Tăng khoảng cách vector trong không gian embedding | Tái tạo lại chuỗi sạch từ raw record |
| `truncate_title` | Cắt ngắn tiêu đề còn 7 ký tự | 2 records (`10.1145/3637528.3671809`, `.3671810`) | Mất mát thông tin ngữ nghĩa tiêu đề | Giảm độ tương đồng ngữ nghĩa khi query nhắm vào title | Khôi phục title gốc từ raw data |
| `stale_date` | Lùi ngày xuất bản về 365 ngày trước (`age_days = 365`) | 2 records (`10.1145/3637528.3671813`, `.3671814`) | Số bản ghi stale tăng từ 1 lên 3 (14.29%) | Vi phạm tiêu chí độ tươi mới của tài liệu | Tính toán lại ngày xuất bản từ nguồn |
| `duplicate_rows` | Sao chép và nối thêm 2 bản ghi đầu vào cuối bảng | 2 records nhân bản (tổng cộng 4 bản ghi trùng DOI) | Vi phạm nghiêm trọng Expectation `ExpectColumnValuesToBeUnique` | Tạo các vector trùng lặp (duplicate / ghost vectors) gây nhiễu ranking | Deduplication dựa trên khóa chính DOI |

### Phân tích Corruption Log

- **Đường dẫn**: `data/results/corruption_log.json`
- **Trạng thái**: Đã lưu đầy đủ và chi tiết.
- **Nhận xét**: File log ghi nhận chi tiết từng hành động (`action`), định danh bản ghi bị tác động (`paper_id`) và diff trước/sau (`changes`), đảm bảo tính kiểm toán và giải thích minh bạch trong toàn bộ quá trình thực nghiệm.

### Cơ chế Repair Idempotent

Thay vì thực hiện các phép vá lỗi chắp vá (heuristic patching) trên tập dữ liệu đã bị biến dạng (vốn tiềm ẩn nguy cơ để sót lỗi hoặc làm sai lệch phân phối dữ liệu), nhóm triển khai chiến lược **Idempotent Rebuild từ Immutable Raw Snapshot**:
1. Đọc lại nguyên bản 24 records từ tệp dữ liệu gốc bất biến `data/raw/crossref_records.json`.
2. Áp dụng toàn bộ quy tắc chuẩn hóa của `build_clean_dataframe()`, làm sạch lại từ đầu.
3. Ghi đè vào các artifact phục hồi: `data/clean/papers_clean_repaired.csv` và `.json`.
4. Xây dựng lại vector index trên collection độc lập `papers-repaired`, đảm bảo không bị lẫn vector rác từ collection lỗi.

---

## 10. So sánh baseline, corrupted và repaired

### Bảng đối chiếu hiệu năng và chất lượng

| Metric / Signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | **1.0000** | **0.6000** | **1.0000** | **-40.0%** | **100.0%** | 4 câu hỏi bị miss do 5 bản ghi mới nhất bị xóa khỏi index |
| `mean_token_f1` | **1.0000** | **0.5817** | **1.0000** | **-41.83%** | **100.0%** | Điểm F1 sụt giảm nghiêm trọng do thiếu context và context rỗng |
| `judge_accuracy` | **1.0000** | **0.6000** | **1.0000** | **-40.0%** | **100.0%** | Tỷ lệ câu trả lời đạt yêu cầu giảm tương ứng với retrieval hit rate |
| `mean_judge_score` | **5.00** | **3.20** | **5.00** | **-1.80** | **100.0%** | Điểm trung bình của LLM Judge bị kéo tụt rõ rệt |
| Quality checks (GX 1.x) | **PASS** (6/6) | **FAIL** (4/6) | **PASS** (6/6) | **2 checks fail** | **100.0%** | Vi phạm tính duy nhất `paper_id` và độ dài `summary` $\ge 30$ |
| Freshness status | **FRESH** (4.17%) | **FRESH** (14.29%) | **FRESH** (4.17%) | +10.12% stale | **100.0%** | Tăng số bài cũ nhưng chưa vượt ngưỡng 25% SLA; phục hồi hoàn toàn |

### Hai chuỗi quan hệ nhân quả có bằng chứng thực nghiệm

1. **Chuỗi tác động của Corruption (Data Corruption $\rightarrow$ Observability Signal $\rightarrow$ Agent Degradation):**
   - *Nguyên nhân*: Thao tác tiêm lỗi `drop_latest_records` đã loại bỏ 5 bản ghi mới nhất, đồng thời `blank_summary` xóa sạch phần tóm tắt của bài báo `10.1145/3637528.3671801`.
   - *Tín hiệu Observability*: Quality Gate lập tức báo động **FAIL** (2 kỳ vọng thất bại tại `corrupted_quality_report.json`), ghi nhận 4 bản ghi có summary rỗng và 4 bản ghi trùng DOI.
   - *Hậu quả tới Agent*: Tại `corrupted_answers.json`, các câu hỏi `q_summary_02`, `q_date_01`, `q_date_02`, `q_authors_01` bị trượt retrieval (`retrieval_hit: false`), trong khi `q_summary_01` dù tìm được document nhưng do context rỗng nên Agent trả về chuỗi rỗng (`answer: ""`, `token_f1: 0.0`, `judge score: 1`). Hiệu năng toàn hệ thống sụt giảm 40%.
2. **Chuỗi phục hồi của Repair (Idempotent Rebuild $\rightarrow$ Quality Recovery $\rightarrow$ Agent Performance Restoration):**
   - *Hành động*: Module `repair_from_raw_snapshot` đọc lại 24 records nguyên gốc từ `data/raw/crossref_records.json`, tái tạo toàn bộ clean dataset và re-index vào collection `papers-repaired`.
   - *Tín hiệu Observability*: Báo cáo `repaired_quality_report.json` ghi nhận **PASS** toàn bộ 6/6 Expectations; `repaired_freshness_report.json` đưa tỷ lệ stale trở lại mức an toàn 4.17%.
   - *Kết quả Agent*: Toàn bộ 10/10 câu hỏi tại `repaired_answers.json` tìm lại đúng tài liệu ngữ cảnh, Token F1 đạt **1.0000** và LLM Judge cho điểm tuyệt đối **5.00/5.00**.

---

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy thực nghiệm tuần tự Baseline $\rightarrow$ Corrupted $\rightarrow$ Repaired trên cùng một ChromaDB PersistentClient, các vector cũ từ pha trước không bị xóa hoàn toàn mà tồn tại dưới dạng "vector ma" (ghost vectors / orphaned embeddings). Điều này khiến quá trình retrieval ở pha Repaired có nguy cơ trích xuất nhầm các vector bị hỏng từ pha Corrupted. Ngoài ra, trên môi trường Python 3.10, việc gọi `datetime.UTC` gây ra lỗi `ImportError: cannot import name 'UTC' from 'datetime'`.
- **Nguyên nhân:** ChromaDB PersistentClient lưu trữ index trực tiếp trên disk (`data/chroma/`). Nếu dùng chung collection name và chỉ gọi `add()` hoặc `upsert()`, các ID bị xóa ở pha corrupted vẫn tồn tại trong index. Đối với lỗi datetime, thuộc tính `datetime.UTC` chỉ mới được giới thiệu từ Python 3.11+.
- **Cách xử lý:**
  1. Tách biệt hoàn toàn không gian vector bằng các collection độc lập: `papers-baseline`, `papers-corrupted` và `papers-repaired`. Khi build index cho từng trạng thái, hàm `LocalEmbeddingIndex.build()` luôn trỏ đúng collection tương ứng.
  2. Bổ sung cơ chế tương thích ngược (backwards compatibility) cho datetime:
     ```python
     try:
         from datetime import UTC
     except ImportError:
         from datetime import timezone
         UTC = timezone.utc
     ```
- **Cách xác minh:** Kiểm tra số lượng vector bằng `chroma_client.get_collection("papers-repaired").count()`, xác nhận đúng 24 vectors sạch và kiểm tra toàn bộ 10 câu hỏi đánh giá đạt Hit Rate 1.0000.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| **Quy mô tập dữ liệu còn nhỏ** (24 bài báo) | Chưa phản ánh hết độ phức tạp của không gian vector khi có hàng chục ngàn tài liệu | Mở rộng ingestion lên $\ge 1,000$ bài báo từ Crossref/ArXiv, đo lường độ trễ truy vấn (latency P99) và đánh giá độ chính xác top-K |
| **Data Quality Gate chạy độc lập (offline)** | Cảnh báo chất lượng phát hiện ra lỗi nhưng chưa tự động ngắt (fail-closed) quá trình index ChromaDB | Tích hợp pre-indexing gate: nếu `run_data_quality_checks().success == False`, tự động abort pipeline và gửi alert qua Webhook thay vì tiếp tục đánh chỉ mục |
| **Chưa đánh giá Ragas đa chiều** | Báo cáo hiện dựa trên Token F1 và LLM Judge đơn lẻ, thiếu các chỉ số chuyên sâu như Faithfulness hay Context Recall | Cấu hình tham số `RUN_RAGAS=1` với cơ chế tính toán bất đồng bộ theo batch để bổ sung 4 chỉ số Ragas tiêu chuẩn |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
