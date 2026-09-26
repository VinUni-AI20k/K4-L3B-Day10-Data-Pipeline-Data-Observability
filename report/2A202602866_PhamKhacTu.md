# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phạm Khắc Tú |
| MSSV | 2A202602866 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | 4aesieunhan |
| Vai trò chính | Data ingestion, benchmark evaluation và baseline pipeline integration |
| Repository | https://github.com/TuTu99999/K4-L3B-DAY10-4aesieunhan-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Bước 2 — Crossref ingestion | `src/ingestion/crossref.py`: `parse_crossref_payload()`, `fetch_source_records()`, `load_raw_records()` | Crossref payload hoặc raw snapshot | 24 `PaperRecord`, raw response và parsed records | Hoàn thành |
| Bước 5 — Benchmark test set | `src/evaluation/testset.py`: `build_test_set()` | Clean DataFrame | `data/eval/test_set.json` gồm 10 câu hỏi | Hoàn thành |
| Bước 6 — Baseline orchestration | `src/pipelines/phase1.py`: `run_phase1_pipeline()` | Settings và các module ingestion, cleaning, retrieval, evaluation, quality | Toàn bộ baseline artifacts và metrics | Hoàn thành |
| Baseline reporting | `src/observability/reporting.py`: `generate_phase1_report()` | Source summary, metrics, quality và freshness | `data/reports/phase1_report.md` | Hoàn thành |

Các thay đổi chính của tôi được ghi nhận trong commit `d8b192c` (`feat: complete ingestion benchmark and baseline pipeline`).

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| --- | --- | --- |
| Kiểm tra Bước 3 và Bước 4 | Module cleaning và quality của Trần Tuấn Hoàng | Xác nhận clean được 24 dòng; quality gate và freshness baseline đều PASS |
| Kiểm tra Bước 7 và Bước 8 | Module corruption/repair của Thân Thị Kim Chi | Xác nhận đủ 6 loại corruption; Phase 2 tạo bảng Baseline–Corrupted–Repaired và report thành công |
| Kiểm tra tích hợp trên Windows | `script/run_corruption_flow.py` | Phát hiện và xử lý lỗi `UnicodeEncodeError` khi PowerShell dùng mã hóa `cp1252` |
| Tích hợp 9Router vào evaluation | `src/retrieval/qa.py`, `src/evaluation/metrics.py` | QA và LLM judge gọi model `cx/gpt-5.6-luna` qua cấu hình custom trong `.env`; không còn heuristic fallback |
| Chuẩn bị môi trường | Toàn nhóm | Python 3.12.10, `.venv`, dependencies, MiniLM và ChromaDB hoạt động |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Parse và bảo toàn dữ liệu Crossref | `parse_crossref_payload()`, `fetch_source_records()`, `load_raw_records()` | 24 raw records; có retry và offline fallback | Lệnh nghiệm thu Bước 2 |
| Sinh benchmark có ground truth | `build_test_set()` | 10 câu hỏi thuộc 4 loại `summary`, `authors`, `date`, `categories` | Lệnh nghiệm thu Bước 5 và `data/eval/test_set.json` |
| Chạy baseline end-to-end | `run_phase1_pipeline()` | Clean data, Chroma index, answers, metrics, quality/freshness reports | `python script/run_phase1.py` |
| Xuất báo cáo baseline | `generate_phase1_report()` | Báo cáo chứa corpus summary, metrics, GX và freshness | `data/reports/phase1_report.md` |
| Xác minh tích hợp Phase 2 | `script/run_corruption_flow.py` | Corrupted metrics giảm và repaired metrics trở về baseline | Console và `data/reports/corruption_report.md` |

Output chính của phần baseline gồm 24 tài liệu sạch, 10 câu hỏi benchmark, retrieval hit rate `1.0000`, mean token F1 `1.0000`, quality gate PASS và freshness PASS.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần giữ nguyên dữ liệu Crossref gốc để có thể truy vết và phục hồi, đồng thời chuyển metadata không đồng nhất thành schema ổn định cho các bước cleaning và embedding. Hệ thống cũng cần một benchmark cố định để so sánh công bằng ba trạng thái baseline, corrupted và repaired. Cuối cùng, các module độc lập phải được ghép thành một baseline flow có quality gate trước khi dữ liệu được đưa vào vector index.

### Cách triển khai

