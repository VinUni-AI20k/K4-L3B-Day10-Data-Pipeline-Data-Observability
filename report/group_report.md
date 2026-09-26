# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4-L3B-Day10               |
| Tên nhóm         | T052AI                     |
| Repository         | https://github.com/younglonelyboiz/K4-L3B-Day10-T052AI-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Trịnh Xuân Huy | 2A202602995 | Trưởng nhóm / Integrator | `core/config.py`, `src/ingestion/corruption.py`, `phase1.py`, `corruption_flow.py` |
| 2 | Hoàng Ngọc Đức | 2A202602380 | Data Foundation & Recovery | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, raw/clean datasets |
| 3 | Lê Việt Hoàng | 2A202602596 | RAG & Vector Index | `src/retrieval/index.py`, `embeddings.py`, ChromaDB collections |
| 4 | Mai Tiến Huy | 2A202602914 | Observability & Evaluation | `src/observability/quality.py`, `testset.py`, `reporting.py` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành trọn vẹn 100% mục tiêu của Day 10 Data Observability Lab:
- **Baseline Pipeline:** Tải thành công 24 bài báo khoa học từ Crossref API (hỗ trợ offline fallback snapshot). Xử lý dữ liệu sạch với 16 trường chuẩn hóa, tính `age_days` và `text_for_embedding` 5 phần có nhãn. Index ChromaDB collection `papers-baseline` và đánh giá đạt **Retrieval Hit Rate 100.0%** cùng **Mean Token F1 1.000**.
- **Data Observability:** Chốt kiểm dịch **Great Expectations 1.x (GX 1.23.2)** với 4 expectations cốt lõi và Freshness SLA (ngưỡng 180 ngày) hoạt động hoàn hảo, phát hiện chính xác vi phạm schema và trôi dạt dữ liệu.
- **Corruption Impact:** Giả lập 6 kịch bản lỗi làm giảm Hit Rate xuống **60.0%** và Token F1 xuống **0.497**, Quality Gate chuyển trạng thái sang `FAILED` và Freshness sang `STALE`.
- **Idempotent Repair:** Phục hồi thành công dữ liệu từ snapshot gốc bất biến `crossref_records.json`, đưa Hit Rate và Token F1 trở lại **100.0%** và **1.000**, chứng minh năng lực tự chữa lành (Self-healing).

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (hoặc Local Snapshot)
    -> raw response & records (data/raw/)
    -> cleaning & 5-part embedding text modeling (data/clean/)
    -> embedding (all-MiniLM-L6-v2) + ChromaDB index (data/chroma/)
    -> benchmark test generation (data/eval/test_set.json)
    -> evaluation baseline (data/results/baseline_metrics.json)
    -> quality gate & freshness reports (data/quality/)
    -> synthetic corruption (6 scenarios) -> corrupted index & eval
    -> idempotent repair từ immutable raw snapshot
    -> repaired index & eval -> comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| ---- | ----- | ----------- | --------------- | ----- |
