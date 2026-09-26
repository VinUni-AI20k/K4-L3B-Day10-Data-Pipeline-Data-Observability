# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | Nguyễn Hữu Chương |
| **MSSV** | 2A202602601 |
| **Khóa/Lớp** | K4/L3B |
| **Tên nhóm** | acer |
| **Vai trò chính** | RAG, Vector Database & Embedding |
| **Repository** | https://github.com/HoangVanSon252/K4-L3B-Day10-acer-Data-Pipeline-Data-Observability |
| **Ngày hoàn thành** | 2026-09-26 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **observability** | `quality.py`, `reporting.py` | `df` (DataFrame clean/corrupted/repaired), `Settings` | Báo cáo kiểm định `quality_report.json`, báo cáo tổng hợp Markdown `phase1_report.md`, `corruption_report.md` | Hoàn thành |
| **pipeline orchestration** | `phase1.py`, `corruption_flow.py`, `run_phase1.py`, `run_corruption_flow.py` | Configuration settings, snapshot thô `crossref_records.json` | Chuỗi 6 bước Baseline Pipeline & 10 bước Corruption-Recovery Flow hoàn chỉnh | Hoàn thành |
| **ingestion & cleaning & corruption** | `cleaning.py`, `corruption.py`, `crossref.py` | `PaperRecord` từ Crossref API, `df_clean` | Dataframe sạch `papers_clean.csv`, Dataframe bẩn `papers_corrupted.csv`, `corruption_log.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| :--- | :--- | :--- |
| **Sửa lỗi bẫy bất tương thích Timezone UTC** | `cleaning.py` | Đã sửa phép trừ datetime giữa `now_utc()` (tz-aware) và `published` (tz-naive), ngăn chặn hoàn toàn lỗi `TypeError: Cannot subtract tz-naive and tz-aware` trong Pandas. |
| **Xử lý JSON Serialization cho Pandas Timestamp** | `quality.py`, `utils.py` | Chuyển đổi các cột Timestamp/datetime thành định dạng chuỗi `YYYY-MM-DD` trước khi ghi file JSON và truyền vào Great Expectations. |
| **Reconfigure Console Standard Output Encoding** | Toàn bộ script pipeline | Thêm cấu hình `sys.stdout.reconfigure(encoding='utf-8')` để các emoji biểu thị log chạy mượt mà trên môi trường Windows Terminal (cp1252) không bị crash. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| **Thiết lập Observability Gate (GX 1.x)** | `src/observability/quality.py` (`run_data_quality_checks`) | 4 Expectation Suites kiểm tra row count, non-null, positive value, regex format | Executed trong `run_phase1.py` & `run_corruption_flow.py` |
| **Xây dựng Baseline Pipeline toàn tuyến (Phase 1)** | `src/pipelines/phase1.py` (`run_phase1_pipeline`) | File dữ liệu sạch `papers_clean.csv`, `baseline_metrics.json`, `phase1_report.md` | Lệnh: `python script/run_phase1.py` |
| **Xây dựng Corruption & Recovery Flow (Phase 2)** | `src/pipelines/corruption_flow.py` (`run_corruption_flow_pipeline`) | Bảng đối chiếu 3 trạng thái tại console và file báo cáo `data/reports/corruption_report.md` | Lệnh: `python script/run_corruption_flow.py` |

**Output cụ thể tạo ra hoặc giúp xác minh:**
Trong thư mục `data/`: đã tạo thành công các file `clean/papers_clean.csv`, Chroma Database vector index (`data/chroma/`), các file báo cáo tổng hợp `reports/phase1_report.md` và `reports/corruption_report.md` minh chứng cho toàn bộ tiến trình chạy pipeline.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng chốt kiểm soát chất lượng dữ liệu (Data Observability Gate) với Great Expectations 1.x và luồng tự phục hồi an toàn (Idempotent Repair) từ snapshot thô.

### Cách triển khai
1. **Quality Check (GX 1.x Ephemeral Context):** Sử dụng `gx.get_context(mode="ephemeral")`, định nghĩa Pandas Data Source & Asset, chạy Batch Validation với 4 quy tắc: `ExpectTableRowCountToBeBetween`, `ExpectColumnValuesToNotBeNull`, `ExpectColumnValuesToBeBetween`, và `ExpectColumnValuesToMatchRegex`.
2. **Synthetic Corruption Injection:** Viết hàm `corrupt_clean_dataframe` thực hiện 6 hành vi biến đổi dữ liệu bẩn: Drop 20% bản ghi mới nhất, Xóa rỗng summary, Chèn chuỗi rác `[CORRUPTED_NOISE...]`, Cắt tiêu đề dưới 8 ký tự, Lùi ngày xuất bản 365 ngày, và Nhân đôi dòng duplicate ID.
3. **Idempotent Repair:** Khi phát hiện dữ liệu hỏng, hàm `build_clean_dataframe()` được gọi lại với đầu vào là bản ghi thô gốc `crossref_records.json` để làm sạch lại từ đầu và ghi đè hoàn toàn Vector Collection trong ChromaDB.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | `PaperRecord` list từ Crossref API / Snapshot JSON (`data/raw/crossref_records.json`), `Settings`. |
| **Output** | Dataframe sạch/bẩn/phục hồi CSV & JSON, Metrics JSON (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`), Báo cáo Markdown `phase1_report.md`, `corruption_report.md`. |
| **Module phụ thuộc** | `core.config`, `ingestion.crossref`, `ingestion.cleaning`, `retrieval.index`, `evaluation.metrics`. |
| **Module sử dụng output** | `observability.reporting` (sinh báo cáo Markdown), `retrieval.index` (nhận dataframe để tạo Vector Store ChromaDB). |
| **Điều kiện lỗi cần xử lý** | Dữ liệu ngày tháng bất tương thích timezone, dữ liệu rỗng (null/empty string). |

