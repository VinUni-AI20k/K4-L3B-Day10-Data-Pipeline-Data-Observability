# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | Thân Thị Kim Chi |
| **MSSV** | 2A202602797 |
| **Khóa/Lớp** | K4 - L3B |
| **Tên nhóm** | 4A (4aesieunhan) |
| **Vai trò chính** | Data Observability, Chaos Testing & Idempotent Pipeline Integrator (Bước 7 & Bước 8) |
| **Repository** | https://github.com/TuTu99999/K4-L3B-DAY10-4aesieunhan-DataPipelineDataObservability |
| **Ngày hoàn thành** | 2026-09-26 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu chính

| Module / Deliverable | File / Hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Bước 7: Data Corruption Suite** | `src/ingestion/corruption.py` / `corrupt_clean_dataframe()` | DataFrame sạch `papers_clean.json` (24 bài báo) | `papers_clean_corrupted.json`, `papers_clean_corrupted.csv`, `data/results/corruption_log.json` | **Hoàn thành 100%** |
| **Bước 8: 3-State Comparison Reporting** | `src/observability/reporting.py` / `generate_corruption_report()` | Metrics và Quality reports của 3 trạng thái (Baseline, Corrupted, Repaired) | Báo cáo Markdown đối chiếu `data/reports/corruption_report.md` | **Hoàn thành 100%** |
| **Bước 8: Phase 2 Pipeline & Idempotent Repair** | `src/pipelines/corruption_flow.py` / `run_corruption_flow_pipeline()`, `repair_from_raw_snapshot()` | Dữ liệu sạch, snapshot thô `crossref_records.json`, bộ testset | Pipeline toàn tuyến `script/run_corruption_flow.py`, ChromaDB collection `papers-corrupted` và `papers-repaired`, `corrupted_metrics.json`, `repaired_metrics.json` | **Hoàn thành 100%** |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên / Module được hỗ trợ | Kết quả và bằng chứng |
| :--- | :--- | :--- |
| **Thiết lập môi trường & Dependency Cache** | Toàn đội (`SETUP_DEPENDENCIES.md`) | Cài đặt thành công công cụ `uv`, cấu hình biến môi trường cache `UV_CACHE_DIR`, giải quyết xung đột tiến trình pip và kiểm tra `Môi trường sẵn sàng` (157 packages). |
| **Kiểm thử Mock Data** | Module Ingestion & Reporting | Thiết kế script kiểm thử giả lập 24 dòng dữ liệu độc lập, chứng minh tính đúng đắn của logic trước khi tích hợp với dữ liệu thật. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File / Hàm / Artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Triển khai 6 kịch bản tiêm lỗi dữ liệu | `src/ingestion/corruption.py` | Hàm tiêm lỗi tự động và file audit log `corruption_log.json` | Chạy lệnh kiểm tra Bước 7 qua Python CLI |
| Xây dựng cơ chế Idempotent Repair | `src/pipelines/corruption_flow.py` | Hàm `repair_from_raw_snapshot()` tự khôi phục dữ liệu sạch | Tái tạo dữ liệu và xác nhận tính toàn vẹn 24 dòng |
| Đánh giá suy giảm (Silent Failure) & phục hồi | `src/pipelines/corruption_flow.py` | Vector index ChromaDB `papers-corrupted`, `papers-repaired` | Chạy toàn tuyến `script/run_corruption_flow.py` |
| Báo cáo đối chiếu 3 trạng thái | `src/observability/reporting.py` | Báo cáo `data/reports/corruption_report.md` và bảng so sánh console | Kiểm tra bảng số liệu 3 cột Baseline vs Corrupted vs Repaired |

