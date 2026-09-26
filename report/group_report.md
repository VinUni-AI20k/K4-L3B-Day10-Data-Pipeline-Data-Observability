# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| :--- | :--- |
| **Khóa/Lớp** | K4/L3B |
| **Tên nhóm** | acer |
| **Repository** | https://github.com/HoangVanSon252/K4-L3B-Day10-acer-Data-Pipeline-Data-Observability |
| **Ngày hoàn thành** | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | :--- | :--- | :--- | :--- |
| 1 | Hoàng Văn Sơn | 2A202602375 | Pipeline Integrator & Data Recovery | `phase1.py`, `crossref.py`, `cleaning.py` |
| 2 | Nguyễn Hữu Chương | 2A202602601 | RAG, Vector Database & Embedding | `quality.py`, `phase1.py`, `corruption_flow` |
| 3 | Phạm Quốc Đạt | 2A202602384 | Observability & Evaluation | `corruption.py`, `testset.py` |

---

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành 100% hai giai đoạn chính của dự án Data Pipeline & Observability cho hệ thống RAG: Phase 1 (Baseline Pipeline toàn tuyến) và Phase 2 (Data Corruption Suite & Idempotent Self-Healing Flow).

Ở Phase 1, Baseline Pipeline đã thu thập 24 bản ghi từ Crossref API (snapshot tại `data/raw/`), làm sạch và xuất tập dữ liệu `data/clean/papers_clean.csv`, đánh chỉ mục Vector trên ChromaDB, sinh tập testset 10 câu hỏi (`data/eval/test_set.json`), đạt chỉ số Baseline **Retrieval Hit Rate 100.00%** và **Token F1 0.5000**, đồng thời thiết lập chốt kiểm định Great Expectations 1.x (PASSED) và Freshness SLA (FRESH).

Ở Phase 2, nhóm tiêm 6 dạng sự cố dữ liệu thực tế (Drop bản ghi mới, Xóa tóm tắt, Tiêm rác, Cắt ngắn tiêu đề, Lùi ngày, Trùng lặp). Trong đó, sự cố **xóa rỗng summary** và **drop bản ghi mới nhất** gây ảnh hưởng nặng nề nhất, khiến Quality Gate lập tức báo `FAILED` và kéo tụt Retrieval Hit Rate từ **100% xuống 50%** (xảy ra hiện tượng RAG Silent Failure).

Cơ chế **Idempotent Repair** khôi phục hoàn toàn dữ liệu từ snapshot thô gốc, đưa các chỉ số Hit Rate và Token F1 **phục hồi 100% về mức Baseline** và Quality Gate trở lại `PASSED`.

Giới hạn quan trọng nhất hiện tại là hệ thống đánh giá LLM Judge đang dùng cơ chế Heuristic Fallback in-memory; hướng cải thiện tiếp theo là tích hợp Live LLM API kèm cơ chế Automated Circuit Breaker để tự động ngắt ghi dữ liệu khi Quality Gate báo lỗi.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API / Snapshot (data/raw/)
    -> raw response/raw records (crossref_records.json)
    -> cleaning và data modeling (src/ingestion/cleaning.py)
    -> embedding + ChromaDB index (papers-baseline)
    -> evaluation baseline (retrieval_hit_rate: 100%)
    -> quality/freshness reports (GX 1.x Ephemeral Context)
    -> corruption (src/ingestion/corruption.py - 6 scenarios)
    -> re-index và re-evaluate (corrupted_hit_rate: 50%, GX: FAILED)
    -> repair từ dữ liệu nguồn (repair_from_raw_snapshot)
    -> comparison report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối module | Input nhận vào | Xử lý chính trong code | Output / Artifact bàn giao | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Crossref REST API / Offline Snapshot | Thu thập metadata bài báo khoa học, parse JSON payload, lưu trữ snapshot thô | `data/raw/crossref_records.json` | Hoàng Văn Sơn |
