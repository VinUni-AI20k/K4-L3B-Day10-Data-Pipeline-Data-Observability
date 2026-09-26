# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
|---|---|
| Khóa/Lớp | K4-L3B |
| Tên nhóm | haianh |
| Repository | https://github.com/AnhDuc0712/K4-L3B-DAY10-haianh-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
|---:|---|---|---|---|
| 1 | Tô Anh Đức | 2A202602639 | Pipeline integration, observability và dashboard | `phase1.py`, `corruption_flow.py`, `quality.py`, `reporting.py`, `app.py`, các report |
| 2 | Vũ Bá Anh | 2A202602893 | Data foundation, RAG và evaluation | `crossref.py`, `cleaning.py`, `retrieval/`, `testset.py`, metrics và raw/clean artifacts |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành pipeline từ ingestion dữ liệu Crossref đến cleaning, data modeling,
embedding, ChromaDB indexing, baseline evaluation và observability. Dữ liệu được chuẩn
hóa với `age_days`, `text_for_embedding` và khử trùng lặp theo `paper_id`. Quality Gate
dùng Great Expectations 1.x với sáu validation results thuộc bốn nhóm expectation bắt
buộc, kết hợp Freshness SLA 180 ngày và ngưỡng stale tối đa 25%.

Baseline tạo 24 clean records, test set 10 câu hỏi thuộc bốn loại, collection
`papers-baseline`, metrics và quality/freshness reports. Corruption flow thực hiện đủ
sáu kịch bản: drop latest records, blank summary, inject noise, truncate title, stale
date và duplicate rows. Hit Rate giảm từ 1.0 xuống 0.9, Token F1 từ 0.5 xuống 0.4.
Repair dựng lại dữ liệu từ raw snapshot, đưa Hit Rate về 1.0 và Token F1 về 0.5.

Giới hạn còn lại là Ragas chưa chạy, chưa có automated test suite, `uv.lock` chưa cập
nhật Streamlit và thông tin submission/GitHub/LMS cần nhóm hoàn thiện thủ công.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API
    -> Raw data
    -> Data cleaning
    -> Embedding và ChromaDB indexing
    -> Baseline evaluation
    -> Quality và Freshness checks
    -> Data corruption
    -> Corrupted evaluation
    -> Repair từ raw data
    -> Re-evaluation
    -> Comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact |
|---|---|---|---|
| Ingestion | Crossref API hoặc snapshot | Fetch, parse, fallback và lưu raw lineage | `data/raw/crossref_response.json`, `crossref_records.json` |
| Cleaning | Raw `PaperRecord` | Normalize, tính tuổi, deduplicate và ghép context | `data/clean/papers_clean.csv/json` |
| Embedding/index | Clean dataframe | `all-MiniLM-L6-v2`, ChromaDB persistent collections | `data/embeddings/`, `papers-baseline` |
| Evaluation | `test_set.json` và index | Retrieval, answer, Hit Rate, Token F1, judge metrics | `data/results/*_metrics.json`, `*_answers.json` |
| Observability | Dataframe các stage | GX 1.x expectations và Freshness SLA | `data/quality/` |
| Corruption/repair | Clean dataframe/raw snapshot | Sáu lỗi có log; rebuild repair từ raw | corrupted/repaired artifacts |
| Orchestration | Settings và artifact paths | Chạy Phase 1 hoặc corruption flow | `phase1_report.md`, `corruption_report.md` |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
|---|---|
| `LLM_PROVIDER` | `openai` |
| `LLM_MODEL` | `gpt-4o-mini` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày; stale ratio tối đa 25% |
| Evaluation set | `data/eval/test_set.json`, 10 câu hỏi dùng chung |

Không đưa API key hoặc nội dung `.env` vào báo cáo.

### Lệnh cài đặt và chạy

```powershell
python -m pip install -r requirements.txt
python script/run_phase1.py
python script/run_corruption_flow.py
streamlit run app.py
```

Trong môi trường không có kết nối Hugging Face nhưng model đã có cache local:

