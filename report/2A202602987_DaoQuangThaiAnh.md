# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đào Quang Thái Anh |
| MSSV | 2A202602987 |
| Khóa/Lớp | K4 |
| Tên nhóm | Bar |
| Vai trò chính | Lead (Pipeline Orchestration & Observability / Quality Gates) |
| Repository | https://github.com/masao1112/K4-L3B-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| **Data Observability & Quality Gates** | `src/observability/quality.py` (`run_data_quality_checks`, `evaluate_freshness_sla`, `build_freshness_report`) | DataFrame (`clean`, `corrupted`, `repaired`), `Settings` | Các báo cáo JSON chất lượng và độ tươi mới: `data/quality/*_quality_report.json`, `data/quality/*_freshness_report.json` | Hoàn thành |
| **Baseline Pipeline Orchestration** | `src/pipelines/phase1.py`, `script/run_phase1.py` (`run_phase1_pipeline`, `main`) | Crossref API / Raw snapshot, cấu hình `Settings` | Toàn bộ quy trình Pha 1: clean CSV/JSON, ChromaDB vector store (`papers-baseline`), evaluation test set, baseline metrics, báo cáo `data/reports/phase1_report.md` | Hoàn thành |
| **Corruption, Repair & Recovery Flow** | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` (`run_corruption_flow_pipeline`, `repair_from_raw_snapshot`, `_write_comparison_report`) | Clean data, raw snapshot `crossref_records.json`, test set `test_set.json` | Dữ liệu corrupted/repaired, vector collections tương ứng, báo cáo so sánh `data/reports/corruption_report.md`, log `corruption_log.json` | Hoàn thành |
| **LLM & Embeddings Integration** | `src/retrieval/embeddings.py`, `src/retrieval/llm.py` (`build_embeddings`, `build_chat_model`) | Cấu hình provider, API key, model name | Client đối tượng embedding model và Chat LLM (hỗ trợ Gemini, OpenAI, MiniLM fallback) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| **Data Modeling & Cleaning** | Dương Đức Vương (`src/ingestion/cleaning.py`) | Thống nhất Data Contract: chuẩn hóa chuỗi `text_for_embedding`, tính toán `age_days` theo chuẩn timezone UTC để phục vụ đo lường Freshness SLA chính xác |
| **Corruption Design & Logging** | Dương Đức Vương (`src/ingestion/corruption.py`) | Định nghĩa cấu trúc file log `data/results/corruption_log.json` có diff trước/sau để làm bằng chứng kiểm toán cho báo cáo so sánh |
| **Benchmark Testset Design** | Nguyễn Thành Tiến (`src/evaluation/testset.py`) | Chuẩn hóa danh sách `ground_truth_doc_ids` (mảng DOI) và xây dựng 4 nhóm câu hỏi nghiệp vụ (`summary`, `authors`, `date`, `categories`) |
| **Crossref API Resilience** | Nguyễn Thành Tiến (`src/ingestion/crossref.py`) | Tích hợp thư viện `tenacity` xử lý retry exponential backoff khi gặp mã lỗi HTTP 429 (rate limit) hoặc 5xx từ máy chủ Crossref |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Xây dựng hệ thống Data Quality Gate dùng Great Expectations 1.x | `src/observability/quality.py` (`run_data_quality_checks`) | Báo cáo kiểm định `baseline_quality_report.json` (6/6 PASS) và `corrupted_quality_report.json` (4/6 PASS, 2 FAIL) | Chạy pipeline và kiểm tra kết quả `success` trong file JSON |
| Xây dựng cơ chế Freshness SLA Monitoring | `src/observability/quality.py` (`evaluate_freshness_sla`, `build_freshness_report`) | Báo cáo `freshness_report.json` và `corrupted_freshness_report.json` ghi nhận tỷ lệ stale rows | Đối chiếu số ngày `age_days` với ngưỡng 180 ngày |
| Xâu chuỗi 6 bước Baseline Pipeline (Pha 1) | `src/pipelines/phase1.py`, `script/run_phase1.py` | Tạo đầy đủ 100% artifact từ Ingestion đến Evaluation và Báo cáo Markdown `phase1_report.md` | Lệnh `python script/run_phase1.py` |
| Xây dựng luồng thực nghiệm 3 trạng thái & Idempotent Repair | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Báo cáo so sánh đối đầu `data/reports/corruption_report.md` và file metrics 3 trạng thái | Lệnh `python script/run_corruption_flow.py` |

### Output cụ thể tạo ra và xác minh

Báo cáo đối đầu 3 trạng thái `data/reports/corruption_report.md` kết hợp cùng `data/quality/corrupted_quality_report.json`:
- Đã phát hiện chính xác 2 vi phạm critical expectations ở trạng thái Corrupted: `ExpectColumnValuesToBeUnique` trên trường `paper_id` (4 lỗi trùng lặp, 19.05%) và `ExpectColumnValueLengthsToBeBetween` trên trường `summary` (4 chuỗi rỗng `""`, 19.05%).
- Đo lường được sự suy giảm của RAG Agent: `retrieval_hit_rate` sụt giảm từ 1.0000 xuống 0.6000 (-40%), `mean_token_f1` giảm từ 1.0000 xuống 0.5817 (-41.83%), `mean_judge_score` giảm từ 5.00 xuống 3.20.
- Khôi phục hoàn toàn 100% các chỉ số (Hit Rate 1.0000, F1 1.0000, Judge Score 5.00/5.00, Quality Gate PASS 6/6) thông qua cơ chế phục hồi idempotent từ nguồn snapshot gốc.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong các hệ thống RAG phục vụ môi trường sản xuất (Production RAG), dữ liệu đưa vào vector store thường xuyên đối mặt với nguy cơ **Silent Failure** (lỗi thầm lặng): dữ liệu bị thiếu trường (null/empty), trùng lặp bản ghi, bị chèn ký tự rác hoặc quá hạn lỗi thời. Những lỗi này không làm sập ứng dụng hay ném ra ngoại lệ (exception) runtime, nhưng làm suy giảm nghiêm trọng độ chính xác của câu trả lời, gây ảo giác (hallucination) hoặc trả lời rỗng.

Nhiệm vụ của tôi là:
1. Thiết kế chốt kiểm định chất lượng (**Data Quality Gate**) và giám sát độ tươi mới (**Freshness SLA**) để tự động phát hiện mọi vi phạm cấu trúc và dữ liệu trước khi vector store phục vụ truy vấn.
2. Xây dựng luồng **Orchestration** tự động hóa việc vận hành pipeline baseline và luồng kiểm nghiệm 3 trạng thái (Baseline $\rightarrow$ Corrupted $\rightarrow$ Repaired) để chứng minh tính hiệu quả của Data Observability.

### Cách triển khai

1. **Kiến trúc Great Expectations 1.x Ephemeral Context**:
   - Sử dụng `gx.get_context(mode="ephemeral")` để kiểm tra trực tiếp DataFrame in-memory, tránh tạo gánh nặng cấu hình file tĩnh cồng kềnh.
   - Xây dựng Expectation Suite `papers_quality_suite_{report_name}` gồm 4 hàng rào kiểm định bắt buộc:
     - `ExpectTableRowCountToBeBetween(5, 5000)`: Kiểm tra tính đầy đủ về số lượng.
     - `ExpectColumnValuesToNotBeNull`: Áp dụng trên `paper_id`, `title`, `text_for_embedding`.
     - `ExpectColumnValuesToBeUnique`: Đảm bảo tính duy nhất tuyệt đối của mã định danh `paper_id` (DOI).
     - `ExpectColumnValueLengthsToBeBetween`: Đảm bảo độ dài tóm tắt `summary` $\ge 30$ ký tự, ngăn chặn văn bản rỗng làm hỏng vector embedding.
2. **Freshness SLA Monitoring**:
   - Đánh giá trường `age_days = (run_date - published).days`. Nếu `age_days > 180` ngày thì bản ghi bị đánh dấu là `stale`.
   - Tính toán tỷ lệ `stale_ratio = stale_rows / total_rows`. Nếu tỷ lệ vượt quá $25\%$ thì hệ thống cảnh báo vi phạm SLA (`is_fresh = False`).
3. **Idempotent Repair Flow**:
   - Thay vì chắp vá dữ liệu lỗi, hàm `repair_from_raw_snapshot()` đọc lại bản ghi snapshot nguyên bản từ `data/raw/crossref_records.json`, tái tạo hoàn toàn clean dataset và đánh chỉ mục lại vào collection cô lập `papers-repaired`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| **Input** | Pandas DataFrame (`papers_clean.csv`, `corrupted`, `repaired`), Đối tượng cấu hình `Settings` (chứa đường dẫn, ngưỡng 180 ngày, model config) |
| **Output** | File JSON chi tiết validation Great Expectations (`*_quality_report.json`), file JSON Freshness SLA (`*_freshness_report.json`), file Markdown báo cáo so sánh (`corruption_report.md`) |
| **Module phụ thuộc** | `src/ingestion/cleaning.py` (cung cấp clean DataFrame), `src/ingestion/corruption.py` (cung cấp corrupted DataFrame) |
| **Module sử dụng output** | `src/pipelines/corruption_flow.py`, `src/observability/reporting.py`, các dashboard quan sát dữ liệu |
| **Điều kiện lỗi cần xử lý** | DataFrame rỗng (0 dòng), thiếu cột `age_days` hoặc `summary`, xung đột tên Data Source trong Great Expectations context, phiên bản Python thiếu hỗ trợ `datetime.UTC` |

### Cách xác minh

```bash
# 1. Chạy xác minh Baseline Pipeline và Quality Gate
python script/run_phase1.py

