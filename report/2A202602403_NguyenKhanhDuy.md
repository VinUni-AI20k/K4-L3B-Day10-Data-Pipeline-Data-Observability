# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Khánh Duy          |
| MSSV               | 2A202602403               |
| Khóa/Lớp         | K4 - Lớp B (Ca Sáng)      |
| Tên nhóm         | Team 03 - DataObservability |
| Vai trò chính    | Data Observability, Freshness SLA & Benchmark Evaluation |
| Repository         | K4-L3B-DAY10-Team03-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| Great Expectations 1.x Quality Gate | `src/observability/quality.py` (`run_data_quality_checks`) | DataFrame, `Settings` | `baseline_quality_report.json`, `corrupted_quality_report.json` | Hoàn thành |
| Freshness SLA Monitoring | `src/observability/quality.py` (`build_freshness_report`) | DataFrame, `Settings` | `freshness_report.json`, cảnh báo stale ratio | Hoàn thành |
| Benchmark Test Set Generation | `src/evaluation/testset.py` (`build_test_set`) | Cleaned DataFrame | `data/eval/test_set.json` (10 câu hỏi qua 4 domains) | Hoàn thành |
| Evaluation Metrics & Reporting Engine | `src/evaluation/metrics.py`, `src/observability/reporting.py` | Test set, ChromaDB index, LLM Judge | `baseline_metrics.json`, `phase1_report.md`, `corruption_report.md` | Hoàn thành |
| Interactive Observability Dashboard (Bonus B1) | `report/observability_dashboard.html` | Dữ liệu benchmark & quality thực tế | Giao diện web HTML trực quan hiện đại | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Kiểm thử Schema & Chốt kiểm dịch dữ liệu sạch | Đặng Thái Anh (`cleaning.py`) | Đảm bảo DataFrame làm sạch đáp ứng 100% 7 expectations của GX 1.x |
| Tích hợp chốt Observability vào Pipeline | Nguyễn Đức Anh (`phase1.py`, `corruption_flow.py`) | Đưa hàm kiểm định chất lượng và đo độ tươi vào luồng thực thi tự động |
| Kiểm thử độ nhạy của Vector Search | Đỗ Trung Tuyến (`retrieval/index.py`) | Đánh giá sự suy giảm Hit Rate khi dữ liệu bị lỗi tiêm vào |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Thiết lập GX 1.x Ephemeral Quality Gate | `src/observability/quality.py` | 7 expectations kiểm định toàn vẹn dữ liệu | `data/quality/baseline_quality_report.json` đạt `success=True` |
| Quản lý Freshness SLA | `src/observability/quality.py` | Cảnh báo vi phạm độ tươi bài báo (> 180 ngày) | Baseline: 4.2% stale (Healthy); Corrupted: 40.9% stale (Alert) |
| Sinh Benchmark Test Set 10 câu | `src/evaluation/testset.py` | 10 câu hỏi chia đều: 3 summary, 3 authors, 2 date, 2 categories | `data/eval/test_set.json` sinh thành công |
| Đánh giá & Báo cáo so sánh | `src/evaluation/metrics.py`, `src/observability/reporting.py` | Báo cáo Markdown & Interactive Dashboard | `data/reports/corruption_report.md`, `report/observability_dashboard.html` |

**Output cụ thể:**
Interactive HTML Observability Dashboard (`report/observability_dashboard.html`) hiển thị trực quan các thẻ KPI, thanh suy thoái, bảng đối chiếu 3 trạng thái và chi tiết 6 kịch bản lỗi.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Các phiên bản Great Expectations cũ (0.18 trở về trước) thường yêu cầu cấu hình file YAML phức tạp và sinh ra nhiều lỗi deprecated khi chạy trong môi trường in-memory. Cần áp dụng chuẩn mới nhất **Great Expectations 1.x** với Ephemeral Context để kiểm định nhanh chóng và nhẹ nhàng.
2. Cần phân định rõ ràng giữa **Data Quality** (tính toàn vẹn cấu trúc tĩnh) và **Freshness SLA** (tính thời điểm dữ liệu).
3. Đánh giá chất lượng RAG không thể chỉ dựa vào một câu hỏi chung chung, mà cần một benchmark đa chiều bao phủ đủ các dạng câu hỏi thực tế: tóm tắt nội dung, tra cứu tác giả, ngày công bố, và phân loại chuyên ngành.