### Cách xác minh

#### Lệnh 1: Baseline Pipeline Execution
```bash
python script/run_phase1.py
```

**Kết quả thực tế Log Output:**
```text
🚀 Running Phase 1 Baseline Pipeline...
📥 1. Ingest: Fetching raw records from Crossref API / Snapshot...
   -> Loaded 24 raw paper records.
🧹 2. Clean: Building clean dataframe...
   -> Cleaned dataframe saved to data\clean\papers_clean.csv (24 rows).
🔍 3. Index ChromaDB: Building Vector Store Index...
   -> Collection 'papers-baseline' built with 24 documents.
🧪 4. Sinh Testset: Generating benchmark evaluation set...
   -> Generated 10 test questions at data\eval\test_set.json.
📊 5. Đánh giá Baseline RAG: Measuring Hit Rate & Token F1...
   -> Hit Rate: 100.00%, Mean Token F1: 0.5000
   -> Baseline metrics saved to data\results\baseline_metrics.json
🛡️ 6. Observability Gate: Great Expectations Quality Gate & Freshness SLA...
   -> Quality Gate Status: True, Freshness SLA Status: True
📝 Xuất báo cáo Phase 1 Report...
   -> Report generated at: data\reports\phase1_report.md
✅ Phase 1 Baseline Pipeline completed successfully!
```

#### Lệnh 2: Corruption Flow Execution
```bash
python script/run_corruption_flow.py
```

**Kết quả thực tế Log Output:**
```text
🚀 Running Corruption & Recovery Flow...
📖 1. Loading baseline metrics and clean dataset...
💥 2. Injecting 6 corruption scenarios into clean dataset...
   -> Corrupted dataframe saved: 21 rows (Log: data\results\corruption_log.json)
🔍 3. Indexing corrupted dataset into ChromaDB...
📊 4. Evaluating corrupted RAG pipeline performance...
   -> Corrupted Hit Rate: 50.00%
🛡️ 5. Running Quality Gate & Freshness SLA on corrupted dataset...
   -> Quality Gate Status: False, Freshness SLA: True
🔧 6. Triggering Idempotent Repair from raw records snapshot...
   -> Repaired dataset restored: 24 rows.
🔍 7. Indexing repaired dataset into ChromaDB...
📊 8. Evaluating repaired RAG pipeline performance...
   -> Repaired Hit Rate: 100.00%
🛡️ 9. Running Quality Gate & Freshness SLA on repaired dataset...
📝 10. Generating 3-State Comparison Report (Baseline vs Corrupted vs Repaired)...
   -> Report generated at: data\reports\corruption_report.md
✅ Corruption & Recovery Flow completed successfully!
```

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn giữa kiến trúc Great Expectations 0.x File Data Context (tạo cây thư mục `great_expectations/` chứa cấu hình YAML) và chuẩn Great Expectations 1.x Ephemeral Context (chạy in-memory).
- **Các phương án đã cân nhắc:**
  - *Phương án A (GX File Data Context):* Tạo thư mục cấu hình tĩnh trên ổ đĩa.
  - *Phương án B (GX 1.x Ephemeral Context):* Cấu hình hoàn toàn bằng code Python, khởi tạo ngữ cảnh in-memory thông qua `gx.get_context(mode="ephemeral")`.
