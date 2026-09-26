# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Mai Tiến Huy               |
| MSSV               | 2A202602914                |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | T052AI                     |
| Vai trò chính    | Observability & Evaluation |
| Repository         | https://github.com/younglonelyboiz/K4-L3B-Day10-T052AI-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Quality Checks (GX 1.x) | `src/observability/quality.py` (`run_data_quality_checks`) | `df: pd.DataFrame`, settings | `data/quality/*_quality_report.json` | Hoàn thành |
| Freshness SLA Monitor | `src/observability/quality.py` (`build_freshness_report`) | `df: pd.DataFrame`, threshold=180 | `data/quality/*_freshness_report.json` | Hoàn thành |
| Benchmark Test Generator | `src/evaluation/testset.py` (`build_test_set`) | Cleaned DataFrame | `data/eval/test_set.json` (10 câu hỏi) | Hoàn thành |
| Reporting Modules | `src/observability/reporting.py` (`generate_phase1_report`, `generate_corruption_report`) | Summary metrics, quality, freshness | `phase1_report.md`, `corruption_report.md` | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Hỗ trợ STT 3 đánh giá RAG | Lê Việt Hoàng (`src/retrieval/index.py`) | Cung cấp file testset 10 câu hỏi chuẩn hóa có ground truth doc IDs |
| Hỗ trợ STT 1 luồng Corruption | Trịnh Xuân Huy (`src/pipelines/corruption_flow.py`) | Cung cấp logic phát hiện vi phạm Great Expectations khi bị tiêm lỗi |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết lập GX 1.x ephemeral | `src/observability/quality.py` | 4 Expectations chạy hoàn hảo trên GX 1.23.2 | Lệnh CP1: `Tín hiệu hoàn thành: Quality check status = True` |
| Sinh bộ 10 câu hỏi test | `src/evaluation/testset.py` | 10 câu hỏi chia đều 4 nhóm nghiệp vụ | Lệnh CP2: `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test` |
| Báo cáo so sánh 3 trạng thái | `src/observability/reporting.py` | Bảng Markdown phản ánh rõ hiện tượng suy giảm và phục hồi | Đối chiếu file `data/reports/corruption_report.md` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Bộ kiểm định Great Expectations phiên bản 1.x hoàn chỉnh không dùng API cũ đã deprecated, tự động xuất báo cáo chất lượng `data/quality/baseline_quality_report.json` và file đối sánh `data/reports/corruption_report.md` với đầy đủ các bảng dữ liệu.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Hiện tượng Silent Failure trong các hệ thống RAG xảy ra khi dữ liệu đầu vào bị trôi dạt (drift), thiếu trường hoặc lỗi thời mà không làm crash ứng dụng, dẫn đến LLM hallucination. Cần một cơ chế Data Observability tự động phát hiện sớm sự suy giảm chất lượng dữ liệu trước khi nạp vào vector store.

### Cách triển khai

- **Cú pháp Great Expectations 1.x:** Khởi tạo `gx.get_context(mode="ephemeral")`, đăng ký Pandas Data Source `gx_data_source`, thêm DataFrame Data Asset và định nghĩa batch bằng `add_batch_definition_whole_dataframe`.
- **4 Expectations trọng tâm:**
  - `ExpectTableRowCountToBeBetween(min_value=20, max_value=30)`: Ngăn chặn thiếu hụt hoặc bùng nổ dữ liệu.
  - `ExpectColumnValuesToNotBeNull(column="paper_id")`: Đảm bảo khóa chính định danh luôn hiện diện.
  - `ExpectColumnValuesToBeUnique(column="paper_id")`: Chống trùng lặp dữ liệu trong vector store.
  - `ExpectColumnValueLengthsToBeBetween(column="summary", min_value=10)`: Ngăn chặn bài báo có tóm tắt rỗng.
- **Giám sát Freshness SLA:** Tính toán tỷ lệ các bài báo có `age_days > 180`. Nếu tỷ lệ vượt quá `settings.freshness_sla_days` (25%), gán cờ `is_fresh = False` và trạng thái `STALE`.
- **Bộ dữ liệu Benchmark:** Sinh 10 câu hỏi chia đều 4 nhóm: `summary` (ngữ nghĩa), `authors` (tác giả), `date` (thời gian), `categories` (chủ đề), kèm `ground_truth_doc_ids` phục vụ tính toán Hit Rate và Token F1.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Cleaned DataFrame hoặc Corrupted DataFrame |
| Output                         | `data/eval/test_set.json`, `data/quality/*.json`, các báo cáo Markdown trong `data/reports/` |
| Module phụ thuộc             | `great_expectations 1.23.2`, `core.config.Settings`, `core.utils.write_json` |
| Module sử dụng output        | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/evaluation/evaluate.py` |
| Điều kiện lỗi cần xử lý | Phiên bản GX không tương thích (chuyển đổi hoàn toàn sang API 1.x), xử lý ngoại lệ JSON serialization khi GX trả về object validation result phức tạp |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from ingestion.cleaning import load_clean_dataset; from observability.quality import run_data_quality_checks; s=load_settings(); res=run_data_quality_checks(load_clean_dataset(s.paths.clean_dataset_json), s); print(f'Tín hiệu hoàn thành: Quality check status = {res.get(\"success\")}')"
```