| **Cleaning** | Raw `PaperRecord` list | Stripping khoảng trắng, ép kiểu datetime UTC, tính `age_days`, tạo `text_for_embedding`, lọc null & duplicate | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` | Hoàng Văn Sơn |
| **Embedding & Indexing** | Cleaned Dataframe | Sinh vector embedding bằng model `all-MiniLM-L6-v2`, khởi tạo ChromaDB Collection, lưu index & metadata | Thư mục Vector DB ChromaDB | Nguyễn Hữu Chương |
| **Evaluation** | Cleaned Dataframe & ChromaDB Index | Sinh bộ câu hỏi Q&A benchmark (`build_test_set`), Vector Search retrieval, tính Hit Rate, Token F1 & Heuristic Judge | `data/eval/test_set.json` | Phạm Quốc Đạt |
| **Observability** | Cleaned Dataframe & Settings | Khởi tạo GX 1.x Ephemeral Context, chạy 4 Expectation Suites, đo Freshness SLA | `data/quality/baseline_quality_report.json` | Phạm Quốc Đạt |
| **Corruption & Repair** | Cleaned Dataframe & Raw Snapshot | Tiêm 6 dạng sự cố bẩn & Khôi phục idempotent từ snapshot thô gốc | `data/clean/papers_corrupted.csv`<br>`data/clean/papers_repaired.csv` | Hoàng Văn Sơn |
| **Orchestration** | System Configuration Settings | Xâu chuỗi 6 bước Phase 1 Baseline & 10 bước Phase 2 Corruption Flow, xuất báo cáo Markdown | Báo cáo Markdown tổng hợp (`data/reports/`) | Hoàng Văn Sơn |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| :--- | :--- |
| `LLM_PROVIDER` | `mock` |
| `LLM_MODEL` |  |
| `Embedding model` | `sentence-transformers/all-MiniLM-L6-v2` |
| `Số lượng Crossref records` | `24` |
| `Retrieval top_k` | `3` |
| `Freshness threshold` | `180 ngày` |
| `Random seed` | `42` |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:
```bash
python script/run_phase1.py
```

Corruption flow:
```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| :--- | :--- | :--- | :--- |
| **Baseline pipeline** | Thành công | 2026-09-26 11:16 | `data/reports/phase1_report.md` (Hit Rate: 100%) |
| **Corruption flow** | Thành công | 2026-09-26 11:17 | `data/reports/corruption_report.md` (3-State Comparison) |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Source** | Crossref REST API (`https://api.crossref.org/works`) |
| **Query/filter** | `query="RAG data pipeline observability"`, `rows=30` |
| **Thời điểm lấy dữ liệu** | 2026-09-26T03:49:00Z |
| **Số record nhận được** | 24 records |
| **Cơ chế retry/backoff** | Fallback tự động đọc snapshot local tại `data/raw/crossref_records.json` khi ngắt kết nối mạng |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| :--- | :--- | :--- | :--- | :--- |
| `paper_id` | String | Có | DOI định danh bài báo | Drop record nếu null/rỗng |
| `title` | String | Có | Tiêu đề bài báo | Strip khoảng trắng; drop nếu null |
| `summary` | String | Có | Tóm tắt nội dung | Strip khoảng trắng; drop nếu null |
| `published` | String (ISO) | Không | Ngày xuất bản (`YYYY-MM-DD`) | `pd.to_datetime(errors="coerce")`, gán rỗng |
| `updated` | String (ISO) | Không | Ngày cập nhật gần nhất | `pd.to_datetime(errors="coerce")`, gán rỗng |
| `authors` | List[String] | Không | Danh sách tác giả | Chuyển thành chuỗi `authors_joined` phân cách dấu phẩy |
| `categories` | List[String] | Không | Danh mục chủ đề | Chuyển thành chuỗi `categories_joined` phân cách dấu phẩy |
| `age_days` | Integer | Có | Tuổi của bài báo tính theo ngày | Tính theo `(now_utc - published)`, clip `>= 0` |
| `text_for_embedding` | String | Có | Chuỗi định dạng ghép nối chuẩn bị cho Vector DB | Ghép `Title + Authors + Categories + Summary` |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| :--- | :--- | --: | :--- |
| Loại bỏ dòng thiếu `paper_id`, `title` hoặc `summary` | Completeness / Validity | 0 | Code filter `dropna` & GX Check |
| Chuẩn hóa định dạng Datetime UTC & tính `age_days` | Timeliness / Accuracy | 24 | Cột `age_days >= 0` trong `papers_clean.csv` |
| Ghép nối trường dữ liệu thành `text_for_embedding` | Representation / Usability | 24 | Cột `text_for_embedding` trong CSV/JSON |
| Deduplicate loại bỏ trùng lặp `paper_id` | Uniqueness | 0 (Baseline) / 1 (Corrupted) | `drop_duplicates(subset=['paper_id'])` |

**Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:**
- **Document ID:** Sử dụng trực tiếp mã DOI chuẩn hóa của Crossref (ví dụ: `10.1145/3637528.3671801`).
- **`text_for_embedding`:** Được tạo bằng cách ghép nối cấu trúc văn bản: `"Title: " + title + "\nAuthors: " + authors_joined + "\nCategories: " + categories_joined + "\nSummary: " + summary`.
- **`age_days`:** Lấy ngày chạy pipeline (`run_date` UTC) trừ đi `published_dt` UTC, đổi sang đơn vị ngày (`.dt.days`), thế chỗ giá trị thiếu bằng `0` và hạ ngưỡng dưới `clip(lower=0)`.

---

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| :--- | :--- |
| **Số câu hỏi** | 10 câu hỏi benchmark |
| **Các `question_type`** | `author_inquiry`, `publication_date`, `category_inquiry`, `summary_inquiry` |
| **Ground-truth document ID** | Trích xuất trực tiếp `paper_id` tương ứng từ tập `papers_clean.csv` |
| **Embedding model** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector store/collection** | ChromaDB |
| **Retrieval `top_k`** | `3` |
| **LLM provider/model** | `mock` |
| **Test set dùng chung cho ba trạng thái** | `data/eval/test_set.json` |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**
Test set được giữ nguyên để tuân thủ nguyên tắc **Controlled Experiment** (Thực nghiệm đối chứng). Việc giữ bộ câu hỏi và ground-truth cố định làm hằng số giúp đảm bảo biến độc lập duy nhất là *Chất lượng dữ liệu trong Vector DB*, từ đó phản ánh trung thực mức độ sụt giảm hiệu năng khi bị tiêm lỗi và khả năng phục hồi khi repair.

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| :--- | :--- | :--- | :--- |
| **Raw response/records** | `data/raw/crossref_records.json` | Có | Snapshot 24 bài báo thô |
| **Cleaned dataset** | `data/clean/papers_clean.csv` | Có | Dataframe 24 dòng sạch |
| **Embedding manifest/index** | `data/embeddings/papers_embeddings.json` | Có | Manifest lưu thông tin embeddings |
| **Evaluation set** | `data/eval/test_set.json` | Có | Tập 10 câu hỏi benchmark |
| **Baseline metrics** | `data/results/baseline_metrics.json` | Có | Lưu chỉ số Hit Rate & Token F1 |
| **Quality/freshness** | `data/quality/baseline_freshness_report.json` | Có | Báo cáo Freshness SLA |
| **Baseline report** | `data/reports/phase1_report.md` | Có | Báo cáo Markdown tổng hợp Phase 1 |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| :--- | --: | :--- |
| `retrieval_hit_rate` | **100.00%** | 10/10 câu hỏi tìm thấy đúng tài liệu ground-truth trong Top-3 |
| `mean_token_f1` | **0.5000** | Độ tương đồng từ vựng trung bình giữa câu trả lời trích xuất và đáp án mẫu |
| `judge_accuracy` | **50.00%** | Tỷ lệ câu trả lời đạt điểm đánh giá >= 3 |
| `mean_judge_score` | **3.0000** | Điểm số đánh giá trung bình (thang điểm 1-5) |