### Output cụ thể tạo ra:
File audit log chi tiết **`data/results/corruption_log.json`** ghi nhận đầy đủ 6 dạng lỗi thực tế:
- `dropped_latest_records`: 4 bài (20% số bài mới nhất bị loại bỏ).
- `blank_summary_records`: 2 bài bị xóa trắng tóm tắt.
- `injected_noise_records`: 2 bài bị chèn chuỗi ký tự rác.
- `truncated_title_records`: 2 bài bị cắt ngắn tiêu đề dưới 8 ký tự (`Draft`).
- `stale_date_records`: 2 bài bị lùi ngày xuất bản về 365 ngày trước.
- `duplicated_records`: 2 bài bị nhân bản tạo trùng lặp khóa chính.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Trong thực tế vận hành các hệ thống RAG và Data Pipeline, dữ liệu nguồn thường xuyên bị suy thoái (nhiễu ký tự, thiếu trường thông tin, trễ hạn xuất bản, dữ liệu bị trùng lặp). Những sự cố này thường **không làm crash code** (không sinh ngoại lệ 500), nhưng lại gây ra hiện tượng **Silent Failure**: câu trả lời của AI bị suy giảm nghiêm trọng về độ chính xác và độ liên quan. Hệ thống cần một bộ thử nghiệm tiêm lỗi có kiểm soát để chứng minh hệ thống giám sát (Great Expectations + Freshness SLA) có khả năng phát hiện lỗi kịp thời, đồng thời hệ thống có khả năng tự phục hồi mà không cần phụ thuộc vào API bên ngoài.

### Cách triển khai
1. **Tiêm 6 lỗi dữ liệu:** Lập trình hàm `corrupt_clean_dataframe()` với các thao tác lọc, cắt lát, gán giá trị và nhân đôi DataFrame bằng Pandas.
2. **Tái tạo ngữ cảnh embedding:** Xây dựng hàm helper `_format_text_for_embedding()` để tự động tổng hợp lại chuỗi `Title: ...\nAuthors: ...\nSummary: ...`, đảm bảo khi đưa vào ChromaDB thì vector biểu diễn phản ánh đúng dữ liệu đã bị làm bẩn.
3. **Cơ chế Idempotent Self-Healing:** Xây dựng hàm `repair_from_raw_snapshot()` đọc lại bản snapshot thô ban đầu `data/raw/crossref_records.json` để chạy lại bước clean. Cơ chế này đảm bảo tính **tất định (deterministic)**: chạy lại bao nhiêu lần thì kết quả vẫn luôn đồng nhất và không tiêu tốn thêm quota gọi API bên ngoài.

### Input, Output và Contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Pandas DataFrame sạch (24 dòng) chứa các cột: `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`. |
| **Output** | DataFrame bị làm bẩn (22 dòng: 24 - 4 dropped + 2 duplicated), file JSON/CSV corrupted, file log `corruption_log.json`. |
| **Module phụ thuộc** | `core/config.py` (đường dẫn), `core/utils.py` (hàm I/O json/csv). |
| **Module sử dụng output** | `retrieval/index.py` (để embed vào ChromaDB), `evaluation/metrics.py` (đánh giá sụt giảm RAG). |
| **Điều kiện lỗi cần xử lý** | DataFrame rỗng (trả về log rỗng an toàn); ngày tháng sai định dạng (xử lý ngoại lệ fallback an toàn). |

### Cách xác minh

```powershell
python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Tín hiệu hoàn thành: Corrupted {len(c)} dòng')"
```
- **Kết quả mong đợi:** Console in ra `Tín hiệu hoàn thành: Corrupted 22 dòng`.
- **Kết quả thực tế:** Code chạy thành công, file `corruption_log.json` được tạo mới với 6 nhóm lỗi chi tiết.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi tiêm lỗi vào các cột `title` và `summary`, nếu chỉ sửa trên DataFrame mà không tái tạo lại cột `text_for_embedding`, Vector Index trong ChromaDB sẽ vẫn mang ngữ cảnh của dữ liệu cũ hoặc bị lệch pha so với dữ liệu hiển thị.
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Chỉ thay đổi giá trị trên các cột rời rạc (`title`, `summary`) và để mặc cột `text_for_embedding` như cũ.
  2. *Phương án B:* Viết logic đồng bộ hóa, tự động gọi hàm tái cấu trúc `_format_text_for_embedding()` để tính toán lại toàn bộ cột `text_for_embedding` ngay sau khi làm bẩn dữ liệu.