- **Kết quả mong đợi:** In ra `Tín hiệu hoàn thành: Quality check status = True`.
- **Kết quả thực tế:** Trùng khớp 100% với kết quả mong đợi.
- **Artifact/log:** `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp tích hợp Great Expectations giữa API cũ (ExpectationSuite, Checkpoint v3) và API mới chuẩn GX 1.x.
- **Các phương án đã cân nhắc:**
  1. *Phương án 1:* Dùng API `gx.dataset.PandasDataset` (legacy, thường gặp lỗi cảnh báo deprecation và không tương thích GX >= 1.0).
  2. *Phương án 2:* Dùng kiến trúc chuẩn GX 1.x Ephemeral (`get_context`, `sources.add_pandas`, `add_batch_definition_whole_dataframe`, `ValidationDefinition`).
- **Phương án đã chọn:** Phương án 2 (Kiến trúc Ephemeral GX 1.x).
- **Lý do:** Đảm bảo mã nguồn chạy ổn định lâu dài trên Great Expectations phiên bản 1.23.2, không yêu cầu khởi tạo thư mục `great_expectations/` cồng kềnh trên đĩa, chạy nhanh và độc lập trong bộ nhớ RAM.
- **Bằng chứng quyết định phù hợp:** Chạy xác minh CP1 thành công chỉ trong 0.8 giây, validation result xuất ra file JSON có cấu trúc chi tiết, phát hiện chính xác vi phạm khi dữ liệu bị lỗi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: DataContext.sources is deprecated / ExpectationSuite not found` khi chạy script kiểm tra chất lượng ban đầu do code mẫu dùng cú pháp Great Expectations v0.15.
- **Lệnh hoặc bước tái hiện:** `python -c "import great_expectations as gx; context = gx.get_context()"`
- **Nguyên nhân gốc:** Môi trường ảo đang cài đặt Great Expectations phiên bản mới nhất `1.23.2`, phiên bản này đã tái cấu trúc toàn bộ API suite và batch definition.
- **Cách xử lý:** Viết lại toàn bộ hàm `run_data_quality_checks` sử dụng cơ chế Data Source -> Data Asset -> Batch Definition -> Expectation -> Validation Definition của GX 1.x.
- **Cách xác minh sau khi sửa:** Chạy kiểm tra trên cả 2 tập dữ liệu: Clean (trả về `success=True`) và Corrupted (trả về `success=False` với 2 vi phạm rõ rệt: trùng lặp DOI và tóm tắt rỗng).
- **Điều học được:** Khi làm việc với các thư viện mã nguồn mở phát triển nhanh, việc bám sát Migration Guide và Release Notes của phiên bản thực tế là yếu tố sống còn.

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** N/A (Đã xử lý hoàn tất 100%)
- **Những gì đã loại trừ:** N/A
- **Bước tiếp theo:** N/A

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index:** Dữ liệu thô từ Crossref REST API (hoặc snapshot offline dự phòng) được tải về và lưu vào `data/raw/crossref_response.json` cùng `crossref_records.json` (bảo toàn data lineage). Sau đó hàm `build_clean_dataframe` trong `cleaning.py` làm sạch các thẻ XML, tính trường `age_days` và tạo chuỗi `text_for_embedding` 5 phần có nhãn. Chuỗi văn bản này được đưa vào mô hình `all-MiniLM-L6-v2` để sinh vector 384 chiều và nạp vào ChromaDB collection `papers-baseline`.
2. **Evaluation set và ground-truth document IDs:** Module `testset.py` trích xuất 10 cặp câu hỏi - câu trả lời cùng `ground_truth_doc_ids` từ clean DataFrame. Khi RAG truy vấn, nếu doc_id do vector search tìm được nằm trong danh sách ground_truth_doc_ids thì tính là `retrieval_hit = True`. Mean Token F1 đo lường sự trùng khớp từ vựng giữa câu trả lời sinh ra và câu trả lời chuẩn ground truth.
3. **Quality checks khác freshness monitoring:** Quality checks (Great Expectations 1.x) kiểm định tính toàn vẹn cấu trúc tĩnh của bảng (số dòng [20, 30], khóa chính không trùng, trường bắt buộc không null, độ dài summary >= 10). Trong khi đó Freshness monitoring đo lường chiều thời gian (Data Drift/Staleness), phát hiện tỷ lệ bài báo quá hạn (> 180 ngày) vượt ngưỡng SLA 25%.
4. **Vì sao phải dùng cùng test set cho 3 trạng thái:** Để đảm bảo tính khách quan và khoa học (Controlled Experiment). Việc giữ cố định bộ câu hỏi giúp mọi sự thay đổi về Hit Rate và Token F1 phản ánh chính xác tác động của việc dữ liệu bị lỗi và phục hồi, loại bỏ thiên vị do câu hỏi khác nhau.
5. **Repair được xem là thành công dựa trên:** Hệ thống khôi phục hoàn toàn chỉ số Retrieval Hit Rate về 100.0%, Mean Token F1 về 1.000, Quality Gate chuyển từ `FAILED` sang `PASSED`, và Freshness SLA chuyển từ `STALE` sang `FRESH`, thể hiện qua các artifact `data/results/repaired_metrics.json` và `data/reports/corruption_report.md`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   100.0% |     60.0% |   100.0% | Sụt giảm nghiêm trọng (-40%) khi bị tiêm lỗi, hồi sinh 100% sau repair |
| `mean_token_f1`      |    1.000 |     0.497 |    1.000 | Chất lượng văn bản câu trả lời giảm hơn 50% ở trạng thái lỗi |
| `judge_accuracy`     |   100.0% |     50.0% |   100.0% | Tỷ lệ câu trả lời đạt chuẩn ngữ nghĩa khôi phục toàn diện |
| `mean_judge_score`   | 5.00/5.0 | 3.00/5.0 | 5.00/5.0 | Điểm đánh giá chất lượng câu trả lời phục hồi tối đa |
| Quality checks         | `PASSED` |  `FAILED` | `PASSED` | GX 1.x bắt trọn vi phạm trùng lặp DOI và rỗng summary |
| Freshness status       |  `FRESH` |   `STALE` |  `FRESH` | Cảnh báo vi phạm ngưỡng SLA 180 ngày chính xác |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. [Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]:  
   Khi 6 kịch bản lỗi được tiêm vào (xóa 20% bản ghi mới nhất, làm rỗng summary, chèn ký tự rác, lùi ngày về 2020) → Quality check chuyển sang `FAILED` và Freshness chuyển sang `STALE` → Dẫn đến Retrieval Hit Rate sụt giảm từ 100.0% xuống 60.0% và Mean Token F1 giảm từ 1.000 xuống 0.497.