---

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| :--- | :--- | :--- | :--- | :--- |
| `ExpectTableRowCountToBeBetween` | Completeness | 5 đến 5000 dòng | **Pass (24 dòng)** | `data/reports/phase1_report.md` |
| `ExpectColumnValuesToNotBeNull` | Completeness | Non-null (`paper_id`, `title`) | **Pass (0 null)** | `data/reports/phase1_report.md` |
| `ExpectColumnValuesToBeBetween` | Validity | `age_days >= 0` | **Pass (100% valid)** | `data/reports/phase1_report.md` |
| `ExpectColumnValuesToMatchRegex` | Validity | DOI Regex `^10\.\d{4,9}/...` | **Pass (100% match)** | `data/reports/phase1_report.md` |

### Freshness

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Freshness được đo tại** | Dataframe sạch `data/clean/papers_clean.csv` |
| **Timestamp mới nhất** | `2026-09-13` |
| **Ngưỡng freshness** | `180 ngày` (`age_days <= 180`) |
| **Trạng thái baseline** | **FRESH** |
| **Lý do** | Tỷ lệ bài báo cũ (>180 ngày) chỉ chiếm **4.17% (1/24 dòng)**, nằm trong ngưỡng cho phép |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| :--- | :--- | --: | :--- | :--- | :--- |
| `drop_latest_records` | Lọc bỏ 20% bài báo có ngày xuất bản mới nhất | 4 records | Tăng tỷ lệ dữ liệu cũ | Mất dữ liệu mới, giảm Hit Rate | Đọc lại snapshot gốc `crossref_records.json` |
| `blank_summary` | Xóa rỗng trường `summary = ""` | 1 record | GX Non-null / Length Fail | Vector bị lệch, gây Silent Failure | Re-clean & nạp lại từ snapshot thô |
| `inject_noise` | Chèn chuỗi `[CORRUPTED_NOISE...]` | 1 record | Data Pollution | Giảm điểm F1 score của câu trả lời | Đè lại dữ liệu gốc từ snapshot |
| `truncate_title` | Cắt ngắn tiêu đề `< 8` ký tự | 1 record | Title Length Warning | Gây nhiễu exact match tìm kiếm | Re-build dataframe từ snapshot gốc |
| `stale_date` | Lùi ngày xuất bản về 365 ngày trước | 1 record | Tăng `age_days` | Tăng tuổi bài báo | Tính lại `age_days` từ ngày xuất bản gốc |
| `duplicate_rows` | Nhân đôi dòng bản ghi đã có | 1 record | Uniqueness Fail | Trùng lặp tài liệu trong Vector DB | Gọi `drop_duplicates(subset=['paper_id'])` |

**Corruption log:**
- **Đường dẫn:** `data/results/corruption_log.json`
- **Trạng thái:** **Có**
- **Nhận xét:** File log lưu đầy đủ 9 sự cố bị tiêm kèm theo `paper_id`, loại corruption và chi tiết trạng thái `before`/`after`.

**Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:**
Hàm `repair_from_raw_snapshot()` thực hiện cơ chế **Idempotent Self-Healing** bằng cách đọc trực tiếp bản ghi thô chưa qua biến đổi từ file immutable snapshot `data/raw/crossref_records.json`. Hàm chạy lại toàn bộ quy trình `build_clean_dataframe()` sạch từ đầu, ghi đè file CSV/JSON và Re-build toàn bộ ChromaDB Vector Store. Cơ chế này đảm bảo dữ liệu được khôi phục triệt để từ gốc thay vì chỉ patch bề nổi.

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| :--- | --: | --: | --: | --: | --: | :--- |
| `retrieval_hit_rate` | **100.00%** | **50.00%** | **100.00%** | -50.00% | +100.00% | Dữ liệu bẩn làm sụt giảm 50% khả năng tìm kiếm; Repair khôi phục hoàn toàn. |
| `mean_token_f1` | **0.5000** | **0.1800** | **0.5000** | -0.3200 | +100.00% | F1 score giảm sâu do mất ngữ cảnh tóm tắt; phục hồi 100% sau repair. |
| `judge_accuracy` | **50.00%** | **20.00%** | **50.00%** | -30.00% | +100.00% | Đánh giá câu trả lời bị sụt giảm mạnh khi bị tiêm rác. |
| `mean_judge_score` | **3.0000** | **1.8000** | **3.0000** | -1.2000 | +100.00% | Điểm số đánh giá phục hồi nguyên vẹn về mức Baseline. |
| Quality checks pass/fail | **PASSED** | **FAILED** | **PASSED** | Báo động đỏ | Phục hồi | Quality Gate phát hiện chính xác sự cố dữ liệu bẩn. |
| Freshness status | **FRESH** | **FRESH** | **FRESH** | 0.00% | 0.00% | Hệ thống vẫn duy trì chỉ số thời gian chung trong ngưỡng cho phép. |

