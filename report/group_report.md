# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3B (ca sáng) |
| Tên nhóm | Alone (1 thành viên) |
| Repository | https://github.com/Dang-Huy1910/K4-L3B-DAY10-Alone--DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đặng Quang Huy | 2A202602962 | Toàn bộ pipeline (nhóm 1 người) | `crossref.py`, `cleaning.py`, `corruption.py`, `quality.py`, `testset.py`, `reporting.py`, `phase1.py`, `corruption_flow.py`, artifacts trong `data/` |

## 2. Tóm tắt kết quả

Nhóm 1 người đã hoàn thành end-to-end data pipeline cho RAG: ingest Crossref (24 bài, fallback snapshot local), clean/dedup, embed MiniLM, index ChromaDB, đánh giá 10 câu hỏi, gắn Great Expectations 1.x và Freshness SLA, rồi chạy corruption → repair.

Baseline tạo đủ artifact: raw JSON, `papers_clean.csv/json`, collection `papers-baseline`, `test_set.json`, `baseline_metrics.json`, quality/freshness reports và `phase1_report.md`. Trên dữ liệu sạch, retrieval hit rate = 1.0, mean token F1 = 1.0, GX `success=True`, freshness `is_fresh=True` (1/24 bài `age_days > 180`).

Sáu kịch bản làm bẩn được ghi trong `corruption_log.json`. Tác động rõ nhất lên agent là **drop 20% bản ghi mới nhất**: bốn paper nằm trong test set bị mất khỏi index, hit rate giảm từ 1.0 xuống 0.6. Quality gate cũng fail (duplicate `paper_id`, summary rỗng, title < 8 ký tự) và freshness `is_fresh=False` vì 14/22 dòng bị lùi ngày về 2019.

Repair đọc lại `data/raw/crossref_records.json`, chạy lại cleaning và index collection `papers-repaired`. Hit rate, token F1, judge score, GX và freshness trở về mức baseline. Giới hạn còn lại: Ragas không chạy (`RUN_RAGAS` tắt), LLM judge dùng `mock` nên điểm judge bám heuristic token F1, và token F1 chỉ giảm nhẹ (1.0 → 0.9) vì câu hỏi authors/date/categories trên tài liệu còn lại vẫn trả lời đúng.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API (hoặc snapshot data/raw/crossref_response.json)
    -> parse PaperRecord + data/raw/crossref_records.json
    -> cleaning (dedup, age_days, text_for_embedding 5 phần)
    -> data/clean/papers_clean.csv|json
    -> embedding all-MiniLM-L6-v2 + ChromaDB papers-baseline
    -> test_set.json (10 câu, 4 nhóm)
    -> evaluate: retrieval_hit_rate, mean_token_f1, judge_*
    -> GX 1.x + freshness SLA
    -> corruption (6 kịch bản) -> papers-corrupted -> evaluate
    -> repair từ raw records -> papers-repaired -> evaluate
    -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref API hoặc snapshot | Parse DOI/title/abstract/authors/subject/dates; retry 429/503; fallback local | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Đặng Quang Huy |
| Cleaning | `list[PaperRecord]`, `run_date` | Bỏ JATS, chuẩn hóa text, dedup `paper_id`, `age_days`, 5 phần embed | `data/clean/papers_clean.csv`, `papers_clean.json` | Đặng Quang Huy |
| Embedding/index | Clean dataframe | MiniLM + 3 collection tách biệt | `data/chroma/`, `data/embeddings/*.json` | Đặng Quang Huy |
| Evaluation | Clean df + index | 10 câu, hit rate, token F1, judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | Đặng Quang Huy |
| Observability | Clean/corrupted/repaired df | GX 1.x (4 loại expectation) + freshness 180 ngày / 25% | `data/quality/*.json` | Đặng Quang Huy |
| Corruption/repair | Clean df + raw records | 6 lỗi; repair = `build_clean_dataframe(load_raw_records)` | `corruption_log.json`, clean corrupted/repaired | Đặng Quang Huy |
| Orchestration | Settings + artifact paths | `run_phase1.py` rồi `run_corruption_flow.py` | `phase1_report.md`, `corruption_report.md` | Đặng Quang Huy |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `mock` (judge heuristic khi structured output không dùng được) |
| `LLM_MODEL` | `mock` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày; `is_fresh=False` nếu tỷ lệ stale > 25% |
| `REFRESH_SOURCE` | tắt (dùng snapshot local để tái lập đúng 24 bài) |
| Random seed | không dùng |