- **Phương án đã chọn:** **Phương án B**.
- **Lý do:** Đảm bảo **Data Consistency** tuyệt đối giữa bảng dữ liệu dạng bảng và không gian vector embedding. Nhờ vậy, khi mô hình tìm kiếm ngữ nghĩa cosine similarity hoạt động, sự suy giảm về độ tương đồng và trượt retrieval (Hit Rate drop) mới diễn ra một cách trung thực nhất.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode character '\u1ec7' in position 6: character maps to <undefined>
  ```
- **Lệnh hoặc bước tái hiện:** Khi chạy lệnh kiểm tra trên Windows PowerShell có in chuỗi tiếng Việt có dấu (`Tín hiệu hoàn thành...`).
- **Nguyên nhân gốc:** Bảng mã mặc định của Windows PowerShell Console là `cp1252`, không hỗ trợ đầy đủ các ký tự Unicode tiếng Việt có dấu.
- **Cách xử lý:** 
  1. Thiết lập biến môi trường `$env:PYTHONIOENCODING = "utf-8"` trong PowerShell trước khi thực thi script.
  2. Sử dụng chuỗi log không dấu hoặc cấu hình chuẩn UTF-8 trong `write_json()` / `write_text()` (`encoding="utf-8"`).
- **Cách xác minh sau khi sửa:** Chạy lại script kiểm thử, console in ra trơn tru mà không văng ngoại lệ mã hóa.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**  
   Dữ liệu được truy vấn từ Crossref REST API qua HTTP ➔ Lưu bản thô nguyên bản vào `crossref_response.json` và `crossref_records.json` ➔ Module cleaning chuẩn hóa văn bản, tính toán `age_days`, khử trùng lặp và ghép chuỗi `text_for_embedding` ➔ Mô hình `all-MiniLM-L6-v2` chuyển đổi văn bản thành các vector 384 chiều ➔ Lưu trữ liên tục (persistent) vào ChromaDB collection với metric khoảng cách Cosine.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**  
   Bộ test set gồm 10 câu hỏi chuẩn hóa kèm `ground_truth_doc_ids` (DOI bài báo chứa đáp án) và `ground_truth` (nội dung câu trả lời chuẩn). Khi chạy RAG:
   - **Retrieval Hit Rate:** Kiểm tra xem danh sách top-k document IDs truy xuất được có chứa `ground_truth_doc_ids` hay không.
   - **Token F1 & Judge Score:** Đo lường mức độ trùng khớp từ vựng và sử dụng LLM thẩm định mức độ chính xác ngữ nghĩa của câu trả lời được sinh ra so với ground-truth.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**  
   - **Quality checks (Great Expectations 1.x):** Tập trung vào tính toàn vẹn cấu trúc và quy tắc dữ liệu nội tại (Schema validation, số lượng dòng, độ dài chuỗi, tính duy nhất của khóa chính).
   - **Freshness monitoring (Data Observability SLA):** Tập trung vào tính kịp thời của dữ liệu theo thời gian thực (độ tuổi `age_days`). Nếu tỷ lệ bài báo cũ quá hạn (> 180 ngày) vượt ngưỡng cho phép (> 25%), hệ thống sẽ báo động vi phạm Freshness SLA dù dữ liệu hoàn toàn đúng schema.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**  
   Để đảm bảo **tính khách quan khoa học (Controlled Experiment)**. Việc cố định tập câu hỏi kiểm định (Ground Truth) là biến độc lập duy nhất cho phép chúng ta đo lường chính xác tác động của biến phụ thuộc (chất lượng dữ liệu từ Sạch ➔ Bẩn ➔ Phục hồi) lên hiệu năng của mô hình AI.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**  
   - **Artifact:** Tồn tại file `papers_clean_repaired.json`, `papers_clean_repaired.csv` và collection ChromaDB `papers-repaired`.
   - **Metric & Signal:** 
     + Data Quality Gate đạt `success = True` (100% checks pass).
     + Freshness SLA chuyển về `is_fresh = True`.
     + Chỉ số `retrieval_hit_rate` và `mean_token_f1` phục hồi tương đương với mức của Baseline.

---

## 8. Phân tích kết quả

### Bảng đối chiếu chỉ số 3 trạng thái

| Metric / Signal | 1. Baseline | 2. Corrupted | 3. Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| **`retrieval_hit_rate`** | **100.0%** | **60.0%** 🔻 | **100.0%** 🔺 | Giảm mạnh do 20% bài mới bị drop, phục hồi 100% sau repair. |
| **`mean_token_f1`** | **0.8500** | **0.4200** 🔻 | **0.8500** 🔺 | Giảm một nửa do tóm tắt bị xóa trắng và chèn chuỗi rác. |
| **`judge_accuracy`** | **100.0%** | **50.0%** 🔻 | **100.0%** 🔺 | AI trả lời sai ngữ cảnh khi tài liệu bị làm bẩn. |
| **`mean_judge_score`** | **4.80** | **2.30** 🔻 | **4.80** 🔺 | Điểm đánh giá chất lượng giảm sâu xuống mức không đạt. |
| **Data Quality Gate** | **PASS** | **FAIL (Alert)** 🚨 | **PASS** ✅ | Phát hiện thành công lỗi trùng lặp và tiêu đề quá ngắn. |
| **Freshness SLA** | **Fresh** | **Stale Alert** ⚠️ | **Fresh** ✅ | Phát hiện thành công sự cố lùi ngày xuất bản. |

### Kết luận từ số liệu

1. **Chuỗi nguyên nhân – bằng chứng 1 (Tiêm lỗi):**
   `Data corruption (Drop bài mới & xóa tóm tắt)` ➔ `Quality gate FAIL & Freshness báo động` ➔ `Retrieval Hit Rate giảm từ 100% xuống 60%, F1 giảm từ 0.85 xuống 0.42`.
2. **Chuỗi nguyên nhân – bằng chứng 2 (Tự phục hồi):**
   `Idempotent Repair từ raw snapshot` ➔ `Quality gate PASS & Freshness trở lại chuẩn` ➔ `Hit Rate và F1 phục hồi hoàn toàn về mức 100% và 0.85`.

- **Corruption ảnh hưởng rõ nhất:** Lỗi **Drop latest records** và **Blank summary** gây ảnh hưởng nặng nề nhất, vì RAG hoàn toàn phụ thuộc vào việc tìm đúng tài liệu và đọc được tóm tắt để tổng hợp câu trả lời.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Kiến trúc Idempotent Pipeline:** Hiểu rõ tầm quan trọng của việc bảo toàn dữ liệu thô (Raw Preservation) làm điểm neo (Lineage Anchor) để phục hồi hệ thống khi có sự cố mà không tốn chi phí gọi lại API ngoài.
2. **Data Observability chặn đứng Silent Failure:** Thấy được giá trị sống còn của Great Expectations và Freshness SLA trong việc phát hiện sớm sự suy thoái dữ liệu trước khi dữ liệu độc hại lan sang mô hình AI.
3. **Mối quan hệ nhân quả Dữ liệu – AI:** Chất lượng của hệ thống RAG phụ thuộc 90% vào độ sạch và tính kịp thời của dữ liệu đầu vào ("Garbage in, Garbage out").

### Nếu có thêm thời gian
Tôi sẽ xây dựng cơ chế **Automated Self-Healing Trigger (Tự động phục hồi theo thời gian thực)**: Khi Great Expectations hoặc Freshness SLA phát hiện tín hiệu `FAIL`, hệ thống sẽ tự động kích hoạt tiến trình rollback và chạy hàm `repair_from_raw_snapshot()` ngay lập tức mà không cần sự can thiệp thủ công của kỹ sư vận hành.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Người báo cáo:** Thân Thị Kim Chi  
**Ngày xác nhận:** 2026-09-26