# 2. Chạy xác minh luồng Corrupted -> Repair -> Comparison
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Baseline đạt 6/6 Expectations PASS, Freshness SLA PASS, Hit Rate 1.0000; Corrupted báo FAIL tại Quality Gate và Hit Rate tụt; Repaired phục hồi 6/6 PASS và Hit Rate trở lại 1.0000.
- **Kết quả thực tế:** Đúng 100% như mong đợi. Great Expectations bắt chính xác 2 lỗi ở Corrupted và phục hồi sạch sẽ ở Repaired.
- **Artifact/log:** `data/quality/baseline_quality_report.json`, `data/quality/corrupted_quality_report.json`, `data/quality/repaired_quality_report.json`, `data/reports/corruption_report.md`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp khởi tạo và quản lý Great Expectations (GX) trong hệ thống Data Pipeline: Sử dụng **File Data Context (GX truyền thống với thư mục cấu hình `great_expectations/` và file YAML)** hay **GX 1.x Ephemeral Context (quản lý in-memory theo phong cách Fluent API)**.
- **Các phương án đã cân nhắc:**
  - *Phương án 1 (File Data Context truyền thống):* Tạo thư mục `gx/` trên disk với các checkpoint và cấu hình datasource tĩnh. Ưu điểm là quen thuộc với các bài giảng GX cũ, nhưng nhược điểm là cấu hình phức tạp, dễ gãy vỡ đường dẫn tương đối khi chạy trên các máy khác nhau hoặc trong container/CI-CD, khó nhúng linh hoạt vào script python tự động.
  - *Phương án 2 (GX 1.x Ephemeral Context):* Khởi tạo context động trong bộ nhớ qua `gx.get_context(mode="ephemeral")`, thêm Pandas Data Source trực tiếp và định nghĩa Expectation Suite bằng code Python thuần túy.