Không dán API key hoặc nội dung `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

Với venv đã kích hoạt:

```bash
source .venv/bin/activate
python script/run_phase1.py
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công, exit 0 | 2026-09-26 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`; hit_rate=1.0, GX success=True |
| Corruption flow | Thành công, exit 0 | 2026-09-26 | `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md`; hit_rate 1.0 → 0.6 → 1.0 |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API `https://api.crossref.org/works`, fallback `data/raw/crossref_response.json` |
| Query/filter | query=`agentic retrieval augmented generation large language model`; filter=`from-pub-date:<today-180d>,has-abstract:true`; `rows=24` |
| Thời điểm lấy dữ liệu | Snapshot có sẵn trong repo; phase 1 chạy 2026-09-26T03:54:28Z không gọi API sống vì `REFRESH_SOURCE` tắt |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | 3 lần, ngủ `2**attempt` giây với HTTP 429/500/502/503/504, sau đó đọc snapshot |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | string (DOI) | Có | Định danh tài liệu / Chroma id logic | Bỏ record nếu trống |
| `title` | string | Có | Tiêu đề | Strip JATS/whitespace; bỏ nếu rỗng |
| `summary` | string | Không bắt buộc lúc parse | Abstract đã bỏ XML | Chuẩn hóa; GX yêu cầu độ dài ≥ 20 trên dữ liệu sạch |
| `authors` / `authors_joined` | list / string | Không | Tác giả | Ghép bằng `", "` |
| `categories` / `categories_joined` | list / string | Không | Subject Crossref | Mặc định `Uncategorized` nếu trống |
| `published` | `YYYY-MM-DD` | Có để tính tuổi | Ngày xuất bản | Parse `date-parts`; dùng để tính `age_days` |
| `age_days` | int | Có sau clean | `(run_date - published).days` | Phục vụ Freshness SLA |
| `text_for_embedding` | string | Có | 5 phần embed | Rebuild sau clean và sau corruption |
| `abs_url` / `pdf_url` | string | Không | Liên kết DOI | Fallback `https://doi.org/{paper_id}` |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| --- | --- | --- | --- |
| Loại record không có `paper_id` hoặc `title` | Completeness | 0 trên snapshot 24 bài | `len(df)==24` |
| Dedup theo `paper_id`, giữ bản published mới hơn | Uniqueness | 0 trùng trên snapshot | GX `ExpectColumnValuesToBeUnique` trên `paper_id` |
| Bỏ JATS/XML và gom whitespace | Validity | Toàn bộ abstract có `<jats:p>` | Summary trong clean JSON không còn tag |
| Tính `age_days` theo `run_date` UTC | Timeliness | 24/24 | `data/quality/freshness_report.json` |

`paper_id` lấy từ DOI Crossref và giữ nguyên qua clean/index/eval. `age_days = (run_date - published).days`. `text_for_embedding` gồm đúng 5 phần:

```text
Title: ...
Authors: ...
Categories: ...
Published: ...
Summary: ...
```

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10 |
| Các `question_type` | summary (3), authors (3), date (2), categories (2) |
| Ground-truth document ID | `paper_id` của đúng bài được hỏi; câu hỏi bọc title trong dấu nháy đơn để QA có thể exact-lookup |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | Chroma persistent `data/chroma/`; `papers-baseline` / `papers-corrupted` / `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | `mock` / `mock`; judge fallback theo token F1 |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

Test set được sinh một lần từ dataframe sạch rồi tái sử dụng cho corrupted và repaired. Nếu mỗi trạng thái tự sinh câu hỏi mới, hit rate không còn so sánh được vì ground-truth document và wording đã đổi.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/crossref_response.json`, `crossref_records.json` | Có | 24 items |
| Cleaned dataset | `data/clean/papers_clean.csv`, `papers_clean.json` | Có | 24 dòng, có `text_for_embedding` |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | Collection `papers-baseline` |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | hit_rate=1.0 |
| Quality/freshness | `data/quality/baseline_quality_report.json`, `freshness_report.json` | Có | GX 6/6 pass |
| Baseline report | `data/reports/phase1_report.md` | Có | Sinh từ pipeline |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0 | 10/10 câu retrieve đúng `paper_id` ground truth |
| `mean_token_f1` | 1.0 | Câu trả lời extractive khớp authors/date/categories/first sentence |
| `judge_accuracy` | 1.0 | Heuristic judge: F1 ≥ 0.5 được tính correct |
| `mean_judge_score` | 5.0 | F1 ≥ 0.95 → score 5 |
| Ragas | N/A | `RUN_RAGAS` không bật; file metrics ghi `skipped` |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `ExpectTableRowCountToBeBetween` | Completeness | 20–30 dòng | Pass, observed=24 | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`paper_id`, `title`) | Completeness | 0 null | Pass | cùng file |
| `ExpectColumnValuesToBeUnique` (`paper_id`) | Uniqueness | 0 trùng | Pass | cùng file |
| `ExpectColumnValueLengthsToBeBetween` (`summary` 20–20000, `title` 8–500) | Validity | Mọi dòng trong ngưỡng | Pass | 6/6 expectation, `success_percent=100` |

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | Clean dataframe, cột `age_days` |
| Timestamp mới nhất | `2026-07-22` |
| Timestamp cũ nhất | `2026-03-28` |
| Ngưỡng freshness | `age_days > 180`; tỷ lệ stale > 25% ⇒ `is_fresh=False` |
| Trạng thái baseline | Fresh (`is_fresh=True`) |
| Lý do | 1/24 dòng stale (tỷ lệ 0.0417 < 0.25), xem `data/quality/freshness_report.json` |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| Drop latest 20% | Xóa 5 paper published mới nhất | 5 | Thiếu document serving | 4/10 câu test mất ground-truth doc; hit rate 0.6 | Load raw records, clean lại |
| Blank summary | Gán `summary=""` 4 dòng | 4 | GX summary length fail | Summary rỗng, embedding mất abstract | Rebuild từ raw |
| Inject noise | Ghép token rác vào summary | 4 | Drift embedding | Làm bẩn `text_for_embedding` | Rebuild từ raw |
| Truncate title | Cắt title còn 7 ký tự | 4 | GX title length fail; vỡ exact lookup | Title < 8 ký tự | Rebuild từ raw |
| Stale date | `published=2019-01-01` trên 10 dòng | 10 | Freshness fail | 14/22 stale (do trùng dòng), `is_fresh=False` | Rebuild từ raw |
| Duplicate rows | Nhân 3 dòng đầu | 3 | GX unique `paper_id` fail | `paper_id` trùng, GX success=False | Rebuild từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Đủ 6 scenario, có `paper_ids`, `count`, `row_count_before=24`, `row_count_after=22`