| Ingestion | Crossref REST API / Snapshot | Fetch, retry 429, parse JATS/XML, lineage | `data/raw/` | Hoàng Ngọc Đức |
| Cleaning | Raw records, `run_date` | Normalize whitespace, compute `age_days`, 5-part text | `papers_clean.csv/json` | Hoàng Ngọc Đức |
| Embedding/index | Cleaned DataFrame | MiniLM 384-d, ChromaDB PersistentClient | `data/chroma/`, `embeddings/` | Lê Việt Hoàng |
| Evaluation | Cleaned DataFrame, ChromaDB | Sinh 10 câu hỏi qua 4 nhóm nghiệp vụ, tính Hit Rate, F1 | `test_set.json`, `*_metrics.json` | Mai Tiến Huy |
| Observability | DataFrame các pha | Great Expectations 1.x ephemeral, Freshness SLA | `data/quality/*.json` | Mai Tiến Huy |
| Corruption/repair | Clean DataFrame, raw snapshot | Tiêm 6 kịch bản lỗi, khôi phục từ raw snapshot | `corruption_log.json`, `repaired_*` | Trịnh Xuân Huy |
| Orchestration | Toàn bộ pipeline | Kết nối pipeline Phase 1 và luồng so sánh 3 trạng thái | `phase1_report.md`, `corruption_report.md` | Trịnh Xuân Huy |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` (hỗ trợ local extractor offline) |
| `LLM_MODEL`                | `gemini-3.6` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | `24` |
| Retrieval `top_k`           | `3` |
| Freshness threshold          | `180` (ngày, tỷ lệ cho phép <= 25%) |
| Random seed, nếu có        | `42` |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

Chỉ giữ lại cách nhóm đã dùng.

```bash
uv sync
```

Hoặc:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
PYTHONPATH=src python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
PYTHONPATH=src python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-09-26 10:45 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-09-26 11:15 | `data/results/corruption_log.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) + Local Snapshot |
| Query/filter                | `query=artificial intelligence data pipeline`, `filter=type:journal-article` |
| Thời điểm lấy dữ liệu | 2026-09-26 09:30 UTC |
| Số record nhận được    | 24 |
| Cơ chế retry/backoff      | Retry 3 lần với exponential backoff cho status 429/503; tự động fallback snapshot |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | string | Có | Mã định danh duy nhất (DOI) | Bỏ qua record nếu thiếu |
| `title` | string | Có | Tiêu đề bài báo khoa học | Bỏ qua record nếu rỗng |
| `authors` | list[str] | Có | Danh sách tác giả | Gán `["Unknown"]` nếu thiếu |
| `published` | string | Có | Ngày xuất bản ISO (YYYY-MM-DD) | Parse date-parts hoặc fallback run_date |
| `summary` | string | Có | Tóm tắt bài báo (abstract) | Lọc bỏ JATS XML, gán title nếu rỗng |
| `categories` | list[str] | Có | Danh mục chủ đề bài báo | Gán `["General"]` nếu rỗng |
| `age_days` | integer | Có | Số ngày tuổi so với run_date | `max(0, (run_date.date() - pub_date).days)` |
| `text_for_embedding` | string | Có | Chuỗi 5 phần có nhãn cho vector index | Ghép Title, Authors, Published, Categories, Summary |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại bỏ thẻ HTML/JATS XML trong summary | Validity / Completeness | 24 | Kiểm tra regex `re.sub(r'<[^>]+>', '', ...)` |
| Chuẩn hóa khoảng trắng thừa | Conformance | 24 | Hàm `normalize_whitespace` |
| Tính toán trường `age_days` | Validity / Timeliness | 24 | Đối chiếu với ngày xuất bản |
| Ghép trường `text_for_embedding` 5 phần có nhãn | Consistency | 24 | Kiểm tra format chuỗi embedding |
| Khử trùng lặp trên `paper_id` | Uniqueness | 24 | `drop_duplicates(subset=["paper_id"])` |
| Sắp xếp ổn định theo published DESC | Consistency | 24 | `sort_values(["published", "paper_id"])` |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