```powershell
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Bằng chứng |
|---|---|---|
| `python script/run_phase1.py` | Thành công | `data/results/baseline_metrics.json`, `phase1_report.md` |
| `python script/run_corruption_flow.py` | Thành công | `corruption_log.json`, corrupted/repaired metrics và report |
| `streamlit run app.py` | Thành công | Dashboard startup trên local Streamlit |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
|---|---|
| Source | Crossref REST API |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:2026-03-30,has-abstract:true` |
| Số record nhận được | 24 |
| Fallback | Đọc local snapshot khi API lỗi/offline hoặc bị rate limit |

### Raw và clean schema

| Trường | Kiểu | Bắt buộc | Ý nghĩa/xử lý |
|---|---|---|---|
| `paper_id` | string | Có | DOI, khóa duy nhất; dòng thiếu bị loại |
| `title` | string | Có | Tiêu đề đã normalize |
| `summary` | string | Có | Abstract đã loại whitespace/XML tag; dùng cho quality |
| `authors`, `categories` | list[string] | Không | Danh sách metadata gốc |
| `authors_joined`, `categories_joined` | string | Có trong clean | Chuỗi phục vụ context/index |
| `published`, `updated` | ISO date/string | Có published | Dùng để tính `age_days` |
| `primary_category`, `abs_url`, `pdf_url`, `comment` | string | Không | Metadata bổ sung |
| `age_days`, `summary_chars` | integer | Có trong clean | Tuổi dữ liệu và độ dài summary |
| `text_for_embedding` | string | Có | Context gồm Title, Authors, Published, Categories, Summary |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Kết quả thực tế | Xác minh |
|---|---|---:|---|
| Bỏ whitespace/XML tag và chuẩn hóa text | Validity/Consistency | 24 dòng sạch | `papers_clean.csv/json` |
| Bỏ record thiếu `paper_id`, `title` hoặc ngày publish hợp lệ | Completeness/Validity | Không làm mất record baseline | `cleaning.py` và row count 24 |
| Tính `age_days` theo run date | Freshness | 0 stale trên baseline | `freshness_report.json` |
| Deduplicate theo `paper_id` | Uniqueness | 24 DOI duy nhất | GX `paper_id_unique` PASS |