2. [Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi hoặc chưa phục hồi]:  
   Khi kích hoạt cơ chế Idempotent Repair tái tạo từ immutable raw snapshot `crossref_records.json` → Quality check phục hồi về `PASSED`, Freshness phục hồi về `FRESH` → Retrieval Hit Rate và Token F1 phục hồi 100% về mức 100.0% và 1.000.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Kịch bản `blank_summary` và `drop_latest_records` làm cho các câu hỏi thuộc nhóm `summary` và `date` hoàn toàn mất phương hướng vì thông tin ngữ nghĩa bị xóa bỏ, dẫn đến Token F1 sụt giảm nghiêm trọng từ 1.000 xuống 0.497.

Kết quả nào khác với kỳ vọng ban đầu?

Ban đầu dự kiến Great Expectations sẽ cảnh báo tất cả 6 lỗi, tuy nhiên chỉ có các lỗi ảnh hưởng trực tiếp đến schema và ràng buộc đã định nghĩa (null, unique, length) mới kích hoạt cảnh báo, còn lỗi ngữ nghĩa cần đến vector search và LLM evaluation mới phát hiện được. Điều này cho thấy kiểm thử chất lượng dữ liệu cần phối hợp đa tầng (Multi-layer Observability).

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Về data pipeline: Pipeline tự động hóa cao bắt buộc phải có các chốt kiểm định chất lượng (Quality Gates) tự động; nếu không, dữ liệu xấu sẽ lan truyền qua toàn bộ hệ thống downstream.
2. Về data quality/observability: Great Expectations 1.x kết hợp cùng Freshness SLA giúp giám sát toàn diện 2 chiều: chiều cấu trúc (Static Schema Quality) và chiều thời gian (Dynamic Data Drift).
3. Về ảnh hưởng của data đến RAG agent: Vector search hoàn toàn phụ thuộc vào chất lượng của trường dữ liệu làm sạch `text_for_embedding`.

### Nếu có thêm thời gian

Tôi sẽ xây dựng thêm bộ Expectation nâng cao để kiểm tra phân bố độ dài của abstract (Distribution Expectations) và thiết lập kênh cảnh báo tự động gửi qua Webhook (Slack / Discord) khi Quality Check bị FAILED.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Mai Tiến Huy  
**Ngày xác nhận:** 2026-09-26