- **Phương án đã chọn:** **Phương án 2 (Great Expectations 1.x Ephemeral Context)**.
- **Lý do:** Tối ưu hóa tính độc lập (portability), không phụ thuộc vào cấu trúc thư mục tĩnh của máy tính cá nhân, giảm thiểu xung đột git merge đối với các file config YAML tự sinh, đồng thời tốc độ thực thi kiểm tra dữ liệu cực nhanh (< 1 giây).
- **Bằng chứng quyết định phù hợp:** Toàn bộ pipeline chạy mượt mà trên môi trường sạch không cần khởi tạo `gx init`, các báo cáo validation JSON sinh ra đầy đủ siêu dữ liệu (`statistics`, `results`, `partial_unexpected_list`) được lưu trữ tập trung tại `data/quality/`.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ImportError: cannot import name 'UTC' from 'datetime'
  ```
  Và khi re-evaluate ở pha Repaired mà dùng chung collection name của ChromaDB, kết quả retrieval trả về cả các văn bản rác đã bị xóa ở pha Corrupted.
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_phase1.py` trên môi trường Python 3.10.
- **Nguyên nhân gốc:**
  1. Hằng số `datetime.UTC` là tính năng mới chỉ xuất hiện từ Python 3.11. Khi chạy trên môi trường Python 3.10, module `datetime` không có thuộc tính này dẫn đến crash ngay từ khâu nạp thư viện.
  2. ChromaDB `PersistentClient` lưu trữ index vĩnh viễn trên ổ cứng (`data/chroma/`). Nếu dùng chung một collection name giữa các lần chạy, ChromaDB không tự động xóa các ID bản ghi không còn trong DataFrame, tạo ra các "vector ma" (ghost vectors / orphaned embeddings).