**Hai kết luận có quan hệ nhân quả:**

1. `[Corruption: Xóa rỗng summary & Drop 20% bài mới]` ➔ `[GX Quality Gate lập tức báo FAILED]` ➔ `[Retrieval Hit Rate bị kéo tụt từ 100% xuống 50%]`.
2. `[Repair action: Tái tạo sạch từ Snapshot thô]` ➔ `[GX Quality Gate trở lại PASSED]` ➔ `[Retrieval Hit Rate và Token F1 phục hồi 100% về trạng thái Baseline]`.

---

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** Xuất hiện lỗi `TypeError: Cannot subtract tz-naive and tz-aware datetime-like objects` tại file `src/ingestion/cleaning.py` làm ngắt đột ngột tiến trình chạy `script/run_phase1.py`.
- **Nguyên nhân:** Hàm `now_utc()` tạo đối tượng `datetime` mang thông tin timezone UTC (`tz-aware`), trong khi `pd.to_datetime(df['published'])` tạo chuỗi `DatetimeIndex` không có thông tin timezone (`tz-naive`). Phép trừ hai kiểu dữ liệu bất tương thích gây ra crash trong Pandas.
- **Cách xử lý:** Cập nhật hàm `build_clean_dataframe()` ép kiểu datetime đồng bộ với `utc=True`:
  ```python
  published_dt = pd.to_datetime(df["published"], errors="coerce", utc=True)
  run_date_utc = pd.to_datetime(run_date, utc=True)
  df["age_days"] = (run_date_utc - published_dt).dt.days.fillna(0).clip(lower=0).astype(int)
  ```
- **Cách xác minh:** Thực thi lệnh `python script/run_phase1.py` và `python script/run_corruption_flow.py` chạy thành công mượt mà với exit code 0.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| :--- | :--- | :--- |
| Đánh giá LLM Judge đang dùng cơ chế Rule-based Fallback Heuristic | Chưa đo lường được khả năng suy luận tự nhiên phong phú của các LLM mạnh | Tích hợp Live API Key (Gemini/OpenAI) và kích hoạt Ragas framework (`RUN_RAGAS=1`) |
| Pipeline chưa có cơ chế ngắt tự động (Circuit Breaker) | Dữ liệu bẩn vẫn có thể nạp vào ChromaDB nếu người dùng không kiểm tra báo cáo | Cài đặt Automated Circuit Breaker: tự động dừng ghi Vector DB và rollback nếu GX Quality Gate báo `FAILED` |
| Tập dữ liệu thử nghiệm còn nhỏ (24 bản ghi) | Chưa đo lường hết độ trễ và hiệu năng của Vector DB ở quy mô lớn | Mở rộng ingestion pipeline, thu thập > 5,000 bài báo từ Crossref để stress-test hệ thống |

---

## 13. Checklist trước khi nộp

- [X] Thông tin nhóm và repository chính xác.
- [X] Phân công khớp với module, artifact và kết quả thực tế.
- [X] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [X] Baseline, corrupted và repaired dùng cùng evaluation set.
- [X] Bảng metrics khớp với các file trong `data/results/`.
- [X] Quality/freshness conclusions khớp với `data/quality/`.
- [X] Các đường dẫn báo cáo và artifact truy cập được.
- [X] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [X] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.