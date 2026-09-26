# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4 - Lớp B (Ca Sáng)      |
| Tên nhóm         | Team 03 - DataObservability |
| Repository         | K4-L3B-DAY10-Team03-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Đức Anh | 2A202602888 | Trưởng nhóm / Pipeline Integrator | `src/core/`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/` |
| 2 | Đặng Thái Anh | 2A202602740 | Data Foundation & Recovery | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, raw data artifacts |
| 3 | Đỗ Trung Tuyến | 2A202602427 | RAG Agent & Vector Index Architecture | `src/retrieval/index.py`, `src/retrieval/embeddings.py`, `src/retrieval/agent.py`, `src/retrieval/qa.py`, ChromaDB |
| 4 | Nguyễn Khánh Duy | 2A202602403 | Data Observability & Evaluation | `src/observability/quality.py`, `src/observability/reporting.py`, `src/evaluation/testset.py`, `src/evaluation/metrics.py`, Dashboard |

---

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn diện 100% các yêu cầu từ Checkpoint 0 đến Checkpoint 6 cùng các hạng mục điểm thưởng mở rộng (Bonus B1, B2, B3).

Trong **Pha 1 (Baseline)**, pipeline thu thập thành công 24 bài báo khoa học từ Crossref API (kèm cơ chế offline fallback), làm sạch dữ liệu, chuẩn hóa cấu trúc 5 thành phần `text_for_embedding`, lưu trữ an toàn hai raw artifacts đảm bảo Data Lineage, và đánh chỉ mục vector vào ChromaDB collection `papers-baseline` bằng mô hình `sentence-transformers/all-MiniLM-L6-v2`. Hệ thống kiểm định chất lượng tự động **Great Expectations 1.x** (với Ephemeral Context) đạt 100% tiêu chí (`success=True`), Freshness SLA đạt trạng thái Healthy với tỷ lệ quá hạn 4.2% (thấp hơn nhiều so với ngưỡng cảnh báo 25%). Bộ câu hỏi benchmark gồm 10 câu hỏi đa dạng đạt Retrieval Hit Rate tuyệt đối 100.0% và Mean Token F1 100.0%.

Trong **Pha 2 (Data Corruption)**, nhóm tiêm 6 kịch bản suy thoái dữ liệu thực tế (mất 20% bản ghi mới, rỗng summary, nhiễu văn bản, cắt ngắn title < 8 ký tự, ngày cũ 2018 vi phạm freshness, và bản ghi trùng lặp). Kết quả làm bộc lộ rõ nét hiện tượng **Silent Failure**: mã nguồn không quăng Exception nhưng Retrieval Hit Rate sụt giảm nghiêm trọng từ 100.0% xuống còn 60.0% (-40.0%), Token F1 giảm xuống 85.1%, Quality Gate lập tức chuyển sang trạng thái FAILED và Freshness SLA báo động đỏ với 40.9% bản ghi quá hạn.

Trong **Pha 3 (Idempotent Repair)**, quy trình tự phục hồi lấy nguồn từ bản snapshot thô bất biến `data/raw/crossref_records.json`, tái tạo hoàn hảo bộ dữ liệu sạch 24 dòng và nạp lại collection `papers-repaired`. Toàn bộ chỉ số Hit Rate (100.0%), Token F1 (100.0%), Quality Gate (PASSED) và Freshness (HEALTHY) được khôi phục 100% so với Baseline.

Nhóm cũng đã triển khai thành công **Interactive HTML Observability Dashboard** (`report/observability_dashboard.html`), mô-đun **Automated Self-Healing Pipeline** (`src/observability/self_healing.py`), và bộ kiểm thử tự động **Pytest CI Suite** (`tests/test_pipeline.py`) vượt ngưỡng coverage chuẩn.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
+-----------------------------------------------------------------------------------+
|                                RAW INGESTION LAYER                                |
|  Crossref REST API  --->  Local Fallback Snapshot (data/raw/crossref_response.json)|
|                                     |                                             |
|                                     v                                             |
|                 Raw Ingestion Artifact (data/raw/crossref_records.json)           |
+-------------------------------------+---------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------------+
|                           CLEANING & MODELING LAYER                               |
|  Clean JATS XML, Normalize Whitespace, Calculate age_days, Build 5-part Embedding |
|                                     |                                             |
|                                     v                                             |
|           Cleaned Artifacts (data/clean/papers_clean.csv & .json)                 |
+-------------------+-------------------------------------------+-------------------+
                    |                                           |
                    v                                           v
+------------------------------------+  +-------------------------------------------+
|          VECTOR INDEX LAYER        |  |          OBSERVABILITY QUALITY GATE       |
|  ChromaDB: 'papers-baseline'       |  |  Great Expectations 1.x (Ephemeral Context)|
|  Embeddings: MiniLM-L6-v2 (384-d)  |  |  Expectations: RowCount, NotNull, Unique, |
|  Persist: data/chroma/             |  |               ValueLengthBetween          |
+-------------------+----------------+  |  Freshness SLA Check: age_days <= 180     |
                    |                   +---------------------+---------------------+
                    v                                         |
+------------------------------------------------------+      |
|                   EVALUATION LAYER                   |      |
|  Benchmark Test Set (10 questions across 4 domains)  |      |
|  Metrics: Hit Rate (@4), Token F1, LLM Judge Score   |      |
+-------------------+----------------------------------+      |
                    |                                         |
                    v                                         v
+-----------------------------------------------------------------------------------+
|                            CORRUPTION & REPAIR SUITE                              |
|  Inject 6 Scenarios  --->  Corrupted Index & Eval  --->  Silent Failure Detected  |
|                                                                |                  |
|  Idempotent Repair   <---  Reload Immutable Raw Snapshot  <----+                  |
|         |                                                                         |
|         v                                                                         |
|  Repaired Clean Dataset  --->  Repaired Chroma Collection  ---> 100% Recovery     |
+-------------------------------------+---------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------------+
|                        REPORTING & OBSERVABILITY DASHBOARD                        |
|  Markdown Comparison Report (data/reports/corruption_report.md)                   |
|  Interactive Visual HTML Dashboard (report/observability_dashboard.html)          |
+-----------------------------------------------------------------------------------+
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API hoặc `data/raw/crossref_response.json` | Request API có timeout, trích xuất metadata, fallback snapshot nếu lỗi mạng/429 | `data/raw/crossref_records.json` | Đặng Thái Anh |
| Cleaning          | `data/raw/crossref_records.json` | Xử lý JATS XML, tính `age_days`, tạo `text_for_embedding` 5 phần, drop trùng lặp theo `paper_id` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Đặng Thái Anh |
| Embedding/index   | `data/clean/papers_clean.json` | Khởi tạo ChromaDB PersistentClient, sinh vector `all-MiniLM-L6-v2`, nạp metadata | `data/chroma/`, `data/embeddings/papers_embeddings.json` | Đỗ Trung Tuyến |
| Evaluation        | Clean DataFrame & Vector Index | Sinh 10 câu hỏi chuẩn hóa qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`), đo Retrieval Hit Rate và Token F1 | `data/eval/test_set.json`, `data/results/baseline_metrics.json` | Nguyễn Khánh Duy |
| Observability     | Clean DataFrame | Cấu hình Great Expectations 1.x ephemeral batch, kiểm định 7 expectations, tính Freshness SLA | `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json` | Nguyễn Khánh Duy |
| Corruption/repair | Clean DataFrame & Raw records | Tiêm 6 kịch bản lỗi, đo lường suy giảm RAG; khôi phục idempotent từ raw snapshot | `data/results/corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json` | Đặng Thái Anh |
| Orchestration     | Toàn bộ các module | Kết nối thứ tự thực thi Pha 1, Pha 2, cơ chế tự phục hồi, bảo đảm tương thích UTF-8 | `script/run_phase1.py`, `script/run_corruption_flow.py`, `data/reports/` | Nguyễn Đức Anh |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` (hoặc `mock` cho CI offline) |
| `LLM_MODEL`                | `gemini-2.5-flash`  |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k`           | 4 |
| Freshness threshold          | 180 ngày (ngưỡng vi phạm SLA: > 25% bài quá hạn) |
| Random seed / deterministic | Cố định theo thứ tự `published` và `paper_id` |