- **Cách xử lý:**
  1. Thêm khối xử lý tương thích đa phiên bản Python:
     ```python
     try:
         from datetime import UTC
     except ImportError:
         from datetime import timezone
         UTC = timezone.utc
     ```
  2. Thiết kế tách biệt hoàn toàn không gian vector bằng 3 collection độc lập trong cấu hình `Settings`: `papers-baseline`, `papers-corrupted` và `papers-repaired`.
- **Cách xác minh sau khi sửa:** Pipeline chạy hoàn hảo trên Python 3.10, 3.11 và 3.12; các collection được kiểm tra độc lập và kết quả đánh giá Repaired đạt độ chính xác 100% không còn hiện tượng lẫn vector rác.
- **Điều học được:** Khi xây dựng Data Pipeline, luôn phải tính đến tính tương thích ngược của môi trường runtime (Python runtime matrix) và cơ chế lưu trữ có trạng thái (stateful persistence) của các hệ cơ sở dữ liệu vector.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu thô được truy vấn từ Crossref REST API qua HTTP GET với từ khóa học thuật và bộ lọc thời gian. Kết quả trả về được lưu dưới dạng snapshot bất biến `data/raw/crossref_records.json`. Tiếp theo, module Cleaning phân tích cú pháp, loại bỏ các thẻ XML/HTML trong abstract, ghép tác giả, tính số ngày tuổi `age_days` và tạo chuỗi tổng hợp `text_for_embedding`. Chuỗi văn bản sạch này được đưa qua mô hình nhúng (Gemini API hoặc MiniLM) để chuyển hóa thành vector ngữ nghĩa và nạp vào ChromaDB PersistentClient kèm theo metadata tương ứng.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Tập đánh giá gồm 10 câu hỏi thuộc 4 nhóm nghiệp vụ khác nhau. Mỗi câu hỏi đi kèm danh sách `ground_truth_doc_ids` (chính là DOI của bài báo chứa câu trả lời đúng) và `ground_truth` (văn bản đáp án chuẩn). Khi Agent thực hiện truy vấn, hệ thống đối chiếu:
   - *Retrieval Hit Rate*: Kiểm tra xem ít nhất một ID trong `ground_truth_doc_ids` có nằm trong top-4 tài liệu được ChromaDB trả về hay không.
   - *Mean Token F1*: Đo mức độ trùng khớp từ vựng giữa câu trả lời sinh ra của Agent và đáp án ground-truth.
   - *Judge Score / Accuracy*: Sử dụng LLM Judge chấm điểm trên thang điểm 5 về độ trung thực và tính đầy đủ so với ground-truth.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - *Quality checks (Great Expectations)*: Tập trung vào **tính toàn vẹn cấu trúc và quy tắc dữ liệu (Data Integrity, Validity & Completeness)**: kiểm tra số lượng dòng, cấm giá trị null, đảm bảo tính duy nhất của khóa chính `paper_id` và độ dài tối thiểu của tóm tắt.
   - *Freshness monitoring (Freshness SLA)*: Tập trung vào **chiều thời gian và tính cập nhật của kiến thức (Data Currency / Timeliness)**: tính toán độ trễ xuất bản của tài liệu so với thời điểm hiện tại và cảnh báo vi phạm SLA nếu tỷ lệ tài liệu lỗi thời vượt quá ngưỡng $25\%$.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính hợp lệ của phương pháp thực nghiệm khoa học: giữ cố định thước đo đánh giá (controlled test benchmark) nhằm cô lập biến số duy nhất cần khảo sát là **chất lượng dữ liệu và vector index**. Nếu đổi câu hỏi ở mỗi trạng thái, không thể kết luận được sự thay đổi của các chỉ số là do dữ liệu bị lỗi hay do câu hỏi mới khó hơn.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair được coi là thành công khi và chỉ khi:
   - *Về chất lượng dữ liệu (Artifact & Signal)*: `repaired_quality_report.json` đạt trạng thái **PASS** 100% (6/6 Expectations thành công, 0 thất bại), và `repaired_freshness_report.json` đạt trạng thái **FRESH** (tỷ lệ stale quay về 4.17%).
   - *Về hiệu năng hệ thống (Metrics)*: `repaired_metrics.json` ghi nhận `retrieval_hit_rate` phục hồi từ 0.6000 lên **1.0000**, `mean_token_f1` phục hồi từ 0.5817 lên **1.0000**, và `mean_judge_score` phục hồi từ 3.20 lên **5.00**.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | **1.0000** | **0.6000** | **1.0000** | Bị giảm 40% do 5 bài báo mới nhất bị xóa khỏi tập dữ liệu corrupted |
