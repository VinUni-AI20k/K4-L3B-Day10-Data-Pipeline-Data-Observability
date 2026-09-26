# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phạm Khắc Tú |
| MSSV | 2A202602866 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | 4aesieunhan |
| Vai trò chính | Data ingestion, benchmark evaluation và baseline integration |
| Repository | https://github.com/TuTu99999/K4-L3B-DAY10-4aesieunhan-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Crossref ingestion | `src/ingestion/crossref.py` | Crossref payload hoặc raw snapshot | 24 `PaperRecord`, raw response và parsed records | Hoàn thành |
| Benchmark test set | `src/evaluation/testset.py` | Clean dataframe | `data/eval/test_set.json` gồm 10 câu hỏi | Hoàn thành |
| Baseline orchestration | `src/pipelines/phase1.py` | Settings, raw records và các module pipeline | Toàn bộ baseline artifacts và metrics | Hoàn thành |
| Baseline reporting | `src/observability/reporting.py` | Source summary, metrics, quality và freshness | `data/reports/phase1_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra cleaning | `src/ingestion/cleaning.py` của HoangTranTuan | Xác nhận clean thành công 24 dòng, không trùng DOI và đúng template embedding |
| Kiểm tra observability | `src/observability/quality.py` của HoangTranTuan | Xác nhận 6 GX expectation instances và freshness SLA đều pass |
| Chuẩn bị môi trường | Toàn nhóm | Python 3.12.10, `uv`, MiniLM cache và `.venv` hoạt động |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Parse và bảo toàn dữ liệu Crossref | `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | 24 record sạch ở tầng raw, có retry và offline fallback | Lệnh nghiệm thu bước 2 và kiểm thử fallback giả lập mất mạng |
| Sinh benchmark có ground truth | `build_test_set` | 10 câu hỏi, đủ 4 loại với phân bố 3/3/2/2 | Lệnh nghiệm thu bước 5 và kiểm tra schema/DOI |
| Chạy baseline end-to-end | `run_phase1_pipeline` | Clean data, Chroma index, answers, metrics, quality và freshness reports | `python script/run_phase1.py` |
| Xuất báo cáo baseline | `generate_phase1_report` | Báo cáo Markdown chứa bảng metrics và GX details | `data/reports/phase1_report.md` |

Output chính là baseline gồm 24 tài liệu, 10 câu hỏi benchmark, retrieval hit rate 1.0, mean token F1 1.0 và quality/freshness đều pass.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần giữ được dữ liệu Crossref nguyên gốc để truy vết và repair, đồng thời phải biến metadata thành schema ổn định cho cleaning. Sau đó cần một benchmark tái lập được để cùng một bộ câu hỏi có thể đánh giá baseline, corrupted và repaired. Cuối cùng, các module độc lập phải được ghép thành một baseline flow có quality gate chặn dữ liệu lỗi trước khi index.

### Cách triển khai

`parse_crossref_payload` đọc `message.items`, chuẩn hóa DOI, title, abstract, authors, subjects và ngày. Thẻ HTML/JATS được loại bỏ, entity được giải mã, DOI trùng hoặc record thiếu trường cốt lõi bị bỏ qua. `fetch_source_records` dùng snapshot khi không yêu cầu refresh; khi gọi API, hàm retry các lỗi 429/5xx và quay về snapshot nếu mạng thất bại.

`build_test_set` khử trùng lặp theo DOI, yêu cầu tối thiểu 10 record đầy đủ và chọn tài liệu trải đều trên corpus. Mười câu hỏi được phân bổ cho `summary`, `authors`, `date`, `categories`; mỗi câu giữ DOI ground truth để đo retrieval hit.

`run_phase1_pipeline` chạy ingestion, cleaning, lưu CSV/JSON, GX quality/freshness gate, MiniLM embedding, ChromaDB indexing, benchmark evaluation và report generation. Pipeline dừng trước bước index nếu quality gate thất bại.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref work-list payload, `Settings`, raw snapshot và clean dataframe |
| Output | `PaperRecord`, clean artifacts, Chroma collection, test set, metrics và Markdown report |
| Module phụ thuộc | `core.config`, `core.utils`, `ingestion.cleaning`, `retrieval.index`, `evaluation.metrics`, `observability.quality` |
| Module sử dụng output | Baseline evaluation và corruption/repair pipeline |
| Điều kiện lỗi cần xử lý | Mạng lỗi/429, payload sai schema, thiếu record, quality gate fail, LLM evaluator không sẵn sàng |

### Cách xác minh

```powershell
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(len(r))"
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); print(len(build_test_set(pd.read_json(s.paths.clean_json), s.paths.eval_testset)))"
python script/run_phase1.py
```

