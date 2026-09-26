# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đặng Quang Huy |
| MSSV | 2A202602962 |
| Khóa/Lớp | K4-L3B (ca sáng) |
| Tên nhóm | Alone |
| Vai trò chính | Thành viên duy nhất — sở hữu toàn bộ pipeline |
| Repository | https://github.com/Dang-Huy1910/K4-L3B-DAY10-Alone--DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

Vì nhóm 1 người, tôi nhận toàn bộ deliverable. Không có thành viên khác để bàn giao ngang hàng.

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Raw ingestion | `src/ingestion/crossref.py` — `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | Crossref API hoặc snapshot | 24 `PaperRecord`; 2 file raw JSON | Hoàn thành |
| Cleaning | `src/ingestion/cleaning.py` — `build_clean_dataframe`, `compose_text_for_embedding` | Raw records + `run_date` | Clean CSV/JSON, `age_days`, embed text 5 phần | Hoàn thành |
| Evaluation set | `src/evaluation/testset.py` — `build_test_set` | Clean dataframe | 10 câu trong `data/eval/test_set.json` | Hoàn thành |
| Quality + freshness | `src/observability/quality.py` | Dataframe từng trạng thái | GX reports + freshness JSON | Hoàn thành |
| Reporting | `src/observability/reporting.py` | Metrics + quality payloads | `phase1_report.md`, `corruption_report.md` | Hoàn thành |
| Baseline orchestration | `src/pipelines/phase1.py`, `script/run_phase1.py` | Settings | Baseline metrics, index, demo answers | Hoàn thành |
| Corruption + repair | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py` | Clean df + raw records | Log 6 lỗi, corrupted/repaired metrics | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Không có thành viên khác | — | Tự chạy lại hai script orchestration và đối chiếu artifact với số liệu trong báo cáo nhóm |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Fetch/parse 24 paper | `crossref.py`, `data/raw/` | 24 records | In `Đã tải 24 bài báo` |
| Clean dataframe | `cleaning.py`, `data/clean/` | 24 dòng có `text_for_embedding` | In `Clean thành công 24 dòng` |
| GX 1.x + freshness | `quality.py`, `data/quality/` | Baseline GX success=True, stale 1/24 | `Quality check status = True` |
| Test set 10 câu | `testset.py`, `data/eval/test_set.json` | 4 nhóm câu hỏi | `Sinh được 10 câu hỏi test` |
| Phase 1 | `run_phase1.py` | hit_rate=1.0, F1=1.0 | `data/results/baseline_metrics.json` |
| Corruption + repair | `run_corruption_flow.py` | hit_rate 0.6 rồi 1.0; GX False rồi True | `corruption_report.md` |

Output cụ thể tôi dùng để kết luận: bảng 3 trạng thái trong `data/reports/corruption_report.md` khớp `baseline_metrics.json` / `corrupted_metrics.json` / `repaired_metrics.json` — hit rate 1.0 / 0.6 / 1.0.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

RAG vẫn trả lời khi dữ liệu bẩn. Cần một pipeline có lineage (raw → clean → index), có cổng chất lượng (GX + freshness), đo được suy giảm khi tiêm lỗi, và phục hồi được từ snapshot gốc.

### Cách triển khai

1. `fetch_source_records` ưu tiên snapshot khi `REFRESH_SOURCE` tắt để lab tái lập đúng 24 bài; nếu bật refresh thì gọi API, retry backoff, fallback local khi 429/mất mạng.
2. Cleaning bỏ XML JATS, dedup DOI, tính `age_days`, dựng `text_for_embedding` 5 phần (title, authors, categories, published, summary).
3. Quality dùng GX 1.x ephemeral pandas batch, không dùng validator 0.x. Freshness: tỷ lệ `age_days > 180` > 25% thì `is_fresh=False`.
4. Test set cố định 10 câu, title trong dấu nháy đơn để `qa.py` exact-lookup được.
5. Ba collection Chroma tách biệt để so sánh công bằng.
6. Corruption gồm 6 lỗi; repair gọi lại cleaning từ `crossref_records.json`, không edit dataframe bẩn.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref payload hoặc list record; `Settings` từ `core/config.py` |
| Output | Clean dataframe, 3 index, metrics JSON, markdown reports |
| Module phụ thuộc | `core.utils` (I/O), `retrieval.index` / `evaluation.metrics` (đã có sẵn trong starter) |
| Module sử dụng output | `phase1.py` và `corruption_flow.py` |
| Điều kiện lỗi cần xử lý | API 429/503, snapshot thiếu, dataframe rỗng, GX fail trên data bẩn |

### Cách xác minh