| `mean_token_f1` | **1.0000** | **0.5817** | **1.0000** | Giảm mạnh do thiếu ngữ cảnh truy xuất và bài báo bị xóa trắng abstract |
| `judge_accuracy` | **1.0000** | **0.6000** | **1.0000** | Tương đồng với Hit Rate, chứng minh vai trò quyết định của Retrieval đối với Generation |
| `mean_judge_score` | **5.00** | **3.20** | **5.00** | Điểm trung bình giảm sâu do nhiều câu trả lời rỗng hoặc sai lệch |
| Quality checks (GX 1.x) | **PASS** (6/6) | **FAIL** (4/6) | **PASS** (6/6) | Bắt chính xác 2 lỗi vi phạm tính unique của `paper_id` và độ dài `summary` |
| Freshness status | **FRESH** (4.17%) | **FRESH** (14.29%) | **FRESH** (4.17%) | Tỷ lệ stale tăng nhưng vẫn dưới 25% SLA; phục hồi hoàn toàn sau repair |

### Kết luận từ số liệu

1. **Chuỗi lỗi Corruption:**
   `drop_latest_records` (xóa 5 bài mới) & `blank_summary` (xóa tóm tắt) $\rightarrow$ Quality Gate báo **FAIL** (2 lỗi critical) và số lượng bản ghi giảm $\rightarrow$ `retrieval_hit_rate` giảm từ **1.0000** xuống **0.6000**, câu trả lời `q_summary_01` bị rỗng (`answer: ""`, score 1).
