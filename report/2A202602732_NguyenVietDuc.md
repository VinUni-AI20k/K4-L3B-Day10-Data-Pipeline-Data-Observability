# Báo cáo cá nhân — Nguyễn Việt Đức

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Việt Đức |
| MSSV | 2A202602732 |
| Khóa/Lớp | K4-L3B-DAY10 |
| Tên nhóm | AIGANG |
| Vai trò chính | Xây dựng bộ đề đánh giá (bước 5) và tích hợp baseline pipeline (bước 6) |
| Repository | https://github.com/JJayzdev/K4-L3B-Day10-AIGANG-DataPipelineDataObservability |
| Ngày ghi nhận kết quả | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Benchmark test set | `src/evaluation/testset.py` — `build_test_set` | `DataFrame` dữ liệu sạch | `data/eval/test_set.json`, 10 câu hỏi | Hoàn thành, đã kiểm tra |
| Baseline orchestration | `src/pipelines/phase1.py` — `run_phase1_pipeline`, `main` | Cấu hình và raw records | Dữ liệu sạch, ChromaDB index, baseline metrics, quality artifacts | Hoàn thành, script chạy exit code 0 |
| Báo cáo baseline | `src/observability/reporting.py` — `generate_phase1_report` | Source summary, metrics, quality, freshness | `data/reports/phase1_report.md` | Hoàn thành, đã đối chiếu số liệu |

### Việc hỗ trợ ngoài phạm vi chính

Tôi điều chỉnh mẫu câu hỏi `authors` và `categories` trong test set để khớp với quy tắc trích xuất câu trả lời hiện có ở `src/retrieval/qa.py`. Tôi không nhận ownership đối với các module ingestion, cleaning, embedding hay Great Expectations; pipeline của tôi gọi các module đó qua giao diện sẵn có.

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Sinh benchmark từ dữ liệu sạch | `src/evaluation/testset.py`, `data/eval/test_set.json` | 10 câu hỏi, 10 DOI riêng biệt: 3 `summary`, 3 `authors`, 2 `date`, 2 `categories` | Chạy `build_test_set`; đọc và đếm các mục trong JSON |
| Chạy baseline pipeline | `src/pipelines/phase1.py`, `script/run_phase1.py` | 24 dòng trong `data/clean/papers_clean.csv`; ChromaDB collection `papers-baseline` | Script chạy exit code 0; đếm dòng CSV |
| Đánh giá baseline | `data/results/baseline_metrics.json`, `baseline_answers.json` | 10 mẫu; Hit Rate 1.000; Token F1 1.000 | Đọc metrics và 10 câu trả lời đã lưu |
| Kiểm tra chất lượng và viết báo cáo | `data/quality/`, `data/reports/phase1_report.md` | Quality Gate đạt; 6/6 GX expectations đạt; 0/24 bài quá hạn | Đối chiếu các JSON chất lượng và báo cáo Markdown |

Artifact chính của phần việc tôi là `data/eval/test_set.json` và `data/reports/phase1_report.md`. Báo cáo Markdown được sinh từ metrics thực tế của lần chạy pipeline, không điền số thủ công.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

RAG cần một tập câu hỏi có đáp án chuẩn và DOI chuẩn để đo hai việc riêng: có lấy được đúng tài liệu hay không, và câu trả lời giống đáp án chuẩn đến mức nào. Sau đó cần một lệnh chạy thống nhất để cùng một dữ liệu sạch đi qua indexing, evaluation và các kiểm tra chất lượng.

### Cách triển khai

`build_test_set` kiểm tra các cột bắt buộc (`paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`), loại các dòng thiếu dữ liệu và DOI trùng, rồi chọn 10 bài rải đều trên DataFrame sạch. Hàm gán luân phiên bốn loại câu hỏi, tạo ID từ `eval_001` đến `eval_010`, lấy câu đầu của `summary` làm đáp án tóm tắt, và đặt DOI trong `ground_truth_doc_ids`. Nếu không đủ 10 bài hợp lệ, hàm báo lỗi rõ ràng thay vì tạo benchmark thiếu mẫu.