- **Phương án đã chọn:** Phương án B (GX 1.x Ephemeral Context).
- **Lý do:** Giảm phụ thuộc vào các file cấu hình YAML cồng kềnh, tránh phát sinh file rác trong source code.
- **Bằng chứng quyết định phù hợp:** Pipeline chạy cực nhanh, kiểm định dữ liệu trực tiếp trên Pandas DataFrame trong RAM và xuất báo cáo JSON/Markdown sạch sẽ mà không cần khởi tạo môi trường GX rườm rà.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: Cannot subtract tz-naive and tz-aware datetime-like objects.` tại dòng 37 file `src/ingestion/cleaning.py`.
- **Lệnh hoặc bước tái hiện:** `python script/run_phase1.py`
- **Nguyên nhân gốc:** Hàm `now_utc()` tạo đối tượng datetime có thông tin timezone UTC (`tz-aware`), trong khi `pd.to_datetime(df['published'])` mặc định tạo chuỗi DatetimeIndex không có timezone (`tz-naive`). Khi thực hiện phép trừ `(run_date - df['published'])` để tính `age_days`, Pandas throw ngoại lệ `TypeError`.
- **Cách xử lý:** Sử dụng tham số `utc=True` khi chuyển đổi datetime và tính toán `age_days` trước khi format về chuỗi ISO `YYYY-MM-DD`.
- **Cách xác minh sau khi sửa:** Lệnh `python script/run_phase1.py` chạy thành công 100% với exit code 0.
- **Điều học được:** Luôn đồng bộ chuẩn hóa Timezone (ưu tiên UTC) cho tất cả các cột datetime ngay từ bước Ingestion/Cleaning trong mọi Data Pipeline.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Raw JSON từ Crossref API được parse thành đối tượng `PaperRecord`.
   - `build_clean_dataframe()` chuẩn hóa văn bản, ép kiểu ngày, tính `age_days`, lọc trùng/rỗng và ghép nối chuỗi `text_for_embedding`.
   - `LocalEmbeddingIndex.build()` đưa chuỗi `text_for_embedding` qua model `SentenceTransformer` để sinh vector embeddings và nạp vào Vector Database (ChromaDB).

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - `build_test_set()` trích xuất các câu hỏi benchmark kèm `ground_truth_paper_id` từ tập dữ liệu sạch.
   - Với mỗi câu hỏi, hệ thống thực hiện Vector Search top-K tài liệu gần nhất trong ChromaDB. Nếu `ground_truth_paper_id` xuất hiện trong top-K, lượt tìm kiếm đó tính là Hit (`retrieval_hit_rate`). Answer Quality được đo bằng cách so sánh câu trả lời sinh ra với câu trả lời mẫu bằng thuật toán Token F1.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - *Quality checks (GX 1.x):* Kiểm tra tính toàn vẹn cấu trúc và logic dữ liệu (không rỗng, đúng định dạng DOI regex, số lượng dòng trong ngưỡng cho phép).
   - *Freshness monitoring:* Kiểm tra độ tươi / tính thời sự của dữ liệu dựa trên khoảng cách giữa thời điểm hiện tại và ngày xuất bản (`published`), xác định tỷ lệ dữ liệu bị lỗi thời (>180 ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Đây là nguyên tắc **Controlled Experiment** (Thực nghiệm có đối chứng). Việc giữ nguyên Test set cố định làm hằng số giúp đảm bảo biến độc lập duy nhất là *Chất lượng dữ liệu trong Vector DB*, từ đó đo lường chính xác mức độ suy giảm và phục hồi hiệu năng của hệ thống RAG.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - *Metric:* `retrieval_hit_rate` phục hồi từ 50.00% trở lại **100.00%**, `mean_token_f1` phục hồi từ 0.1800 trở lại **0.5000**.
   - *Artifact:* Trạng thái Great Expectations Quality Gate trong file `data/reports/corruption_report.md` và `repaired_metrics.json` chuyển từ `FAILED` về lại **`PASSED`**.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | --: | --: | --: | :--- |
| `retrieval_hit_rate` | **100.00%** | **50.00%** | **100.00%** | Dữ liệu bẩn làm sụt giảm nghiêm trọng 50% khả năng tìm đúng tài liệu. |
| `mean_token_f1` | **0.5000** | **0.1800** | **0.5000** | Chất lượng câu trả lời giảm sâu do ngữ cảnh truy xuất bị nhiễu/rỗng. |
| `judge_accuracy` | **50.00%** | **20.00%** | **50.00%** | LLM Judge đánh giá độ chính xác giảm mạnh khi dữ liệu bị tiêm rác. |
| `mean_judge_score` | **0.5000** | **0.2000** | **0.5000** | Điểm số đánh giá tổng thể giảm tương ứng với mức độ suy giảm dữ liệu. |
| Quality checks | **PASSED** | **FAILED** | **PASSED** | Data Quality Gate phát hiện chính xác sự cố dữ liệu bẩn. |
| Freshness status | **FRESH** | **FRESH** | **FRESH** | Chỉ số thời gian duy trì trạng thái đáp ứng SLA. |

### Kết luận từ số liệu

1. `[Tiêm 6 dạng lỗi dữ liệu bẩn]` ➔ `[Data Quality Gate lập tức cảnh báo FAILED]` ➔ `[Retrieval Hit Rate giảm 50%, Token F1 giảm 0.32]`.
2. `[Thực thi Idempotent Repair từ Snapshot thô]` ➔ `[Data Quality Gate phục hồi về PASSED]` ➔ `[Retrieval Hit Rate và Token F1 phục hồi 100% về mức Baseline]`.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Hành vi `blank_summary` (xóa tóm tắt) và `drop_latest_records` (bỏ rơi bài báo mới) ảnh hưởng nặng nề nhất. Khi `summary` bị xóa rỗng, vector embedding chỉ còn thông tin từ `title`, làm cho Semantic Distance giữa Vector Query và Document Embedding bị chênh lệch lớn, dẫn đến việc ChromaDB trả về sai tài liệu (Silent Failure).

**Kết quả nào khác với kỳ vọng ban đầu?**
Ban đầu kỳ vọng chỉ số `Freshness status` sẽ chuyển sang `STALE` khi tiêm lỗi `stale_date`. Tuy nhiên, do số lượng dòng bị lùi ngày chỉ chiếm tỷ lệ nhỏ trên tổng tập dữ liệu 24 dòng, chỉ số tổng thể vẫn nằm trong ngưỡng Freshness SLA chấp nhận được.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Tầm quan trọng của Data Observability Gate:** Việc cài đặt chốt kiểm định dữ liệu (Great Expectations) trước khi nạp vào Vector DB là bắt buộc để ngăn chặn các sự cố rác dữ liệu gây Silent Failure cho AI/RAG.
2. **Sức mạnh của Idempotent Self-Healing:** Thiết kế pipeline theo cơ chế Khả Nhiệm (Idempotent) dựa trên Raw Data Snapshot giúp hệ thống dễ dàng khôi phục 100% về trạng thái chuẩn mà không gây side-effect hay nhân bản dữ liệu rác.
3. **Mối quan hệ Garbage In - Garbage Out trong RAG:** Chất lượng câu trả lời của LLM phụ thuộc trực tiếp vào độ sạch của Vector Search Index; dữ liệu truy xuất bị hỏng sẽ kéo tụt ngay lập tức chỉ số F1 và Accuracy của Agent.

### Nếu có thêm thời gian

Triển khai **Automated Circuit Breaker** (Cầu chì tự động): Nếu Great Expectations Quality Gate trả về status `FAILED`, pipeline sẽ ngay lập tức dừng tiến trình Indexing vào ChromaDB, gửi cảnh báo cho Data Engineering team và tự động kích hoạt luồng Repair từ snapshot gần nhất.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [X] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [X] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [X] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [X] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [X] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [X] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hữu Chương  
**Ngày xác nhận:** 2026-09-26