2. **Chuỗi khắc phục Repair:**
   `repair_from_raw_snapshot` (tái tạo từ snapshot gốc) $\rightarrow$ Quality Gate báo **PASS** toàn bộ 6/6 Expectations và tỷ lệ stale giảm về 4.17% $\rightarrow$ `retrieval_hit_rate` và `mean_token_f1` phục hồi tuyệt đối về **1.0000**, điểm Judge đạt **5.00/5.00**.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Hành động `drop_latest_records` (loại bỏ 20% bản ghi mới nhất) và `blank_summary` gây ảnh hưởng nặng nề nhất:
- `drop_latest_records` trực tiếp làm mất 4 trên 10 tài liệu mục tiêu của bài test (`q_summary_02`, `q_date_01`, `q_date_02`, `q_authors_01`), khiến cho vector search hoàn toàn bất lực trong việc tìm tài liệu đúng (Hit Rate tụt ngay 40%).
- `blank_summary` làm context trả về cho Agent bị rỗng hoàn toàn, khiến Agent không có thông tin để trả lời và sinh ra chuỗi rỗng.

**Kết quả nào khác với kỳ vọng ban đầu?**
Ban đầu nhóm dự đoán việc tiêm `inject_noise` (chèn chuỗi `@@###CORRUPTED_TEXT###@@`) sẽ làm sụp đổ hoàn toàn điểm số của câu hỏi liên quan. Tuy nhiên trên thực tế, mô hình embedding ngữ nghĩa dày đặc (Dense Embedding) vẫn có khả năng bắt được ngữ cảnh của phần văn bản còn lại xung quanh chuỗi nhiễu, do đó câu hỏi vẫn đạt retrieval hit. Điều này chứng minh rằng lỗi cấu trúc (xóa bản ghi, xóa trường rỗng) gây tổn thất lớn hơn nhiều so với việc chèn một lượng nhỏ nhiễu ký tự.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Pipeline không chỉ là việc nạp và chuyển đổi dữ liệu, mà phải được xây dựng dựa trên nguyên lý **Idempotency** (tính bất biến và khả năng tái lập kết quả) thông qua các snapshot dữ liệu thô không thể thay đổi.
2. **Về Data Observability:** Data Observability là lớp bảo vệ sống còn của hệ thống RAG. Việc giám sát dữ liệu bằng các bộ công cụ chuyên dụng như Great Expectations giúp bắt được lỗi dữ liệu ngay tại nguồn trước khi lỗi âm thầm lọt vào vector index.
3. **Về ảnh hưởng của Data đối với RAG Agent:** "Rác vào thì rác ra" (Garbage In, Garbage Out) - chất lượng và độ trung thực của RAG Agent phụ thuộc hoàn toàn vào độ sạch và tính toàn vẹn của corpus. Lỗi dữ liệu dẫn đến Silent Failure nguy hiểm hơn nhiều so với lỗi crash hệ thống vì người dùng cuối vẫn nhận được câu trả lời sai mà không hề hay biết.

### Nếu có thêm thời gian

Tôi sẽ triển khai một cơ chế **Fail-Closed Circuit Breaker** trực tiếp giữa tầng Data Quality Gate và Vector Indexing: Nếu Great Expectations trả về bất kỳ kỳ vọng nào thất bại (`success == False`), pipeline sẽ tự động kích hoạt Circuit Breaker, ngay lập tức chặn đứng việc ghi đè vào ChromaDB và gửi thông báo cảnh báo qua Slack/Webhook, thay vì tiếp tục index dữ liệu hỏng vào hệ thống phục vụ.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đào Quang Thái Anh  
**Ngày xác nhận:** 2026-09-26