Repair không vá từng ô trên dataframe bẩn. `corruption_flow.py` gọi `load_raw_records(raw_records_json)` rồi `build_clean_dataframe` — cùng hàm cleaning của phase 1 — nên kết quả idempotent với baseline.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0 | 0.6 | 1.0 | −0.4 | +0.4 | Drop latest làm mất 4 ground-truth doc trong test set |
| `mean_token_f1` | 1.0 | 0.9 | 1.0 | −0.1 | +0.1 | Câu authors/date trên tài liệu còn lại vẫn extract đúng |
| `judge_accuracy` | 1.0 | 0.9 | 1.0 | −0.1 | +0.1 | Bám token F1 vì LLM mock |
| `mean_judge_score` | 5.0 | 4.6 | 5.0 | −0.4 | +0.4 | Phục hồi đầy đủ sau repair |
| Quality checks | Pass (6/6) | Fail (3/6) | Pass (6/6) | Gate báo bẩn | Phục hồi | Duplicate + summary ngắn + title ngắn |
| Freshness status | True (1/24) | False (14/22) | True (1/24) | Stale date | Phục hồi | SLA 25% bị vượt (0.6364) |

Hai kết luận nhân quả:

1. Drop 5 paper mới nhất, trong đó 4 paper thuộc `test_set.json` (1802, 1804, 1807, 1808) → retrieval không còn ground-truth doc → `retrieval_hit_rate` 1.0 → 0.6. Agent vẫn trả lời, không crash: silent failure.
2. Repair từ `crossref_records.json` → GX 6/6 pass, `is_fresh=True`, collection `papers-repaired` index đủ 24 doc → hit rate và token F1 trở lại 1.0.

Token F1 giảm ít hơn hit rate là đúng với thiết kế extractive QA: khi document còn trong index, câu hỏi authors/date/categories không cần summary.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Great Expectations 0.x (`get_validator`, `expect_*` kiểu cũ) không còn là API được lab yêu cầu; gọi sai sẽ crash hoặc bị trừ điểm.
- **Nguyên nhân:** Lab chốt GX 1.x: ephemeral context, pandas dataframe asset, `batch.validate(suite)`.
- **Cách xử lý:** `quality.py` dùng `gx.get_context(mode="ephemeral")`, `add_pandas` / `add_dataframe_asset` / `add_batch_definition_whole_dataframe`, rồi gắn `ExpectTableRowCountToBeBetween`, `ExpectColumnValuesToNotBeNull`, `ExpectColumnValuesToBeUnique`, `ExpectColumnValueLengthsToBeBetween`. Cột list được stringify trước khi validate.
- **Cách xác minh:** `run_data_quality_checks(df, s, 'test')` in `Quality check status = True` trên clean data; corrupted report `success=false`, `unsuccessful_expectations=3`.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| LLM judge = mock/heuristic | `judge_*` gần như lặp lại token F1 | Chạy lại với Gemini/OpenAI và so `mean_judge_score` trên cùng `test_set.json` |
| Ragas tắt | Thiếu faithfulness/context precision | `RUN_RAGAS=1` trên 10 câu, ghi thêm vào metrics |
| Token F1 giảm ít | Người đọc có thể nghĩ corruption “nhẹ” | Thêm câu hỏi summary cho đúng những paper bị blank/drop |
| Chưa tự kích hoạt repair khi GX fail | Repair vẫn do `run_corruption_flow.py` gọi chủ động | Nếu `success=False` thì tự `load_raw_records` + reindex (bonus self-healing) |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế (1 thành viên làm toàn bộ).
- [x] Lệnh tái hiện đã chạy: `uv run python script/run_phase1.py` và `run_corruption_flow.py` exit 0.
- [x] Baseline, corrupted và repaired dùng cùng `data/eval/test_set.json`.
- [x] Bảng metrics khớp `data/results/*_metrics.json`.
- [x] Quality/freshness khớp `data/quality/`.
- [x] Đường dẫn artifact truy cập được.
- [x] Báo cáo vai trò: `report/individual_report.md` và `report/2A202602962_DangQuangHuy.md`.
- [x] Không nhúng `.env`, API key, token hoặc secret.