`parse_crossref_payload()` đọc `message.items`, chuẩn hóa DOI, tiêu đề, abstract, tác giả, subjects và ngày xuất bản. Thẻ HTML/JATS được loại bỏ, entity được giải mã, record thiếu trường cốt lõi hoặc trùng DOI bị loại. `fetch_source_records()` ưu tiên snapshot có sẵn khi không bật refresh; khi gọi API, hàm retry lỗi tạm thời và fallback về snapshot nếu mạng hoặc API thất bại.

`build_test_set()` khử trùng lặp theo `paper_id`, yêu cầu ít nhất 10 record đầy đủ và chọn tài liệu trải đều trên corpus. Mười câu hỏi có phân bố 3 `summary`, 3 `authors`, 2 `date`, 2 `categories`. Mỗi câu giữ DOI chuẩn trong `ground_truth_doc_ids` để đo retrieval hit.

`run_phase1_pipeline()` xâu chuỗi ingestion, cleaning, lưu CSV/JSON, kiểm tra GX và freshness, tạo embedding MiniLM, index ChromaDB, sinh test set, đánh giá RAG và xuất báo cáo. Pipeline không tiếp tục index nếu quality gate baseline thất bại.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref work-list payload, `Settings`, raw snapshot và clean DataFrame |
| Output | `PaperRecord`, raw/clean artifacts, Chroma collection, test set, metrics và Markdown report |
| Module phụ thuộc | `core.config`, `core.utils`, `ingestion.cleaning`, `retrieval.index`, `evaluation.metrics`, `observability.quality` |
| Module sử dụng output | Baseline evaluation và corruption/repair pipeline |
| Điều kiện lỗi cần xử lý | HTTP 429/5xx, mất mạng, payload sai schema, thiếu record, quality gate fail, LLM evaluator không sẵn sàng |

### Cách xác minh