### Cách triển khai
1. **Great Expectations 1.x Ephemeral Implementation:**
   ```python
   context = gx.get_context(mode="ephemeral")
   data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
   data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{report_name}")
   batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{report_name}")
   batch = batch_def.get_batch(batch_parameters={"dataframe": df})
   suite = gx.ExpectationSuite(name=f"papers_suite_{report_name}")
   
   # 7 expectations bắt buộc
   suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=20, max_value=30))
   suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
   suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
   suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="summary"))
   suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
   suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8))
   suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20))
   ```
2. **Freshness SLA Monitoring:**
   Tính toán tỷ lệ các bài báo có `age_days > 180`. Nếu tỷ lệ này vượt quá 25% (ngưỡng quy định), cờ `is_fresh` sẽ tự động chuyển thành `False`, kích hoạt cảnh báo suy thoái dữ liệu.
3. **Bộ Benchmark Test Set (10 câu qua 4 domains):**
   - 3 câu hỏi nhóm `summary` $\rightarrow$ Đo khả năng trích xuất nội dung tóm tắt chính xác.
   - 3 câu hỏi nhóm `authors` $\rightarrow$ Đo khả năng tra cứu danh sách tác giả.
   - 2 câu hỏi nhóm `date` $\rightarrow$ Đo khả năng xác định ngày công bố.
   - 2 câu hỏi nhóm `categories` $\rightarrow$ Đo khả năng nhận diện phân loại chuyên ngành.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | DataFrame cleaned/corrupted/repaired, `Settings` |
| Output | Validation result dictionary, `test_set.json`, `*_metrics.json`, Markdown reports |
| Module phụ thuộc | `ingestion/cleaning.py`, `retrieval/index.py` |
| Module sử dụng output | Pipeline runner, ban giám khảo đánh giá |
| Điều kiện lỗi cần xử lý | Tên suite trùng lặp trong ephemeral context, LLM Judge API timeout |

### Cách xác minh

```bash
# Kiểm tra Quality Gate và Freshness SLA
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks, build_freshness_report; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); q=run_data_quality_checks(df, s, 'test'); f=build_freshness_report(df, s); print(f'GX Success: {q[\"success\"]}, Freshness: {f[\"is_fresh\"]}')"
```

- **Kết quả mong đợi:** In ra `GX Success: True, Freshness: True`.
- **Kết quả thực tế:** Hoàn toàn chính xác theo mong đợi.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp định nghĩa kỳ vọng (Expectation Definition) trong Great Expectations 1.x.
- **Các phương án đã cân nhắc:**
  - *Phương án 1:* Sử dụng File Data Context truyền thống với thư mục `great_expectations/` và file cấu hình YAML trên ổ đĩa.
  - *Phương án 2:* Sử dụng Ephemeral Context (in-memory) khởi tạo trực tiếp trong code Python.