`run_phase1_pipeline` dùng raw records đã lưu khi không yêu cầu refresh, làm sạch và ghi CSV/JSON, tạo ChromaDB index, sinh hoặc đọc test set theo cấu hình, đánh giá 10 câu hỏi, chạy Great Expectations và freshness check, rồi chuyển kết quả đo được vào hàm tạo báo cáo. Việc dùng raw records đã lưu giúp lần chạy baseline này có nguồn đầu vào ổn định.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input bước 5 | `DataFrame` dữ liệu sạch có DOI, tiêu đề, tóm tắt, tác giả, lĩnh vực, ngày xuất bản |
| Output bước 5 | JSON list; mỗi mục có `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` |
| Input bước 6 | `Settings` từ `core.config`, raw records và các module ingestion/retrieval/evaluation/observability |
| Output bước 6 | `papers_clean.csv/json`, ChromaDB index, test set, baseline metrics/answers, quality/freshness JSON, báo cáo Markdown |
| Module dùng output | `evaluation.metrics` đọc test set; pipeline và nhóm dùng metrics/report để kiểm tra baseline |
| Điều kiện lỗi | Thiếu cột bắt buộc, ít hơn 10 bài hợp lệ, hoặc DataFrame sạch rỗng sẽ dừng với thông báo lỗi |

### Cách xác minh

Trong PowerShell, với `.venv` đã kích hoạt:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:REFRESH_TEST_SET = 'true'
python script/run_phase1.py
```

Kết quả thực tế: `Clean papers: 24`, `Retrieval hit rate: 1.000`, `Mean token F1: 1.000`, `Quality gate passed: True`; tiến trình kết thúc với exit code 0. Tôi cũng kiểm tra file JSON có đúng 10 câu hỏi, đủ bốn loại và 10 DOI riêng biệt. `REFRESH_TEST_SET=true` được dùng trong lần chạy này để tạo lại test set sau khi chỉnh mẫu câu hỏi.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn 10 bài báo cho benchmark từ 24 bài sạch.
- **Phương án cân nhắc:** Lấy 10 dòng đầu tiên hoặc rải đều 10 bài trên toàn bộ DataFrame.
- **Phương án chọn:** Rải đều theo vị trí sau khi lọc dòng hợp lệ và DOI trùng.
- **Lý do:** Tránh benchmark chỉ tập trung vào một đoạn đầu của dữ liệu đã sắp theo ngày; cách chọn vẫn xác định được và tái tạo được trên cùng đầu vào.
- **Bằng chứng:** `data/eval/test_set.json` có 10 DOI riêng biệt và phân bổ câu hỏi 3/3/2/2. Số lượng và DOI được kiểm tra trực tiếp từ artifact.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi chạy lệnh kiểm tra in thông báo tiếng Việt, terminal báo `UnicodeEncodeError: 'charmap' codec can't encode character ...` dù hàm đã tạo file JSON.
- **Bước tái hiện:** Chạy lệnh `python -c` kiểm tra `build_test_set` trong phiên PowerShell dùng mã hóa đầu ra `cp1252`.
- **Nguyên nhân gốc:** Python không mã hóa được một số ký tự tiếng Việt theo code page của terminal; lỗi xảy ra ở `print`, không phải ở logic sinh test set.
- **Cách xử lý:** Đặt `PYTHONIOENCODING=utf-8` cho tiến trình Python, rồi chạy lại lệnh kiểm tra.
- **Xác minh:** Console in đúng `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test` và file JSON có 10 mục.
- **Điều học được:** Khi gặp lỗi encoding ở console, cần phân biệt nó với lỗi ghi artifact để không sửa nhầm phần xử lý dữ liệu.

Trong lần chạy baseline, Gemini còn trả `429 RESOURCE_EXHAUSTED` tạm thời do giới hạn số request; thư viện tự retry và pipeline vẫn kết thúc thành công. `baseline_answers.json` ghi một lượt chấm bằng fallback heuristic, nên `judge_accuracy` không hoàn toàn đến từ LLM judge.

## 7. Hiểu biết về luồng end-to-end

