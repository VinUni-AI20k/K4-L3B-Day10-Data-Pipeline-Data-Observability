# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Hà Thị Mỹ Linh             |
| MSSV               | 2A202602619                     |
| Khóa/Lớp         | K4 - Lớp B              |
| Tên nhóm         | Enigma     |
| Vai trò chính    | Data Observability, Benchmark Evaluation & Quality Reporting (`quality.py`, `testset.py`, `corruption.py`, `reporting.py`) |
| Repository         | https://github.com/hungdq1306/K4-L3B-Day10-Enigma-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Great Expectations 1.x Quality Gate | `src/observability/quality.py`<br>• `run_data_quality_checks` | Cleaned / Corrupted DataFrame | `data/quality/baseline_quality_report.json`<br>`data/quality/corrupted_quality_report.json` | Hoàn thành |
| Freshness SLA Monitoring | `src/observability/quality.py`<br>• `evaluate_freshness_sla`<br>• `build_freshness_report` | DataFrame `age_days` | `data/quality/freshness_report.json` | Hoàn thành |
| Benchmark Test Set Generation | `src/evaluation/testset.py`<br>• `build_test_set` | Cleaned DataFrame 24 dòng | `data/eval/test_set.json` (10 câu hỏi chuẩn hóa qua 4 dạng nghiệp vụ) | Hoàn thành |
| Synthetic Corruption Suite | `src/ingestion/corruption.py`<br>• `corrupt_clean_dataframe` | Cleaned DataFrame | 6 kịch bản lỗi, `data/results/corruption_log.json` | Hoàn thành |
| Quality & Comparison Reporting | `src/observability/reporting.py`<br>• `generate_phase1_report`<br>• `generate_corruption_report` | Metrics & Quality reports | `data/reports/phase1_report.md`<br>`data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Xác thực chuẩn cấu trúc `text_for_embedding` | Đặng Quang Hưng (`cleaning.py`) | Đảm bảo trường embedding không null và tuân thủ schema 5 phần |
| Tích hợp chốt chặn Quality Gate vào luồng pipeline | Nguyễn Anh Tuấn (`phase1.py`, `corruption_flow.py`) | Quality Gate và Freshness SLA được kích hoạt tự động ở cả 2 phase |
| Kiểm thử suy giảm chỉ số RAG | Nguyễn Hữu Thành (`retrieval/index.py`) | Đo lường chính xác hiện tượng Silent Failure trên tập corrupted |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Xây dựng GX 1.x Quality Gate | `src/observability/quality.py` | 4 Expectations bắt buộc (6 checks chi tiết) | Cú pháp Ephemeral Context 1.x, `status = True` |
| Giám sát Freshness SLA | `src/observability/quality.py` | Cảnh báo khi tỷ lệ `age_days > 180` vượt 25% | Baseline: 4.2% (FRESH), Corrupted: 38.1% (STALE) |
| Sinh Benchmark Test Set | `src/evaluation/testset.py` | 10 câu hỏi bao quát `summary`, `authors`, `date`, `categories` | `test_set.json` sinh đủ 10 câu Ground Truth |
| Thực thi 6 dạng Corruption | `src/ingestion/corruption.py` | Tiêm đủ 6 lỗi dữ liệu thực tế | `corruption_log.json` ghi nhận đầy đủ 6 kịch bản |
| Báo cáo so sánh 3 trạng thái | `src/observability/reporting.py` | Bảng so sánh đa chiều Baseline vs Corrupted vs Repaired | `corruption_report.md` với phân tích nhân quả |

**Output cụ thể tạo ra:**
- `data/quality/baseline_quality_report.json` và `corrupted_quality_report.json`: Báo cáo chi tiết từng expectation (row count, non-null, unique, text length).
- `data/quality/freshness_report.json`: Theo dõi phân bố độ tuổi bài báo và cảnh báo vi phạm SLA.
- `data/eval/test_set.json`: 10 câu hỏi đánh giá chuẩn với ID, câu hỏi, ground truth và DOI mục tiêu.
- `data/results/corruption_log.json`: Nhật ký kiểm thử làm bẩn dữ liệu ghi rõ loại lỗi, số lượng và DOI bị tác động.
- `data/reports/phase1_report.md` và `data/reports/corruption_report.md`: Báo cáo đối chiếu 3 trạng thái.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Silent Failure trong AI/RAG**: Khi dữ liệu bị bẩn (mất bài mới, rỗng tóm tắt, trùng lặp, nhiễu), hệ thống AI vẫn sinh câu trả lời nhưng câu trả lời bị sai lệch hoặc ảo giác mà không báo lỗi runtime. Cần chốt chặn Data Observability để cảnh báo sớm.
2. **Nâng cấp Great Expectations 1.x**: Các phiên bản GX cũ dùng DataContext truyền thống gây lỗi cú pháp trên Python 3.11+. Cần chuyển đổi sang chuẩn `gx.get_context(mode="ephemeral")` hiện đại.
3. **Độc lập giữa Data Quality và Data Freshness**: Dữ liệu có thể hoàn toàn hợp lệ về schema nhưng bài báo đã quá hạn (stale), cần một cơ chế SLA riêng biệt giám sát độ tươi.

### Cách triển khai
1. **Great Expectations 1.x Ephemeral Context**:
   ```python
   context = gx.get_context(mode="ephemeral")
   data_source = context.data_sources.add_pandas(name="papers_source")
   data_asset = data_source.add_dataframe_asset(name="papers_asset")
   batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
   batch = batch_def.get_batch(batch_parameters={"dataframe": df})
   ```
   Thiết lập 4 nhóm Expectations:
   - `ExpectTableRowCountToBeBetween(5, 5000)`: Kiểm soát thể tích dữ liệu.
   - `ExpectColumnValuesToNotBeNull`: Đảm bảo `paper_id`, `title`, `text_for_embedding` không bị rỗng.
   - `ExpectColumnValuesToBeUnique`: Đảm bảo tính duy nhất của khóa chính `paper_id`.
   - `ExpectColumnValueLengthsToBeBetween`: Đảm bảo `summary` có độ dài tối thiểu 30 ký tự.

2. **Freshness SLA**:
   - Tính toán tỷ lệ bản ghi có `age_days > 180`.
   - Gắn cờ `is_fresh = False` và kích hoạt trạng thái `STALE` nếu tỷ lệ này vượt ngưỡng 25%.

3. **Corruption Suite & Log**:
   - Giả lập 6 lỗi: drop 20% bài mới nhất, xóa rỗng summary, chèn token rác, cắt ngắn tiêu đề (<8 ký tự), lùi ngày 365 ngày (stale), nhân đôi dòng (duplicate).
   - Tái tạo `text_for_embedding` và ghi log chi tiết vào `data/results/corruption_log.json`.

4. **3-State Markdown Reporting**:
   - Xuất bảng đối chiếu chi tiết giữa 3 trạng thái với các cột: Baseline, Corrupted, Repaired, Thay đổi và Mức phục hồi (Recovery %).

### Cách xác minh

```bash
# 1. Kiểm tra Quality Gate trên dữ liệu sạch
.venv\Scripts\python.exe -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Tín hiệu hoàn thành: Quality check status = {res[\"success\"]}')"

# 2. Kiểm tra sinh Test Set 10 câu hỏi
.venv\Scripts\python.exe -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"

# 3. Kiểm tra Corruption Suite
.venv\Scripts\python.exe -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Tín hiệu hoàn thành: Corrupted {len(c)} dòng')"
```

- **Kết quả thực tế:**
  ```text
  Tín hiệu hoàn thành: Quality check status = True
  Tín hiệu hoàn thành: Sinh được 10 câu hỏi test
  Tín hiệu hoàn thành: Corrupted 21 dòng
  ```

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp tích hợp Great Expectations giữa cấu hình file `great_expectations.yml` truyền thống và `ephemeral context` trên mã nguồn Python.
- **Phương án đã chọn:** Sử dụng Ephemeral Context (`gx.get_context(mode="ephemeral")`).
- **Lý do:** Tránh việc phụ thuộc vào các file cấu hình YAML cồng kềnh dễ bị lỗi path trên các hệ điều hành khác nhau (Windows vs Linux). Ephemeral Context cho phép cấu hình Data Source, Data Asset, Batch Definition và chạy Validation trực tiếp trên in-memory DataFrame trong mã Python, đảm bảo tính tự động hóa cao và chạy mượt mà trong pipeline CI/CD.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  AttributeError: module 'great_expectations' has no attribute 'DataContext'
  TypeError: ExpectationSuite() takes no arguments
  ```
- **Nguyên nhân gốc:** Mã nguồn ban đầu tham chiếu theo cú pháp cũ của Great Expectations 0.18, trong khi môi trường đang cài đặt GX 1.23+. Phiên bản 1.x đã tái cấu trúc hoàn toàn hệ thống API sang hướng declarative với `data_sources.add_pandas()` và `batch.validate(expectation)`.
- **Cách xử lý:** Viết lại toàn bộ hàm `run_data_quality_checks` theo đúng chuẩn GX 1.x: khởi tạo ephemeral context, tạo Pandas data source, whole dataframe batch definition và dùng `batch.validate(exp)`.
- **Cách xác minh sau khi sửa:** Chạy kiểm thử xác minh thành công, kết quả validate trả về `success = True` với đầy đủ kết quả đo lường từng expectation.

## 7. Hiểu biết về luồng end-to-end

1. **Chu trình Data Observability:** Bắt đầu từ khi dữ liệu sạch được sinh ra, Quality Gate chặn trước kho vector ChromaDB để kiểm tra tính toàn vẹn (integrity) và độ tươi (freshness). Nếu dữ liệu không đạt chuẩn, pipeline phải báo động ngay.
2. **Tác động của Data Corruption tới RAG:** Khi bỏ rơi 20% bài báo mới nhất, các truy vấn về chủ đề mới sẽ bị Retrieval Miss (`retrieval_hit_rate` giảm từ 100% xuống 60-70%). Khi tóm tắt bị làm rỗng hoặc chèn chuỗi rác, mô hình trả lời sai lệch (`mean_token_f1` giảm từ 1.0000 xuống 0.8000).
3. **Ý nghĩa của Idempotent Repair:** Phục hồi từ raw snapshot bất biến đảm bảo đưa hệ thống về trạng thái chuẩn mà không sinh ra phụ phẩm hay rác dữ liệu. Bảng đối chiếu 3 trạng thái chứng minh hiệu năng hệ thống AI đã phục hồi 100%.

## 8. Phân tích kết quả

### Metrics chính (Tri-State Benchmark)

| Metric / Signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `retrieval_hit_rate` | 100.00% | 70.00% | 100.00% | -30.00% | 100.0% |
| `mean_token_f1` | 1.0000 | 0.8000 | 1.0000 | -0.2000 | 100.0% |
| `judge_accuracy` | 100.00% | 80.00% | 100.00% | -20.00% | 100.0% |
| `mean_judge_score` | 5.00 / 5.0 | 4.20 / 5.0 | 5.00 / 5.0 | -0.80 | 100.0% |
| `Quality Gate (GX 1.x)` | **PASSED** | **FAILED** | **PASSED** | Vi phạm 2 checks | 100.0% |
| `Freshness SLA` | **FRESH** | **STALE** | **FRESH** | 38.1% quá hạn (>25%) | 100.0% |

### Kết luận từ số liệu
1. Dữ liệu lỗi tác động tiêu cực ngay lập tức lên chất lượng của RAG Agent (Hit Rate và Token F1 sụt giảm rõ rệt).
2. Quality Gate chuẩn GX 1.x và Freshness SLA bắt chính xác 100% các vi phạm schema và vi phạm thời gian.
3. Sau khi phục hồi, toàn bộ chỉ số đạt mức 100%, chứng minh cơ chế Self-Healing hoạt động hiệu quả.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Quan sát dữ liệu (Data Observability) là tấm khiên bảo vệ AI:** Không thể tin tưởng hoàn toàn dữ liệu đầu vào mà không có các cổng kiểm định tự động (Quality Gates).
2. **Khái niệm Silent Failure:** AI không báo lỗi (crash) khi dữ liệu sai, nó chỉ âm thầm trả lời ngô nghê. Đây là dạng lỗi nguy hiểm nhất trong môi trường sản xuất.
3. **Chuẩn hóa công cụ hiện đại:** Làm chủ Great Expectations 1.x với ephemeral context giúp xây dựng pipeline kiểm định linh hoạt và đáng tin cậy.

### Nếu có thêm thời gian
Thiết lập Dashboard theo dõi trực quan bằng Streamlit hoặc Grafana để hiển thị biến động của các chỉ số Data Quality và Drift Score theo thời gian thực.

## 10. Cam kết của thành viên
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hà Thị Mỹ Linh  
**Ngày xác nhận:** 2026-09-26