Giá trị `text_for_embedding` ghép năm phần: Title, Authors, Published, Categories và
Summary. `paper_id` là DOI dùng làm document identity; `age_days` là số ngày từ ngày
publish đến run date.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
|---|---|
| Số câu hỏi | 10 |
| `question_type` | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID | DOI trong `ground_truth_doc_ids` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store | ChromaDB persistent; `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | OpenAI / `gpt-4o-mini` |
| Test set dùng chung | `data/eval/test_set.json` cho cả ba trạng thái |

Giữ nguyên test set để mọi thay đổi metrics phản ánh trạng thái dữ liệu/index,
không bị trộn với thay đổi câu hỏi hoặc ground truth.

## 7. Kết quả baseline

| Artifact | Đường dẫn | Trạng thái | Ghi chú |
|---|---|---|---|
| Raw response/records | `data/raw/` | Có | 24 records và raw response |
| Cleaned dataset | `data/clean/` | Có | 24 dòng |
| Embedding/index | `data/embeddings/`, `data/chroma/` | Có | Collection baseline có 24 documents |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu hỏi |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Hit Rate, Token F1, judge metrics |
| Quality/freshness | `data/quality/` | Có | GX PASS, FRESH |
| Baseline report | `data/reports/phase1_report.md` | Có | Report tái lập được |

| Metric | Giá trị | Diễn giải |
|---|---:|---|
| `retrieval_hit_rate` | 1.0 | 10/10 câu truy hồi đúng document ID |
| `mean_token_f1` | 0.5 | F1 trung bình giữa câu trả lời và ground truth |
| `judge_accuracy` | 0.5 | Tỷ lệ judge đánh giá câu trả lời đúng |
| `mean_judge_score` | 3.0 | Điểm judge trung bình trên thang 1–5 |
| Ragas | N/A | Được skip nếu không bật `RUN_RAGAS=1` |

## 8. Data quality và freshness

### Quality checks baseline

| Check | Ngưỡng/kỳ vọng | Kết quả | Bằng chứng |
|---|---|---|---|
| Row count | 5–5000 | PASS, 24 | `baseline_quality_report.json` |
| `paper_id` not null | Không null | PASS, 0 unexpected | Cùng report |
| `title` not null | Không null | PASS, 0 unexpected | Cùng report |
| `text_for_embedding` not null | Không null | PASS, 0 unexpected | Cùng report |
| `paper_id` unique | DOI duy nhất | PASS, 0 duplicate | Cùng report |
| `summary` length | Tối thiểu 30 ký tự | PASS | Cùng report |

### Freshness

| Thuộc tính | Giá trị |
|---|---|
| Freshness đo trên | Clean dataframe baseline |
| Latest published | 2026-09-15 |
| Oldest published | 2026-04-01 |
| Ngưỡng | `age_days > 180`, stale ratio tối đa 25% |
| Baseline | FRESH; 0/24 stale, ratio 0.0 |
| Corrupted | FRESH; stale date có trong dữ liệu nhưng ratio dưới 25% |
| Repaired | FRESH; 0/24 stale |

## 9. Corruption scenarios và repair

| Corruption | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
|---|---:|---|---|---|
| Drop latest records | 5 | Giảm row count/index coverage | Corrupted dataset còn 20 dòng | Rebuild từ raw |
| Blank summary | 1 | `summary_length` FAIL | Summary rỗng trong corrupted data | Rebuild summary từ raw |
| Inject noise | 1 | Content consistency giảm | Summary chứa noise marker | Rebuild text từ raw |
| Truncate title | 1 | Title validity giảm | Title bị cắt còn 7 ký tự | Rebuild title từ raw |
| Stale date | 1 | Freshness tăng | Có 1 stale record, vẫn dưới SLA 25% | Rebuild published từ raw |
| Duplicate rows | 1 | `paper_id_unique` FAIL | Output có 20 dòng nhưng 19 DOI duy nhất | Rebuild và deduplicate |

Corruption log nằm tại `data/results/corruption_log.json`, ghi đủ 6 scenario,
paper IDs bị tác động, input rows 24 và output rows 20. Repair không sửa trực tiếp
corrupted file; pipeline gọi `load_raw_records()` rồi chạy lại `build_clean_dataframe()`.
Do đó repair giữ được data lineage và có tính idempotent.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi | Mức phục hồi |
|---|---:|---:|---:|---:|---:|
| `retrieval_hit_rate` | 1.0 | 0.9 | 1.0 | -0.1 | 100% |
| `mean_token_f1` | 0.5 | 0.4 | 0.5 | -0.1 | 100% |
| `judge_accuracy` | 0.5 | 0.4 | 0.5 | -0.1 | 100% |
| `mean_judge_score` | 3.0 | 2.7 | 3.0 | -0.3 | 100% |
| Quality checks | PASS | FAIL | PASS | Fail tại corrupted | PASS trở lại |
| Freshness status | FRESH | FRESH | FRESH | Không vượt SLA | FRESH |

Kết luận nhân quả thứ nhất: blank summary, duplicate rows và các nội dung bị biến đổi
làm corrupted Quality Gate FAIL; cùng lúc việc mất hoặc làm sai context khiến Hit Rate
giảm 10 điểm phần trăm và Token F1 giảm 0.1.

Kết luận nhân quả thứ hai: repair từ raw snapshot khôi phục đủ 24 dòng, rebuild index
và dùng cùng test set; Quality Gate trở lại PASS, Hit Rate và Token F1 trở về baseline.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Lần chạy corruption đầu tiên lỗi khi một trường text rỗng từ CSV
  được đọc thành `NaN` float và truyền vào `normalize_whitespace()`.
- **Nguyên nhân:** CSV parser biểu diễn một số ô text rỗng bằng float `NaN`.
- **Cách xử lý:** Thêm chuẩn hóa an toàn `_clean_text()` trước khi rebuild
  `text_for_embedding` trong `corruption.py`.
- **Cách xác minh:** Chạy lại `python script/run_corruption_flow.py` ở offline mode;
  flow exit code 0 và sinh đủ corrupted/repaired artifacts.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện |
|---|---|---|
| Ragas đang skip | Chưa có các chỉ số faithfulness/context của Ragas | Chạy với `RUN_RAGAS=1` khi có cấu hình LLM phù hợp |
| Chưa có automated test suite | Verification chủ yếu dựa trên script và artifact | Thêm unit/integration tests cho cleaning, corruption và report |

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