### Lệnh cài đặt

Kích hoạt môi trường và cài đặt dependencies:

```bash
# Cách 1: Sử dụng pip trong môi trường venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
pip install pytest pytest-cov
```

Hoặc qua `uv`:

```bash
uv sync --extra dev
```

### Lệnh chạy

**1. Chạy Baseline Pipeline (Pha 1):**

```bash
python script/run_phase1.py
```

**2. Chạy Data Observability & Corruption Flow (Pha 2 & 3):**

```bash
python script/run_corruption_flow.py
```

**3. Chạy Automated Self-Healing Pipeline (Bonus B2):**

```bash
python script/run_self_healing.py
```

**4. Chạy toàn bộ Test Suite Pytest với Coverage (Bonus B3):**

```bash
pytest tests/ -v --cov=src
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công (Exit code 0) | 2026-09-26 10:41:03 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công (Exit code 0) | 2026-09-26 10:42:12 | `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` |
| Pytest Test Suite | Thành công (100% passed) | 2026-09-26 10:40:11 | Console output 5/5 tests passed in 3.77s |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter                | `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:...,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-26 10:41:00 UTC              |
| Số record nhận được    | 24 bài báo khoa học chuẩn |
| Cơ chế retry/backoff      | Timeout 10s, bắt Exception và tự động fallback sang local snapshot `data/raw/crossref_response.json` |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id`      | `str`           | Có           | DOI định danh duy nhất của bài báo | Bỏ qua bản ghi nếu rỗng |
| `title`         | `str`           | Có           | Tiêu đề bài báo khoa học | Bỏ qua bản ghi nếu rỗng; làm sạch khoảng trắng |
| `summary`       | `str`           | Có           | Đoạn trích tóm tắt (abstract) | Loại bỏ tag JATS XML (`<jats:p>`), fallback về rỗng nếu thiếu |
| `authors`       | `list[str]`     | Không        | Danh sách tác giả | Ghép họ và tên chuẩn (`given + family`), loại bỏ rỗng |
| `categories`    | `list[str]`     | Không        | Phân loại chủ đề bài báo | Chuẩn hóa mảng chuỗi |
| `published`     | `str` (YYYY-MM-DD) | Có        | Ngày xuất bản chính thức | Trích xuất từ `date-parts`, fallback về `created` hoặc `2026-01-01` |
| `age_days`      | `int`           | Có           | Số ngày từ ngày xuất bản đến thời điểm chạy | `max(0, (run_date - pub_date).days)`, chuẩn hóa timezone |
| `text_for_embedding` | `str`      | Có           | Chuỗi văn bản tổng hợp cấu trúc 5 phần | Ghép theo cấu trúc: Title, Authors, Categories, Published, Summary |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Bỏ qua bản ghi thiếu `paper_id` hoặc `title` | Completeness                 | 0 / 24                     | Kiểm tra `len(df_clean) == 24` |
| Khử thẻ JATS XML `<[^>]+>` trong summary | Validity & Consistency       | 24 / 24                    | Regex stripping, kiểm tra không còn thẻ `<` hoặc `>` |
| Khử trùng lặp bản ghi theo `paper_id`    | Uniqueness                   | 0 / 24 (100% unique)       | `ExpectColumnValuesToBeUnique(column="paper_id")` |
| Chuẩn hóa ngày tháng và tính `age_days`  | Timeliness                   | 24 / 24                    | Trường `age_days` là số nguyên không âm |
| Xây dựng cấu trúc `text_for_embedding` 5 phần | Semantic Integrity     | 24 / 24                    | Chứa đủ 5 tiêu đề: Title, Authors, Categories, Published, Summary |

**Chi tiết tính toán:**
- `age_days`: Được tính bằng hiệu số giữa `run_date` (UTC hiện tại) và `pub_date`. Nhóm xử lý triệt để xung đột timezone giữa naive datetime và aware datetime bằng cách đồng bộ `tzinfo`.
- `text_for_embedding`: Định dạng chuỗi đồng nhất giúp mô hình embedding `all-MiniLM-L6-v2` nắm bắt đồng thời ngữ cảnh tiêu đề, tác giả, chuyên ngành và tóm tắt nghiên cứu.

---

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 câu hỏi benchmark chuẩn |
| Các `question_type`                    | `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu) |
| Ground-truth document ID                 | Trích xuất trực tiếp từ trường `paper_id` của bản ghi mục tiêu |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` (384 chiều, chuẩn hóa cosine) |
| Vector store/collection                  | ChromaDB PersistentClient (`data/chroma/`), các collection riêng biệt |
| Retrieval `top_k`                       | 4 documents                   |
| LLM provider/model                       | `gemini-2.5-flash` (qua `ChatGoogleGenerativeAI`, judge temperature = 0.0) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (giữ cố định không đổi) |

**Giải thích vì sao test set được giữ nguyên:**
Để việc đối chiếu hiệu năng giữa ba trạng thái **Baseline - Corrupted - Repaired** đảm bảo tính khoa học và khách quan, biến số được kiểm soát (controlled variable) bắt buộc phải là bộ câu hỏi kiểm thử và ground truth. Nếu thay đổi test set giữa các lần chạy, sự thay đổi chỉ số có thể do độ khó của câu hỏi thay đổi chứ không phản ánh sự suy thoái dữ liệu (data corruption) hay năng lực tự phục hồi (self-healing).

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/crossref_records.json`     | Có           | 24 bản ghi thô đầy đủ metadata |
| Cleaned dataset          | `data/clean/papers_clean.json`, `.csv` | Có           | 24 dòng sạch, có `text_for_embedding` |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json` | Có         | Collection `papers-baseline` trong ChromaDB |
| Evaluation set           | `data/eval/test_set.json`            | Có           | 10 câu hỏi phủ 4 nhóm nghiệp vụ |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có           | Hit Rate: 100.0%, Token F1: 100.0% |
| Quality/freshness        | `data/quality/baseline_quality_report.json` | Có      | GX 1.x 100% Passed, Freshness Healthy |
| Baseline report          | `data/reports/phase1_report.md`      | Có           | Báo cáo Markdown tổng hợp chi tiết |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate`   |          100.0% | Toàn bộ 10/10 câu hỏi đều truy xuất trúng tài liệu mục tiêu trong top 4 kết quả |
| `mean_token_f1`        |          100.0% | Trùng khớp từ vựng hoàn hảo giữa câu trả lời trích xuất và ground-truth |
| `judge_accuracy`       |          100.0% | Mô hình LLM Judge đánh giá 10/10 câu trả lời chính xác về mặt nội dung |
| `mean_judge_score`     |      5.00 / 5.0 | Đạt điểm tuyệt đối 5/5 từ LLM Judge |
| Ragas, nếu có          |         Skipped | Bỏ qua để tối ưu thời gian phản hồi (chạy khi bật `RUN_RAGAS=1`) |

