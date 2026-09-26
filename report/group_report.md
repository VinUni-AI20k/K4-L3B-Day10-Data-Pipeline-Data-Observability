# Báo cáo nhóm — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | 4aesieunhan |
| Repository | https://github.com/TuTu99999/K4-L3B-DAY10-4aesieunhan-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Phạm Khắc Tú | 2A202602866 | Ingestion, benchmark và baseline integration | `crossref.py`, `testset.py`, `phase1.py`, baseline reporting |
| 2 | Trần Tuấn Hoàng | 2A202602832 | Cleaning và data observability | `cleaning.py`, `quality.py`, clean/quality artifacts |
| 3 | Thân Thị Kim Chi | 2A202602797 | Corruption, repair và Phase 2 integration | `corruption.py`, `corruption_flow.py`, three-state reporting |

Phạm Khắc Tú đồng thời kiểm tra tích hợp cuối, xử lý encoding Windows và kết nối QA/LLM judge với custom provider qua `.env`.

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành pipeline từ thu thập Crossref, bảo toàn raw snapshot, làm sạch 24 bản ghi, tạo embedding MiniLM và index ChromaDB đến sinh bộ benchmark 10 câu hỏi, đánh giá baseline, kiểm soát chất lượng và giám sát freshness. Baseline đạt retrieval hit rate `1.0000`, mean token F1 `1.0000`, judge accuracy `1.0000`; quality gate và freshness đều PASS. Nhóm tiếp tục tiêm đủ sáu dạng lỗi dữ liệu. Tập corrupted còn 22 dòng, có hai DOI bị nhân đôi, hai summary trống và tỷ lệ stale tăng lên `31,82%`. Great Expectations và Freshness SLA chuyển sang FAIL, trong khi pipeline vẫn chạy, qua đó thể hiện silent failure. Hiệu năng giảm còn hit rate `0.8000`, Token F1 `0.7720`, judge accuracy `0.8000` và mean judge score `4.1000`. Repair dựng lại 24 dòng từ raw snapshot, đưa toàn bộ quality signal và metrics về mức baseline. Lần chạy cuối sử dụng 9Router model `cx/gpt-5.6-luna` qua `.env` cho QA và judge; cả ba tập có `0` heuristic fallback. Giới hạn chính là benchmark còn nhỏ, câu hỏi chứa nguyên tiêu đề nên exact lookup tương đối dễ, và Ragas chưa được bật.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API / raw snapshot
    -> raw response + PaperRecord
    -> cleaning, deduplication, age_days, text_for_embedding
    -> Great Expectations gate + freshness SLA
    -> MiniLM embedding + ChromaDB baseline index
    -> fixed 10-question benchmark
    -> baseline QA/evaluation
    -> six controlled corruptions
    -> corrupted quality check, re-index and evaluation
    -> repair from immutable raw snapshot
    -> repaired quality check, re-index and evaluation
    -> Baseline / Corrupted / Repaired comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref payload hoặc snapshot | Fetch, retry/backoff, fallback, parse và chuẩn hóa | `data/raw/crossref_response.json`, `crossref_records.json` | Phạm Khắc Tú |