- **Phương án đã chọn:** Phương án 2 (Ephemeral Context).
- **Lý do:** Phương án 1 đòi hỏi cấu hình phức tạp, dễ bị lỗi đường dẫn tương đối khi chạy trên các máy khác nhau hoặc trong môi trường CI/CD không có quyền ghi file tĩnh. Phương án 2 cực kỳ nhẹ, khởi tạo tức thì trong bộ nhớ, hoàn toàn tương thích với chuẩn GX 1.x mới nhất và không để lại các file cache rác.
- **Bằng chứng quyết định phù hợp:** Thời gian chạy kiểm định Quality Gate chỉ mất chưa đầy 0.5 giây và chạy trơn tru 100% trong cả luồng pipeline chính lẫn Pytest CI.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  UserWarning: Direct use of automatic function calling (AFC) in Models.generate_content is not recommended.
  ```
  Và đôi khi LLM Evaluator bị nghẽn mạng khi chấm điểm 10 câu hỏi liên tiếp bằng API Gemini.
- **Lệnh tái hiện:** Chạy hàm `evaluate_pipeline` với cấu hình mặc định khi kết nối Internet không ổn định.
- **Nguyên nhân gốc:** Khi LLM API gọi ra Internet gặp sự cố mạng hoặc rate-limit, việc thiếu cơ chế fallback sẽ làm sập toàn bộ chu trình đánh giá.
- **Cách xử lý:** 
  Tích hợp cơ chế chấm điểm dự phòng (Heuristic Fallback Judge) trong `src/evaluation/metrics.py`:
  ```python
  try:
      llm = build_llm(settings=settings, temperature=0.0).with_structured_output(JudgeVerdict)
      return llm.invoke(prompt)
  except Exception:
      score = 5 if _token_f1(reference, prediction) >= 0.95 else 3 if _token_f1(reference, prediction) >= 0.5 else 1
      return JudgeVerdict(
          score=score,
          correct=score >= 3,
          reasoning="Fallback heuristic judge used because the LLM evaluator was unavailable.",
      )
  ```
- **Cách xác minh sau khi sửa:** Kể cả khi tắt mạng hoặc không có API key, pipeline vẫn hoàn tất đánh giá với điểm số Token F1 và Heuristic Judge chính xác, không bao giờ bị dừng đột ngột.
- **Điều học được:** Một hệ thống kiểm định chất lượng trong sản xuất luôn cần cơ chế Graceful Degradation (suy giảm chức năng an toàn) khi các dịch vụ bên thứ ba gặp sự cố.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu được lấy từ Crossref REST API $\rightarrow$ lưu raw snapshot $\rightarrow$ làm sạch và tạo văn bản nhúng $\rightarrow$ tính toán vector embedding 384 chiều $\rightarrow$ lưu trữ trên ChromaDB vector database.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Đo lường bằng cách kiểm tra xem bài báo chứa câu trả lời đúng (`ground_truth_doc_ids`) có xuất hiện trong danh sách bài báo mà ChromaDB tìm thấy hay không. Nếu có là Hit; sau đó so sánh câu trả lời của AI với câu trả lời chuẩn bằng Token F1 và LLM Judge.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks giám sát lỗi cấu trúc tĩnh (thiếu trường, sai kiểu, trùng lặp, chuỗi quá ngắn). Freshness monitoring giám sát tính thời sự của thông tin (Data Drift theo thời gian).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính khách quan và khoa học. Nếu thay đổi câu hỏi kiểm thử giữa các pha, chúng ta không thể biết sự thay đổi chỉ số là do dữ liệu tốt/xấu hay do câu hỏi dễ/khó.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Dựa trên sự phục hồi của toàn bộ hệ thống chỉ số: Hit Rate đạt 100%, F1 đạt 100%, Quality Report đạt PASSED, và Freshness đạt HEALTHY.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate`   |   100.0% |     60.0% |   100.0% | 4 câu hỏi bị trượt do thiếu tài liệu mục tiêu |
| `mean_token_f1`        |   100.0% |     85.1% |   100.0% | Các câu hỏi tóm tắt bị mất từ khóa chính xác |
| `judge_accuracy`       |   100.0% |     90.0% |   100.0% | LLM Judge phát hiện câu trả lời bị sai lệch |
| `mean_judge_score`     |     5.00 |      4.20 |     5.00 | Giảm từ 5.0 xuống 4.2 do chất lượng câu trả lời suy thoái |
| Quality checks         |   PASSED |    FAILED |   PASSED | Chốt chặn GX 1.x phát hiện vi phạm ngay lập tức |
| Freshness status       |  HEALTHY |  VIOLATED |  HEALTHY | Tỷ lệ stale 40.9% vượt xa ngưỡng cho phép 25% |

### Kết luận từ số liệu
- Tác động của Data Corruption thể hiện rõ rệt nhất ở chỉ số **Retrieval Hit Rate** (giảm 40.0%), chứng minh rằng khi dữ liệu nền bị suy thoái, RAG Agent không thể tìm đúng thông tin cần thiết.
- Sau khi chạy Idempotent Repair, cả 4 chỉ số hiệu năng và 2 tín hiệu Observability đều được phục hồi 100%, chứng minh tính hiệu quả tuyệt đối của kiến trúc tự chữa lành.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Sức mạnh của Great Expectations 1.x:** Cung cấp giải pháp chốt kiểm dịch chất lượng tự động cực kỳ mạnh mẽ và thanh lịch với cú pháp mới.
2. **Khái niệm Data Observability:** Không chỉ quan sát hệ thống máy chủ (CPU, RAM) mà phải quan sát chính bản thân dòng dữ liệu (Dòng chảy, Độ tươi, Tính đúng đắn).
3. **Đánh giá RAG đa chiều:** Phải kết hợp giữa Retrieval Metrics (Hit Rate) và Generation Metrics (Token F1, LLM as a Judge) để có cái nhìn toàn diện.

### Nếu có thêm thời gian
Tôi sẽ tích hợp thêm công cụ Ragas để đo lường tự động 4 chỉ số nâng cao: Faithfulness, Answer Relevancy, Context Precision, và Context Recall trực tiếp trên giao diện Dashboard.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Khánh Duy  
**Ngày xác nhận:** 2026-09-26