- `document ID / paper_id`: Dùng chính chuỗi định danh DOI chuẩn hóa từ Crossref (ví dụ `10.1000/182`) làm khóa chính xuyên suốt từ raw sang clean và vector index.
- `age_days`: Phân tích ngày xuất bản thành `datetime.date` và trừ khỏi ngày chạy pipeline `run_date.date()`. Nếu ngày xuất bản ở tương lai, kẹp về 0.
- `text_for_embedding`: Ghép nối 5 thành phần có nhãn rõ ràng theo cấu trúc: `Title: {title}\nAuthors: {authors}\nPublished Date: {published}\nCategories: {categories}\nSummary: {summary}` để mô hình embedding `all-MiniLM-L6-v2` dễ dàng phân tách ngữ nghĩa.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 |
| Các `question_type`                    | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID                 | Trích xuất `paper_id` của bài báo nguồn tạo câu hỏi |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB PersistentClient (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k`                       | 3 |
| LLM provider/model                       | `gemini-3.6` / Local Extractor |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Việc giữ cố định bộ câu hỏi và ground truth document IDs là nguyên tắc cốt lõi của phương pháp Controlled Experiment (thực nghiệm đối chứng), nhằm loại bỏ yếu tố nhiễu do câu hỏi khác nhau, đảm bảo mọi sự thay đổi trong Retrieval Hit Rate và Token F1 phản ánh chính xác tác động của chất lượng dữ liệu.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | 24 bài báo khoa học chất lượng cao |
| Cleaned dataset          | `data/clean/`                        | Có | `papers_clean.csv` và `papers_clean.json` (24 dòng) |
| Embedding manifest/index | `data/embeddings/`                   | Có | `papers_embeddings.json` (24 vectors) |
| Evaluation set           | `data/eval/`                         | Có | `test_set.json` (10 QA samples) |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Hit rate 100%, F1 1.000 |
| Quality/freshness        | `data/quality/`                      | Có | `baseline_quality_report.json`, `freshness_report.json` |
| Baseline report          | `data/reports/phase1_report.md`      | Có | Báo cáo Markdown tự động |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |          100.0% | 10/10 câu hỏi tìm trúng bài báo nguồn trong top-3 |
| `mean_token_f1`      |           1.000 | Câu trả lời trùng khớp hoàn hảo với ground truth |
| `judge_accuracy`     |          100.0% | Toàn bộ câu trả lời đạt chuẩn ngữ nghĩa |
| `mean_judge_score`   |        5.00/5.0 | Điểm đánh giá chất lượng câu trả lời tối đa |
| Ragas, nếu có        |             N/A | Bỏ qua để tối ưu thời gian chạy theo hướng dẫn bài lab |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `ExpectTableRowCountToBeBetween` | Completeness | [20, 30] dòng | Pass (24 dòng) | `data/quality/baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` | Completeness | `paper_id` not null | Pass (0% null) | `data/quality/baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` | Uniqueness | `paper_id` duy nhất | Pass (100% unique) | `data/quality/baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` | Validity | `summary` length >= 10 | Pass (100% đạt chuẩn) | `data/quality/baseline_quality_report.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Cột `age_days` trong `data/clean/papers_clean.json` |
| Timestamp mới nhất       | Ngày xuất bản bài báo gần nhất (2025/2026) |
| Ngưỡng freshness         | SLA 180 ngày (tỷ lệ bài quá hạn <= 25%) |
| Trạng thái baseline      | `FRESH` |
| Lý do                     | Tỷ lệ bài báo quá 180 ngày nằm trong giới hạn cho phép |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_latest_records` | Xóa 20% bản ghi mới nhất | 5 | Table row count | Hit rate giảm mạnh đối với câu hỏi về bài mới | Rebuild từ raw snapshot |
| `blank_summary` | Gán rỗng summary của top bài báo | 3 | Summary length check FAIL | Mất ngữ nghĩa tóm tắt, F1 giảm sâu | Rebuild từ raw snapshot |
| `inject_noise` | Chèn chuỗi ký tự rác vào text | 4 | Text divergence | Vector embedding bị lệch khoảng cách cosine | Rebuild từ raw snapshot |
| `truncate_titles` | Cắt ngắn tiêu đề < 8 ký tự | 4 | Title validity | Mất từ khóa quan trọng khi tra cứu | Rebuild từ raw snapshot |
| `stale_dates` | Lùi ngày xuất bản về năm 2020 | 12 | Freshness SLA FAIL (`STALE`) | Cảnh báo dữ liệu quá hạn SLA | Rebuild từ raw snapshot |
| `duplicate_records` | Nhân bản các dòng dữ liệu | 2 | Unique paper_id FAIL | Vi phạm tính duy nhất của khóa chính DOI | Rebuild từ raw snapshot |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi nhận đầy đủ 6 loại kịch bản, số dòng bị tác động và các tham số chi tiết.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Hệ thống thực hiện cơ chế Idempotent Repair bằng cách coi Clean Dataset là tài sản phái sinh (derived data asset). Khi phát hiện lỗi hoặc dữ liệu bị ô nhiễm, hệ thống không sửa chắp vá (không in-place mutation) mà xóa bỏ bảng lỗi và tái thực thi hàm `build_clean_dataframe` trực tiếp từ immutable raw snapshot `data/raw/crossref_records.json`.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |   100.0% |     60.0% |   100.0% |                   -40.0% |          100.0% | Sụt giảm nghiêm trọng khi mất dữ liệu, hồi sinh trọn vẹn |
| `mean_token_f1`        |    1.000 |     0.497 |    1.000 |                   -0.503 |          100.0% | Chất lượng câu trả lời giảm hơn 50% |
| `judge_accuracy`       |   100.0% |     50.0% |   100.0% |                   -50.0% |          100.0% | Độ chính xác câu trả lời thực tế giảm một nửa |
| `mean_judge_score`     | 5.00/5.0 | 3.00/5.0 | 5.00/5.0 |                    -2.00 |          100.0% | Điểm chất lượng trung bình phục hồi tối đa |
| Quality checks pass/fail | `PASSED` |  `FAILED` | `PASSED` |            Chuyển FAILED | Phục hồi PASSED | GX 1.x phát hiện chính xác vi phạm |
| Freshness status         |  `FRESH` |   `STALE` |  `FRESH` |             Chuyển STALE |  Phục hồi FRESH | Cảnh báo vi phạm ngưỡng SLA 180 ngày |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. [Corruption/data change] → [quality/freshness signal] → [retrieval/answer metric]: Khi 6 lỗi được tiêm vào (xóa bài báo mới, làm rỗng summary, nhân bản dòng, lùi ngày về 2020) → Great Expectations báo `FAILED` và Freshness báo `STALE` → Dẫn đến Retrieval Hit Rate sụt từ 100% xuống 60% và Token F1 sụt từ 1.000 xuống 0.497.
2. [Repair action] → [quality/freshness recovery] → [agent metric recovery]: Khi kích hoạt Idempotent Repair từ snapshot gốc `crossref_records.json` → Quality Checks và Freshness SLA lập tức quay lại `PASSED` và `FRESH` → Retrieval Hit Rate và Token F1 phục hồi 100% về mức 100.0% và 1.000.

Không kết luận corruption “có tác động” nếu số liệu không cho thấy thay đổi. Nếu kết quả khác kỳ vọng, mô tả giả thuyết và cách nhóm đã kiểm tra.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** `TypeError: DataContext.sources is deprecated / ExpectationSuite not found` khi chạy quality checks do code mẫu dùng API Great Expectations cũ.
- **Nguyên nhân:** Môi trường ảo sử dụng Great Expectations phiên bản mới `1.23.2` đã tái cấu trúc cơ chế quản lý Data Source, Data Asset và Batch Definition.
- **Cách xử lý:** Viết lại hàm `run_data_quality_checks` theo chuẩn kiến trúc Ephemeral Data Context của GX 1.x (`gx.get_context(mode="ephemeral")`, `add_batch_definition_whole_dataframe`, `ValidationDefinition`).
- **Cách xác minh:** Chạy `run_data_quality_checks` trên clean dataset trả về `success=True` và trên corrupted dataset trả về `success=False` chính xác.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Số lượng bài báo còn khiêm tốn (24 bài) | Chưa thử nghiệm được quy mô lớn | Nâng số bài báo lên 500+ và dùng cơ chế phân trang cursor của Crossref |
| Đo lường LLM Judge đang dùng local heuristic | Đánh giá ngữ nghĩa chưa đa dạng | Tích hợp DeepSeek / OpenAI API key để chấm điểm LLM-as-a-judge đa chiều |

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