```bash
uv sync
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Phase 1 24 dòng, GX True, 10 câu test, hit_rate baseline = 1.0. Corruption flow in bảng 3 cột, GX corrupted = False, repaired = True.
- **Kết quả thực tế:** Đúng như trên. Hit rate 1.0000 / 0.6000 / 1.0000. Freshness True / False / True.
- **Artifact/log:** `data/results/*_metrics.json`, `data/results/corruption_log.json`, `data/quality/*`, `data/reports/*.md`. Không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Live Crossref có thể trả bộ 24 bài khác snapshot, làm vỡ test set và freshness.
- **Các phương án đã cân nhắc:** Luôn gọi API; hoặc mặc định đọc snapshot, chỉ refresh khi `REFRESH_SOURCE=1`.
- **Phương án đã chọn:** Mặc định snapshot local, API là đường phụ có retry + fallback.
- **Lý do:** Lab cần số liệu tái lập được. Snapshot đã có 24 abstract/DOI ổn định. Gọi API sống chỉ khi cần dữ liệu mới.
- **Bằng chứng:** `fetch_source_records` trả đúng 24 bài offline; baseline và repaired trùng hit rate 1.0 trên cùng `test_set.json`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** CUDA warning `The NVIDIA driver on your system is too old (found version 12020)` khi load `sentence-transformers`.
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_phase1.py`
- **Nguyên nhân gốc:** Torch GPU build không khớp driver; embedding vẫn chạy CPU.
- **Cách xử lý:** Không chặn pipeline. MiniLM encode trên CPU. Không đưa secret hay path tuyệt đối vào code.
- **Cách xác minh sau khi sửa:** Phase 1 và corruption flow đều exit 0, index 3 collection trong `data/chroma/`.
- **Điều học được:** Observability của môi trường chạy (GPU/CPU) khác data observability; pipeline serving vẫn phải ra artifact khi GPU không dùng được.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. Crossref payload được parse thành `PaperRecord`, ghi raw JSON, clean thành dataframe (DOI, `age_days`, `text_for_embedding`), embed MiniLM, upsert Chroma theo `paper_id`.
2. `build_test_set` chọn 10 paper, gán `ground_truth_doc_ids=[paper_id]`. Retrieval hit khi `paper_id` nằm trong `top_k`. Token F1 so answer với ground truth (authors_joined / published / categories_joined / first sentence).
3. Quality (GX) kiểm schema/tính đầy đủ/duy nhất/độ dài trên batch hiện tại. Freshness chỉ nhìn phân bố `age_days` so với SLA 180 ngày / 25%. GX có thể pass trong khi freshness fail, và ngược lại.
4. Cùng `test_set.json` để delta hit rate/F1 chỉ phản ánh dữ liệu/index, không phản ánh việc đổi câu hỏi.
5. Repair thành công khi repaired GX `success=True`, `is_fresh=True`, 24 dòng, và `retrieval_hit_rate`/`mean_token_f1` trở lại bằng baseline trên cùng test set. Artifact: `papers_clean_repaired.json`, `repaired_metrics.json`, collection `papers-repaired`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0 | 0.6 | 1.0 | Tín hiệu rõ nhất: mất document trong test set |
| `mean_token_f1` | 1.0 | 0.9 | 1.0 | Giảm nhẹ vì QA extractive vẫn đúng trên doc còn lại |
| `judge_accuracy` | 1.0 | 0.9 | 1.0 | Bám F1 do mock judge |
| `mean_judge_score` | 5.0 | 4.6 | 5.0 | Phục hồi đủ sau repair |
| Quality checks | Pass 6/6 | Fail 3/6 | Pass 6/6 | Gate bắt duplicate, summary rỗng, title ngắn |
| Freshness status | True (1/24) | False (14/22) | True (1/24) | Stale date đẩy tỷ lệ stale lên 0.6364 |

### Kết luận từ số liệu

1. Drop latest 20% (5 DOI, trong đó 1802/1804/1807/1808 nằm trong test set) → index thiếu ground-truth → hit rate 1.0 → 0.6; đồng thời GX fail và freshness fail vì duplicate/stale/blank.
2. Repair từ `data/raw/crossref_records.json` → clean 24 dòng, GX 6/6, freshness 1/24 stale → hit rate và F1 = 1.0 trở lại.

Corruption ảnh hưởng rõ nhất tới agent là **drop latest records**, vì nó xóa đúng document mà câu hỏi đang chấm. Truncate title và blank summary chủ yếu đánh GX/exact-lookup; stale date đánh freshness hơn là token F1.

Khác kỳ vọng: tôi tưởng token F1 sẽ rơi mạnh như hit rate. Thực tế 1.0 → 0.9 vì `_extract_answer` vẫn trả authors/date/categories nếu retrieval còn bám được paper khác hoặc paper chưa bị blank. Đã đối chiếu `corruption_log.json` với `test_set.json` để giải thích 4/10 miss.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot là nguồn sự thật; repair phải chạy lại transform từ raw, không patch dữ liệu bẩn.
2. GX 1.x + freshness bắt được lỗi trước serving, ngay cả khi RAG không exception.
3. Dữ liệu thiếu (drop) hại retrieval hơn nhiễu text nhẹ, nếu evaluation set bám document ID.

### Nếu có thêm thời gian

Gắn self-healing: nếu `run_data_quality_checks` trả `success=False` hoặc `is_fresh=False` thì tự repair và reindex. Đo bằng việc chỉ chạy phase 1 trên data bẩn và kiểm tra collection repaired xuất hiện mà không gọi tay `run_corruption_flow.py`.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end.
- [x] Mọi kết luận có artifact hoặc metric để đối chiếu.
- [x] Không ghi “đã chạy thành công” cho phần chưa kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm; báo cáo nhóm tập trung evidence chung, báo cáo này tập trung quyết định và phần việc cá nhân.

**Họ và tên:** Đặng Quang Huy
**Ngày xác nhận:** 2026-09-26