```powershell
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Da tai {len(r)} bai bao')"
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); ts=build_test_set(pd.read_json(s.paths.clean_json), s.paths.eval_testset); print(f'Sinh duoc {len(ts)} cau hoi')"
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** 24 raw/clean records, 10 benchmark questions, baseline PASS; corrupted suy giảm và FAIL; repaired trở lại baseline và PASS.
- **Kết quả thực tế:** Các kết quả đều đạt như mong đợi. Phase 2 kết thúc với mã thoát `0` và in bảng ba trạng thái.
- **Artifact/log:** `data/raw/`, `data/eval/test_set.json`, `data/results/*_metrics.json`, `data/quality/`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Baseline phải chạy được khi Crossref không ổn định, và test set phải dùng lại nguyên vẹn cho cả ba trạng thái.
- **Các phương án đã cân nhắc:** Luôn gọi live API hoặc ưu tiên snapshot; chọn 10 dòng đầu hoặc chọn tài liệu trải đều trên corpus.
- **Phương án đã chọn:** Ưu tiên snapshot mặc định, có retry/fallback khi refresh; chọn 10 tài liệu theo các vị trí trải đều và lưu test set thành artifact.
- **Lý do:** Giảm phụ thuộc mạng, tránh rate limit, bảo toàn data lineage và làm phép so sánh ba trạng thái có thể tái lập.
- **Bằng chứng:** Offline snapshot trả đủ 24 records; benchmark sinh đúng 10 câu với DOI tồn tại trong clean corpus; cùng file test set được sử dụng ở baseline, corrupted và repaired.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Lần chạy `python script/run_corruption_flow.py` trên PowerShell dừng tại câu lệnh `print()` tiếng Việt với `UnicodeEncodeError: 'charmap' codec can't encode character`.
- **Nguyên nhân gốc:** Luồng `stdout/stderr` của terminal đang dùng `cp1252`, không biểu diễn được đầy đủ ký tự tiếng Việt.
- **Cách xử lý:** Cấu hình lại `stdout` và `stderr` sang UTF-8 trong wrapper `script/run_corruption_flow.py`, với `errors="replace"` để script không dừng vì ký tự hiển thị.
- **Cách xác minh:** Chạy lại `python script/run_corruption_flow.py`; pipeline hoàn tất với mã thoát `0`, in bảng ba trạng thái và tạo `corruption_report.md`.
- **Điều học được:** Một pipeline có thể đúng về logic nhưng vẫn không tái hiện được trên môi trường khác nếu entry point không xử lý encoding của terminal.

Khi kiểm tra sâu hơn, custom LLM trả judge theo dạng nhãn `Score/Correct/Reasoning` thay vì JSON nên `with_structured_output()` từng rơi vào heuristic fallback. Tôi bổ sung bộ phân tích hỗ trợ cả JSON và dạng nhãn, đồng thời chuyển QA sang sinh câu trả lời từ context qua model cấu hình trong `.env`. Lần chạy cuối ghi nhận `0` fallback trên cả baseline, corrupted và repaired. Ragas vẫn được bỏ qua vì `RUN_RAGAS` chưa bật.

## 7. Hiểu biết về luồng end-to-end

1. Crossref payload được giữ trong raw response, parse thành `PaperRecord`, làm sạch và ghép `text_for_embedding`. MiniLM biến văn bản thành vector rồi nạp vào các collection ChromaDB tương ứng.
2. Evaluation set chứa câu hỏi, đáp án chuẩn và DOI chuẩn. DOI xuất hiện trong top-k quyết định retrieval hit; prediction và ground truth được dùng để tính Token F1 và judge metrics.
3. Quality checks kiểm tra cấu trúc và tính hợp lệ như row count, null, unique và độ dài summary. Freshness kiểm tra tỷ lệ record có `age_days > 180` so với ngưỡng 25%.
4. Dùng cùng test set giúp thay đổi metrics phản ánh thay đổi dữ liệu, không phải thay đổi câu hỏi.
5. Repair thành công khi dữ liệu được dựng lại từ raw snapshot, quality/freshness trở lại PASS và metrics repaired trở về mức baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 1.0000 | Mất tài liệu mới và thay đổi nội dung làm trượt 20% câu hỏi; repair phục hồi hoàn toàn |
| `mean_token_f1` | 1.0000 | 0.7720 | 1.0000 | Summary trống/nhiễu làm câu trả lời lệch ground truth; repair phục hồi hoàn toàn |
| `judge_accuracy` | 1.0000 | 0.8000 | 1.0000 | 9Router judge đánh giá 20% câu trả lời corrupted là không đúng |
| `mean_judge_score` | 5.0000 | 4.1000 | 5.0000 | Điểm judge thật giảm 0,9 ở trạng thái corrupted và trở lại baseline |
| Quality checks | PASS | FAIL | PASS | Corrupted bị phát hiện do DOI trùng và hai summary có độ dài dưới 30 |
| Freshness status | PASS | FAIL | PASS | Tỷ lệ stale tăng từ 4,17% lên 31,82%, sau repair trở lại 4,17% |

### Kết luận từ số liệu

1. Bỏ 4 tài liệu mới, làm trống/nhiễu summary và tạo DOI trùng → GX chuyển từ PASS sang FAIL, freshness chuyển sang Stale Alert → retrieval hit rate giảm từ `1.0000` xuống `0.8000`, Token F1 giảm còn `0.7720`.
2. `repair_from_raw_snapshot()` dựng lại 24 dòng sạch từ `data/raw/crossref_records.json` → quality và freshness trở lại PASS → toàn bộ metrics repaired trở về đúng mức baseline.

Drop latest records ảnh hưởng trực tiếp đến retrieval hit vì tài liệu ground truth không còn trong index. Blank/noisy summary ảnh hưởng rõ đến Token F1 vì câu trả lời không còn đủ nội dung chuẩn. Kết quả hiện tại là tác động tổng hợp của sáu corruption; chưa có ablation riêng để định lượng chính xác đóng góp của từng lỗi.

Lần chạy đầu khác kỳ vọng vì judge âm thầm dùng heuristic dù 9Router hoạt động. Kiểm tra riêng cho thấy endpoint trả lời thành công nhưng không tuân theo JSON schema của `with_structured_output()`. Sau khi hỗ trợ định dạng phản hồi thực tế, các file `*_answers.json` chứa reasoning do model trả về và không còn chuỗi `Fallback heuristic`.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw preservation là điều kiện để repair có thể tái lập mà không phụ thuộc API ngoài.
2. Quality gate và freshness đo hai nhóm rủi ro khác nhau; cần dùng cả hai để phát hiện silent failure.
3. Benchmark cố định và collection tách biệt giúp phép so sánh baseline–corrupted–repaired có ý nghĩa.

### Nếu có thêm thời gian

Tôi sẽ bổ sung test tự động cho payload thiếu trường, HTTP 429, benchmark thiếu record và từng corruption riêng lẻ; sau đó chạy ablation để đo mức giảm metric do từng lỗi. Tôi cũng sẽ bật Ragas và mở rộng test set bằng câu hỏi không chứa nguyên tiêu đề để giảm lợi thế của exact-title lookup.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Khắc Tú
**Ngày xác nhận:** 2026-09-26