---

## 8. Data quality và freshness

### Quality checks (Great Expectations 1.x)

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ----- | ----------------- | -------------- | ---------------- | ---------- |
| `ExpectTableRowCountToBeBetween` | Completeness | [20, 30] dòng | PASSED (24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull(paper_id)` | Completeness | 0% null | PASSED (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull(title)` | Completeness | 0% null | PASSED (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull(summary)` | Completeness | 0% null | PASSED (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique(paper_id)` | Uniqueness | 100% duy nhất | PASSED (0 trùng) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween(title)` | Validity | >= 8 ký tự | PASSED (min >= 15) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween(summary)` | Validity | >= 20 ký tự | PASSED (min >= 100) | `baseline_quality_report.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `data/clean/papers_clean.json`      |
| Timestamp mới nhất       | `2026-07-22`                        |
| Timestamp cũ nhất        | `2026-03-28`                        |
| Ngưỡng freshness         | `age_days <= 180` (Tỷ lệ quá hạn <= 25%) |
| Trạng thái baseline      | **HEALTHY (`is_fresh = True`)**     |
| Lý do                     | Chỉ có 1 bản ghi cũ hơn 180 ngày (tỷ lệ 4.2% <= 25%) |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ---------- | -------- | -----------------: | ---------------------- | ---------------- | ----------- |
| **1. Drop latest records** | Xóa 20% bản ghi mới nhất (4 bài) | 4 dòng | Row count giảm còn 20 | Hit Rate sụt giảm nghiêm trọng trên các câu hỏi liên quan bài mới | Nạp lại toàn bộ danh sách bản ghi gốc từ raw snapshot |
| **2. Blank summary** | Xóa rỗng chuỗi tóm tắt tại index 0, 1 | 2 dòng | `ExpectColumnValuesToNotBeNull` & length FAILED | Trả lời summary rỗng, Token F1 suy giảm | Trích xuất lại trường summary sạch từ raw records |
| **3. Inject noise** | Chèn chuỗi rác `### CORRUPTED RANDOM NOISE...` | 2 dòng | Giảm khoảng cách cosine vector | Embedding bị nhiễu ngữ nghĩa, giảm similarity | Ghi đè lại summary chuẩn từ raw snapshot |
| **4. Truncate title** | Cắt ngắn tiêu đề thành "Bad" (< 8 ký tự) | 2 dòng | `ExpectColumnValueLengthsToBeBetween` FAILED | Mất khả năng exact lookup theo title | Khôi phục tiêu đề gốc đầy đủ từ raw snapshot |
| **5. Stale date** | Lùi ngày xuất bản về năm 2018 (`age_days = 3000`) | 8 dòng | Freshness SLA VIOLATED (> 25% stale) | Tỷ lệ stale vọt lên 40.9%, vi phạm SLA nghiêm trọng | Khôi phục trường `published` chuẩn từ raw snapshot |
| **6. Duplicate rows** | Nhân bản 2 bản ghi đầu vào cuối DataFrame | 2 dòng | `ExpectColumnValuesToBeUnique` FAILED | Vector index bị trùng lặp kết quả, sai phân bổ | Khử trùng lặp dựa trên khóa `paper_id` |

**Corruption log:**
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: **Đầy đủ**
- Nhận xét: Ghi nhận chính xác 6 kịch bản, số lượng bản ghi bị ảnh hưởng và danh sách `affected_ids` chi tiết.

**Cơ chế Idempotent Repair:**
Thay vì sửa cục bộ hoặc "vá tạm" trên tập dữ liệu đã bị làm bẩn, pipeline tuân thủ nguyên tắc **Idempotency** (tính bất biến): đọc lại từ bản snapshot thô bất biến `data/raw/crossref_records.json`, chạy lại toàn bộ quy trình làm sạch chuẩn, tạo DataFrame sạch mới hoàn toàn, sau đó xóa collection ChromaDB cũ và nạp lại. Cơ chế này đảm bảo dù chạy một lần hay một trăm lần, kết quả luôn đồng nhất 100% với Baseline chuẩn.

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |   100.0% |     60.0% |   100.0% |                   -40.0% |            100% | Lỗi drop bài mới và nhiễu làm sụt giảm 4 câu truy xuất |
| `mean_token_f1`        |   100.0% |     85.1% |   100.0% |                   -14.9% |            100% | Summary bị rỗng và nhiễu làm giảm độ chính xác từ khóa |
| `judge_accuracy`       |   100.0% |     90.0% |   100.0% |                   -10.0% |            100% | LLM Judge phát hiện câu trả lời thiếu ngữ cảnh |
| `mean_judge_score`     |     5.00 |      4.20 |     5.00 |                    -0.80 |            100% | Phục hồi điểm tối đa 5/5 |
| Quality checks pass/fail |   PASSED |    FAILED |   PASSED |               Chuyển đỏ  |            100% | Chốt kiểm dịch GX 1.x chặn đứng dữ liệu bẩn |
| Freshness status         |  HEALTHY |  VIOLATED |  HEALTHY |          40.9% > 25% SLA |            100% | Khôi phục độ tươi về 0.0% stale |

**Hai chuỗi quan hệ nhân quả cốt lõi:**
1. *Tiêm lỗi:* `Drop latest records (20%)` & `Inject noise into summary` $\rightarrow$ Great Expectations báo lỗi `ExpectTableRowCountToBeBetween` & Freshness SLA vi phạm (40.9% stale) $\rightarrow$ Retrieval Hit Rate sụt giảm nghiêm trọng từ 100% xuống 60%, chứng minh hiện tượng **Silent Failure**.
2. *Phục hồi:* `Idempotent Repair từ raw snapshot` $\rightarrow$ Khôi phục 24 dòng sạch, Great Expectations đạt 100% PASSED và Freshness SLA trở về HEALTHY $\rightarrow$ Retrieval Hit Rate và Token F1 lập tức hồi phục về mức tuyệt đối 100.0%.

---

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy script kiểm tra trên Windows PowerShell / CMD mặc định, chương trình bị crash ngay lập tức với lỗi:
  `UnicodeEncodeError: 'charmap' codec can't encode characters in position 6-7: character maps to <undefined>` khi in các chuỗi tiếng Việt như `Môi trường sẵn sàng`.
- **Nguyên nhân:** Windows console mặc định sử dụng code page ANSI (cp1252), không hỗ trợ bảng mã UTF-8 của tiếng Việt có dấu.
- **Cách xử lý:** 
  1. Thêm đoạn mã tự động cấu hình lại bộ đệm stdout tại các entrypoint:
     ```python
     import sys
     if hasattr(sys.stdout, "reconfigure"):
         sys.stdout.reconfigure(encoding="utf-8", errors="replace")
     ```
  2. Bổ sung cờ `-X utf8` và thiết lập biến môi trường `$env:PYTHONIOENCODING="utf-8"` trong tất cả các script thực thi.
- **Cách xác minh:** Chạy lại `python script/run_phase1.py` và `python script/run_corruption_flow.py`, toàn bộ console hiển thị tiếng Việt và ký tự đặc biệt mượt mà với exit code 0.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Quy mô bộ dữ liệu thử nghiệm hiện tại dừng ở 24 bài báo | Chưa đo lường được hiệu năng vector search khi dữ liệu tăng lên hàng triệu bản ghi | Tích hợp phân trang (paging cursor) từ Crossref API để mở rộng lên 10,000+ bản ghi và đo lường latency HNSW index |
| Mô hình embedding chạy CPU cục bộ | Thời gian tạo embedding cho bộ dữ liệu lớn có thể chậm | Cấu hình batching song song hoặc hỗ trợ inference qua GPU (CUDA) / ONNX Runtime |
| Kiểm định Freshness dựa trên ngày xuất bản tĩnh | Bài báo cập nhật bổ sung (updated) có thể bị đánh giá cũ | Bổ sung kiểm tra trường `updated` song song với `published` trong SLA logic |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác (`K4-L3B-DAY10-Team03-DataPipelineDataObservability`).
- [x] Phân công khớp với module, artifact và kết quả thực tế trong `docs/TEAM.md`.
- [x] Lệnh tái hiện đã được chạy lại thành công trên phiên bản dùng để nộp (Exit code 0).
- [x] Baseline, corrupted và repaired dùng chung một evaluation test set (`data/eval/test_set.json`).
- [x] Bảng metrics khớp 100% với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp 100% với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng (`<MSSV>_HoTen.md`).
- [x] Tuyệt đối không commit file `.env`, API key, token bí mật lên GitHub repository.