| Cleaning | `PaperRecord` | Chuẩn hóa text/date, tính `age_days`, deduplicate, ghép embedding text | `data/clean/papers_clean.*` | Trần Tuấn Hoàng |
| Embedding/index | Clean/corrupted/repaired DataFrame | MiniLM embedding và ba Chroma collection | `data/embeddings/`, `data/chroma/` | Tú tích hợp baseline; Chi tích hợp Phase 2 |
| Evaluation | Index và test set cố định | QA qua 9Router, Hit Rate, Token F1 và LLM judge | `data/results/*_answers.json`, `*_metrics.json` | Phạm Khắc Tú |
| Observability | DataFrame từng trạng thái | GX 1.x và freshness SLA | `data/quality/` | Trần Tuấn Hoàng |
| Corruption/repair | Clean data và raw snapshot | Tiêm 6 lỗi, rebuild từ raw snapshot | Corruption log, corrupted/repaired datasets | Thân Thị Kim Chi |
| Orchestration/reporting | Toàn bộ module và artifacts | Chạy đúng thứ tự, dừng ở gate cần thiết, xuất Markdown | `data/reports/phase1_report.md`, `corruption_report.md` | Tú (Phase 1), Chi (Phase 2) |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| Python | 3.12.10 |
| `LLM_PROVIDER` | `custom` |
| `LLM_MODEL` | `cx/gpt-5.6-luna` |
| LLM gateway | OpenAI-compatible 9Router, cấu hình bằng `CUSTOM_LLM_BASE_URL` trong `.env` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | `age_days > 180`; cảnh báo khi stale ratio `> 0.25` |
| Chọn test set | Deterministic, không dùng random seed |

API key chỉ nằm trong `.env`, không xuất hiện trong source, report hoặc artifact được commit.

### Lệnh cài đặt và chạy

```powershell
python -m pip install -e .
python script/run_phase1.py
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| `python script/run_phase1.py` | Thành công | 2026-09-26 | 24 clean records, 10 benchmark questions, baseline report |
| `python script/run_corruption_flow.py` | Thành công | 2026-09-26 | Bảng ba trạng thái trên console và `corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | `https://api.crossref.org/works` hoặc local snapshot |
| Query | `agentic retrieval augmented generation large language model` |
| Filter của lần chạy | `from-pub-date:2026-03-30,has-abstract:true` |
| Số record | 24 |
| Retry/backoff | Retry HTTP 429/500/502/503/504, dùng `Retry-After` hoặc exponential backoff, tối đa 10 giây |
| Offline fallback | Đọc `data/raw/crossref_response.json` khi API/mạng thất bại |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | string | Có | DOI, khóa duy nhất | Bỏ record thiếu DOI; deduplicate |
| `title` | string | Có | Tiêu đề bài báo | Chuẩn hóa khoảng trắng; bỏ record thiếu title |
| `summary` | string | Có cho quality gate | Abstract đã bỏ HTML/JATS | Chuẩn hóa; GX yêu cầu tối thiểu 30 ký tự |
| `authors` / `authors_joined` | list/string | Có cho benchmark authors | Danh sách tác giả | Ghép `given` và `family`, loại phần rỗng |
| `categories` / `categories_joined` | list/string | Có cho benchmark categories | Chủ đề Crossref | Chuẩn hóa và nối bằng dấu phẩy |
| `published` | string `YYYY-MM-DD` | Có | Ngày xuất bản | Chuẩn hóa từ `date-parts` |
| `age_days` | integer | Có | Tuổi dữ liệu tại thời điểm chạy | Tính từ `run_date - published` |
| `text_for_embedding` | string | Có | Context năm phần cho embedding | Dựng lại sau mọi thay đổi dữ liệu |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Bỏ HTML/JATS và chuẩn hóa whitespace | Validity/Consistency | Áp dụng trên toàn corpus | So sánh raw abstract và clean summary |
| Chuẩn hóa ngày, tính `age_days` | Timeliness | 24 | Cột `published`, `age_days` trong clean JSON |
| Deduplicate theo `paper_id` | Uniqueness | 0 duplicate trong snapshot hiện tại | 24 raw → 24 clean; GX unique PASS |
| Ghép `text_for_embedding` năm phần | Completeness | 24 | Kiểm tra các nhãn Title/Authors/Published/Categories/Summary |

`paper_id` được giữ nguyên từ DOI để liên kết raw, clean, vector index và ground truth. `text_for_embedding` có cùng cấu trúc ở cả ba trạng thái và được dựng lại sau corruption để vector phản ánh đúng dữ liệu đang đánh giá.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10 |
| `question_type` | 3 summary, 3 authors, 2 date, 2 categories |
| Ground-truth document ID | DOI trong `ground_truth_doc_ids` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store | ChromaDB: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | `custom` / `cx/gpt-5.6-luna` qua 9Router |
| Test set dùng chung | `data/eval/test_set.json` |