- **Kết quả mong đợi:** 24 raw records, 10 benchmark questions, baseline artifacts đầy đủ và quality gate pass.
- **Kết quả thực tế:** 24 raw/clean records, 10 câu hỏi, retrieval hit rate 1.0, mean token F1 1.0, GX và freshness đều pass.
- **Artifact/log:** `data/raw/`, `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Baseline cần chạy được khi Crossref không ổn định và test set phải dùng lại được cho các pha sau.
- **Các phương án đã cân nhắc:** Luôn gọi live API; hoặc ưu tiên snapshot và chỉ refresh khi được yêu cầu. Test set có thể lấy 10 dòng đầu; hoặc chọn tài liệu trải đều trên corpus.
- **Phương án đã chọn:** Ưu tiên snapshot mặc định, có retry/fallback khi refresh; chọn 10 tài liệu theo các vị trí trải đều và lưu test set thành artifact.
- **Lý do:** Cách này giảm phụ thuộc mạng, tránh rate limit, giữ lineage anchor và làm phép so sánh ba trạng thái có thể tái lập.
- **Bằng chứng quyết định phù hợp:** Kiểm thử offline fallback vẫn trả 24 record; benchmark sinh đúng 10 câu với mọi DOI tồn tại trong clean corpus.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `401 Invalid API key` khi thử gọi model qua 9Router local.
- **Lệnh hoặc bước tái hiện:** Khởi tạo `ChatOpenAI` với endpoint `http://127.0.0.1:20128/v1` và gọi model `cx/gpt-5.6-luna`.
- **Nguyên nhân gốc:** Project chưa được cung cấp API key hợp lệ cho endpoint 9Router.
- **Cách xử lý:** Baseline verification dùng `LLM_PROVIDER=mock`; evaluator tự dùng heuristic fallback đã có trong `evaluation/metrics.py`. Retrieval và answer extraction vẫn chạy trên ChromaDB/MiniLM thật.
- **Cách xác minh sau khi sửa:** `python script/run_phase1.py` hoàn tất và sinh đủ metrics/report.
- **Điều học được:** Cần phân biệt retrieval metrics độc lập với LLM-as-a-judge và phải ghi rõ khi evaluator dùng fallback.

## 7. Hiểu biết về luồng end-to-end

1. Crossref payload được giữ ở raw response, parse thành `PaperRecord`, làm sạch và ghép `text_for_embedding`. MiniLM biến văn bản thành vector rồi nạp vào collection ChromaDB.
2. Evaluation set chứa câu hỏi, đáp án chuẩn và DOI chuẩn. DOI xuất hiện trong top-k quyết định retrieval hit; answer và ground truth được dùng tính Token F1 và judge metrics.
3. Quality checks kiểm tra cấu trúc và tính hợp lệ như row count, null, unique và độ dài summary. Freshness đo tuổi dữ liệu và tỷ lệ record quá SLA 180 ngày.
4. Dùng cùng test set giúp mọi thay đổi metrics đến từ dữ liệu baseline/corrupted/repaired, thay vì do thay đổi câu hỏi.
5. Repair thành công khi quality/freshness phục hồi và metrics repaired tiến gần hoặc bằng baseline, được chứng minh bằng JSON artifacts và comparison report.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | Chưa chạy | Chưa chạy | Exact-title lookup và clean index tìm đúng toàn bộ DOI chuẩn |
| `mean_token_f1` | 1.0000 | Chưa chạy | Chưa chạy | Câu trả lời trích trực tiếp metadata khớp ground truth |
| `judge_accuracy` | 1.0000 | Chưa chạy | Chưa chạy | Baseline này dùng heuristic fallback do 9Router chưa có key hợp lệ |
| `mean_judge_score` | 5.0000 | Chưa chạy | Chưa chạy | Mọi prediction baseline khớp reference |
| Quality checks | PASS | Chưa chạy | Chưa chạy | 6/6 expectation instances pass |
| Freshness status | PASS | Chưa chạy | Chưa chạy | 1/24 record stale, tỷ lệ 0.0417 nhỏ hơn 0.25 |

### Kết luận từ số liệu

Baseline chứng minh clean corpus, index và benchmark đang nhất quán. Chưa thể kết luận chuỗi corruption → metric suy giảm hoặc repair → metric phục hồi vì corruption flow chưa được thực thi ở thời điểm lập báo cáo này.

Corruption ảnh hưởng rõ nhất và kết quả khác kỳ vọng sẽ được bổ sung sau khi `run_corruption_flow.py` tạo artifact thật. Không ghi nhận định trước khi có số liệu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw preservation giúp pipeline phục hồi và tái hiện kết quả mà không phụ thuộc API ngoài.
2. Data quality gate cần chạy trước indexing để lỗi dữ liệu không âm thầm đi vào serving layer.
3. Benchmark phải cố định ground-truth document IDs để tách ảnh hưởng của dữ liệu khỏi ảnh hưởng của bộ câu hỏi.

### Nếu có thêm thời gian

Bổ sung test tự động cho payload thiếu trường, HTTP 429, benchmark không đủ 10 record và quality gate fail; sau đó đo coverage để bảo vệ contract giữa các module.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Khắc Tú
**Ngày xác nhận:** 26/09/2026