1. Crossref payload được lưu ở `data/raw/crossref_response.json`, bóc tách thành `PaperRecord` tại `crossref_records.json`; bước cleaning chuẩn hóa, khử trùng lặp DOI và tạo `text_for_embedding`; mô hình MiniLM mã hóa văn bản để lưu vào collection ChromaDB.
2. Test set giữ câu hỏi, đáp án chuẩn và DOI chuẩn. `ground_truth_doc_ids` được so với DOI của các tài liệu truy xuất để tính Hit Rate; câu trả lời của QA được so với `ground_truth` để tính Token F1 và điểm judge.
3. Great Expectations kiểm tra cấu trúc và nội dung như số dòng, null, DOI trùng và độ dài tóm tắt. Freshness dùng `age_days` để kiểm tra tỷ lệ bài quá ngưỡng 180 ngày; một bộ dữ liệu có thể đúng schema nhưng vẫn quá cũ.
4. Nếu baseline, corrupted và repaired dùng các câu hỏi khác nhau, mức tăng giảm metric không thể quy về thay đổi chất lượng dữ liệu. Vì vậy ba trạng thái phải dùng cùng test set và cùng định nghĩa metric.
5. Repair chỉ có thể được kết luận thành công sau khi dữ liệu sạch được tái lập, quality/freshness report đạt và metrics repaired được so trực tiếp với baseline trên cùng test set. Trong lần ghi nhận này chưa có artifacts corrupted/repaired nên chưa kết luận về repair.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | Chưa chạy | Chưa chạy | 10/10 câu có DOI chuẩn trong kết quả truy xuất |
| `mean_token_f1` | 1.000 | Chưa chạy | Chưa chạy | Câu trả lời trùng token với đáp án chuẩn trong lần chạy này |
| `judge_accuracy` | 1.000 | Chưa chạy | Chưa chạy | Có 1/10 lượt chấm dùng fallback heuristic |
| `mean_judge_score` | 5.000 | Chưa chạy | Chưa chạy | Điểm trung bình trong baseline metrics |
| Quality checks | Đạt, 6/6 GX | Chưa chạy | Chưa chạy | 24 dòng được kiểm tra |
| Freshness status | Đạt, 0/24 cũ | Chưa chạy | Chưa chạy | Tỷ lệ quá hạn bằng 0 |

Các chuỗi **corruption → tín hiệu chất lượng → metric** và **repair → phục hồi tín hiệu → metric** chưa thể phân tích bằng số vì chưa có `corrupted_metrics.json`, `repaired_metrics.json` và báo cáo tương ứng trong workspace. Không có cơ sở để nêu loại corruption ảnh hưởng mạnh nhất.

Điểm baseline 1.000 cần đọc trong đúng bối cảnh: câu hỏi chứa nguyên tên bài báo, còn `answer_question` có nhánh tra cứu tên chính xác trước khi chốt kết quả. Do đó Hit Rate này phản ánh toàn bộ logic truy xuất hiện tại, chưa đo riêng sức mạnh tìm kiếm ngữ nghĩa của ChromaDB trên câu hỏi không nêu tên bài.

## 9. Điều học được và hướng cải thiện

1. Benchmark cần DOI ổn định, đáp án chuẩn và quy tắc tạo mẫu có thể tái hiện; chỉ có số câu hỏi là chưa đủ.
2. Quality Gate và freshness là hai tín hiệu bổ sung: schema tốt không bảo đảm tài liệu còn mới.
3. Điểm RAG cao phải được giải thích cùng cách đặt câu hỏi và chiến lược lookup; không nên xem một số 1.000 là bằng chứng tổng quát cho mọi truy vấn.

Nếu có thêm thời gian, tôi sẽ thêm một nhóm câu hỏi diễn đạt lại không chứa tên bài chính xác, rồi so Hit Rate và Token F1 với benchmark hiện tại. Phép đo đó giúp tách đóng góp của vector search khỏi nhánh exact-title lookup.

## 10. Tự kiểm tra trước khi nộp

- [x] Các số liệu baseline trong báo cáo khớp với artifacts đã tạo từ pipeline.
- [x] Không ghi kết quả corrupted/repaired khi chưa có artifacts để kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Tôi đã tự đọc lại, xác nhận nội dung phản ánh đúng đóng góp cá nhân và có thể giải thích khi được hỏi.
- [ ] Tôi đã cập nhật phân công tương ứng trong `docs/TEAM.md` và xác nhận thông tin nhóm.

**Họ và tên:** Nguyễn Việt Đức

**Ngày tự xác nhận:** Chờ cá nhân xác nhận trước khi nộp.