Cùng một test set được dùng cho ba trạng thái để mọi thay đổi metric đến từ dữ liệu/index. QA lấy context từ tài liệu retrieved và gọi 9Router để sinh đáp án. Judge cũng gọi cùng provider, nhưng bằng prompt đánh giá riêng; lần chạy cuối không có heuristic fallback.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | 24 records |
| Cleaned dataset | `data/clean/papers_clean.*` | Có | 24 dòng |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/` | Có | MiniLM + ChromaDB |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu |
| Baseline metrics/answers | `data/results/baseline_*.json` | Có | 10 answers, 0 fallback |
| Quality/freshness | `data/quality/` | Có | Baseline PASS |
| Baseline report | `data/reports/phase1_report.md` | Có | Khớp metrics hiện tại |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | DOI ground truth nằm trong top-4 của cả 10 câu |
| `mean_token_f1` | 1.0000 | Model tuân thủ prompt và trả đúng trường metadata chuẩn |
| `judge_accuracy` | 1.0000 | 9Router judge đánh giá đúng cả 10 câu |
| `mean_judge_score` | 5.0000 | Điểm trung bình tối đa trên baseline |
| Ragas | N/A | Chưa bật `RUN_RAGAS=1` |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| Row count | Volume | 5–5000 | PASS, 24 | `baseline_quality_report.json` |
| Non-null `paper_id`, `title`, `text_for_embedding` | Completeness | 0 null | PASS | Cùng report |
| Unique `paper_id` | Uniqueness | 0 duplicate | PASS | Cùng report |
| Summary length | Validity | Tối thiểu 30 ký tự | PASS, 0 unexpected | Cùng report |

Ba expectation non-null được tính riêng nên report có tổng cộng 6 expectation instances.

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness đo tại | Clean DataFrame trước indexing |
| Ngày xuất bản mới nhất | 2026-07-22 |
| Ngày xuất bản cũ nhất | 2026-03-28 |
| Ngưỡng stale | `age_days > 180` |
| Baseline | Fresh: 1/24 stale, tỷ lệ `0.0417` |
| Giới hạn tỷ lệ stale | `0.25` |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Signal/tác động thực tế | Repair |
| --- | --- | ---: | --- | --- |
| Drop latest | Bỏ 4 record mới nhất theo `published` | 4 | Retrieval hit giảm còn 0.8 | Dựng lại từ raw snapshot |
| Blank summary | Gán summary rỗng | 2 | Summary-length expectation FAIL | Dựng lại summary từ raw |
| Inject noise | Nối payload nhiễu vào summary | 2 | Làm thay đổi context/embedding | Dựng lại summary từ raw |
| Truncate title | Đổi title thành `Draft` | 2 | Làm giảm chất lượng nhận dạng/ngữ cảnh | Dựng lại title từ raw |
| Stale date | Lùi `published` 365 ngày | 6 | Stale ratio tăng lên 31,82%, SLA FAIL | Tính lại từ raw date |
| Duplicate rows | Nhân đôi hai dòng | 2 dòng thêm | Unique expectation FAIL, 4 occurrences unexpected | Deduplicate khi rebuild clean data |

`data/results/corruption_log.json` có đủ sáu nhóm lỗi, số lượng và `paper_id` bị tác động. Tập corrupted có 22 dòng vì `24 - 4 + 2 = 22`.

Repair không sửa trực tiếp các giá trị bẩn. `repair_from_raw_snapshot()` đọc lại `data/raw/crossref_records.json`, chạy lại toàn bộ cleaning contract và ghi dataset repaired mới. Vì raw snapshot không bị mutation, cơ chế này có thể chạy lặp lại và không phụ thuộc Crossref API.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 1.0000 | -0.2000 | 100% | Hai câu không còn tìm đúng DOI sau corruption |
| `mean_token_f1` | 1.0000 | 0.7720 | 1.0000 | -0.2280 | 100% | Nội dung mất/nhiễu làm câu trả lời lệch reference |
| `judge_accuracy` | 1.0000 | 0.8000 | 1.0000 | -0.2000 | 100% | Judge thật qua 9Router, 0 heuristic fallback |
| `mean_judge_score` | 5.0000 | 4.1000 | 5.0000 | -0.9000 | 100% | Chất lượng ngữ nghĩa giảm rồi phục hồi |
| Quality gate | PASS | FAIL | PASS | FAIL do duplicate/summary | Hoàn toàn | GX chặn dữ liệu bẩn |
| Freshness | PASS | FAIL | PASS | 4,17% → 31,82% stale | Hoàn toàn | Repair đưa tỷ lệ về 4,17% |

Hai chuỗi nguyên nhân–bằng chứng:

1. Drop latest, blank summary và duplicate rows làm thay đổi corpus → GX unique/summary checks FAIL và retrieval mất ground-truth documents → hit rate giảm 20%, Token F1 giảm 22,8%.
2. Stale-date corruption làm stale ratio vượt 25% → Freshness SLA phát cảnh báo dù pipeline không crash. Repair từ raw snapshot khôi phục schema/date/content → quality, freshness và toàn bộ metrics trở về baseline.

Kết quả là tác động tổng hợp của sáu corruption. Nhóm chưa chạy ablation riêng nên không gán toàn bộ mức giảm cho một loại lỗi duy nhất.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng 1:** `python script/run_corruption_flow.py` lỗi `UnicodeEncodeError` khi in tiếng Việt trên PowerShell dùng `cp1252`.
- **Nguyên nhân:** Entry point không cấu hình encoding cho `stdout/stderr`.
- **Cách xử lý:** Reconfigure hai stream sang UTF-8 trong script wrapper.
- **Xác minh:** Pipeline chạy mã thoát `0` và in đầy đủ bảng ba trạng thái.

- **Triệu chứng 2:** 9Router gọi được nhưng toàn bộ judge âm thầm rơi vào heuristic.
- **Nguyên nhân:** Model trả dạng `Score/Correct/Reasoning`, không phải JSON mà `with_structured_output()` yêu cầu.
- **Cách xử lý:** Với custom provider, gọi LLM qua cấu hình `.env` và parse cả JSON lẫn dạng nhãn; QA cũng sinh đáp án từ retrieved context qua LLM.
- **Xác minh:** `fallbacks=0` trên 10 baseline, 10 corrupted và 10 repaired answers; judge reasoning đến từ model.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Chỉ có 10 câu và câu hỏi chứa nguyên tiêu đề | Exact lookup dễ, baseline đạt điểm tuyệt đối | Thêm câu paraphrase không chứa nguyên tiêu đề và đo hit rate theo từng nhóm |
| Chưa bật Ragas | Chưa có faithfulness/context precision/recall | Bật `RUN_RAGAS=1`, lưu artifact và so sánh ba trạng thái |
| Chưa có ablation cho từng corruption | Không định lượng riêng tác động của từng lỗi | Chạy từng corruption độc lập với cùng test set |
| Custom gateway có thể trả nhiều định dạng | Structured output thiếu ổn định | Thêm contract test cho JSON, labelled text và malformed response |
| HF cache báo warning quyền ghi metadata phụ | Log nhiễu, có thể làm lần tải sau chậm | Cấu hình cache vào thư mục người dùng có quyền ghi và chạy lại cold-start test |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, commit và artifact thực tế.
- [x] Baseline và corruption flow đã được chạy lại trên phiên bản hiện tại.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact tồn tại.
- [x] Mỗi thành viên có báo cáo cá nhân riêng.
- [x] Report không chứa `.env`, API key, token hoặc secret.
