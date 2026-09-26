# Member Role Report - Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | Thân Thị Kim Chi |
| **MSSV** | 2A202602797 |
| **Khóa/Lớp** | K4 - L3B |
| **Tên nhóm** | 4A (4aesieunhan) |
| **Vai trò chính** | Data Observability, Chaos Testing & Idempotent Pipeline Integrator (Bước 7 & Bước 8) |
| **Repository** | https://github.com/TuTu99999/K4-L3B-DAY10-4aesieunhan-DataPipelineDataObservability/tree/chi |
| **Ngày hoàn thành** | 2026-09-26 |

---

## 2. Vai trò và phạm vi công việc

Trong bài lab Day 10, tôi được phân công chịu trách nhiệm chính về phần kiểm thử suy thoái dữ liệu (Data Corruption Suite - Bước 7), đo lường sự suy giảm chất lượng của mô hình AI, thiết kế cơ chế tự phục hồi Idempotent Repair và lập báo cáo đối chiếu 3 trạng thái (Bước 8).

### Phần việc sở hữu chính

| Module / Deliverable | File / Hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Bước 7: Data Corruption Suite** | `src/ingestion/corruption.py` / `corrupt_clean_dataframe()` | DataFrame sạch `papers_clean.json` (24 bài báo) | `papers_clean_corrupted.json`, `papers_clean_corrupted.csv`, `data/results/corruption_log.json` | Hoàn thành 100% |
| **Bước 8: 3-State Comparison Reporting** | `src/observability/reporting.py` / `generate_corruption_report()` | Metrics và Quality reports của 3 trạng thái (Baseline, Corrupted, Repaired) | Báo cáo Markdown đối chiếu `data/reports/corruption_report.md` | Hoàn thành 100% |
| **Bước 8: Phase 2 Pipeline & Idempotent Repair** | `src/pipelines/corruption_flow.py` / `run_corruption_flow_pipeline()`, `repair_from_raw_snapshot()` | Dữ liệu sạch, snapshot thô `crossref_records.json`, bộ testset | Pipeline toàn tuyến `script/run_corruption_flow.py`, ChromaDB collection `papers-corrupted` và `papers-repaired`, `corrupted_metrics.json`, `repaired_metrics.json` | Hoàn thành 100% |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên / Module được hỗ trợ | Kết quả và bằng chứng |
| :--- | :--- | :--- |
| **Thiết lập môi trường & Dependency Cache** | Toàn đội (`SETUP_DEPENDENCIES.md`) | Tôi đã hỗ trợ cấu hình công cụ uv, thiết lập thư mục cache UV_CACHE_DIR, gỡ lỗi xung đột tiến trình pip và kiểm tra môi trường chạy đủ 157 thư viện. |
| **Kiểm thử Mock Data** | Module Ingestion & Reporting | Tôi đã chuẩn bị kịch bản kiểm thử giả lập dữ liệu độc lập để các thành viên xác minh logic trước khi tích hợp dữ liệu thật. |

---

## 3. Kết quả theo vai trò

Trong quá trình thực hiện nhiệm vụ của mình, tôi đã bàn giao đầy đủ các sản phẩm sau:

| Nhiệm vụ đã thực hiện | File / Hàm / Artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Triển khai 6 kịch bản tiêm lỗi dữ liệu | `src/ingestion/corruption.py` | Hàm tiêm lỗi tự động và file audit log `corruption_log.json` | Chạy lệnh kiểm tra Bước 7 qua Python CLI |
| Xây dựng cơ chế Idempotent Repair | `src/pipelines/corruption_flow.py` | Hàm `repair_from_raw_snapshot()` tự khôi phục dữ liệu sạch | Tái tạo dữ liệu và xác nhận tính toàn vẹn 24 dòng |
| Đánh giá suy giảm (Silent Failure) & phục hồi | `src/pipelines/corruption_flow.py` | Vector index ChromaDB `papers-corrupted`, `papers-repaired` | Chạy toàn tuyến `script/run_corruption_flow.py` |
| Báo cáo đối chiếu 3 trạng thái | `src/observability/reporting.py` | Báo cáo `data/reports/corruption_report.md` và bảng so sánh console | Kiểm tra bảng số liệu 3 cột Baseline vs Corrupted vs Repaired |

### Chi tiết các lỗi dữ liệu tôi đã tiêm vào tập dữ liệu (Bước 7):
Tôi đã lập trình để tạo ra file nhật ký kiểm toán `data/results/corruption_log.json` ghi nhận đầy đủ 6 dạng lỗi thực tế:
- `dropped_latest_records`: 4 bài (tương đương 20% số bài mới nhất theo ngày xuất bản bị loại bỏ).
- `blank_summary_records`: 2 bài bị xóa trắng toàn bộ nội dung tóm tắt.
- `injected_noise_records`: 2 bài bị chèn chuỗi ký tự rác không thể đọc hiểu vào phần tóm tắt.
- `truncated_title_records`: 2 bài bị cắt ngắn tiêu đề xuống chữ "Draft" (dưới 8 ký tự).
- `stale_date_records`: 6 bài bị lùi ngày xuất bản về 365 ngày trước, làm tăng tuổi thọ dữ liệu vượt ngưỡng SLA.
- `duplicated_records`: 2 bài bị nhân bản dòng để tạo ra sự trùng lặp khóa chính paper_id.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề tôi cần giải quyết
Trong thực tế vận hành các hệ thống RAG và Data Pipeline, dữ liệu nguồn thường xuyên bị suy thoái do lỗi mạng, lỗi người nhập liệu hoặc lỗi từ API đối tác (nhiễu ký tự, thiếu trường thông tin, trễ hạn xuất bản, dữ liệu bị trùng lặp). Những sự cố này thường không làm crash code (không sinh mã lỗi 500), nhưng lại gây ra hiện tượng Silent Failure: câu trả lời của AI bị suy giảm nghiêm trọng về độ chính xác và độ liên quan mà lập trình viên không hay biết. Tôi cần xây dựng một bộ tiêm lỗi có kiểm soát để chứng minh hệ thống giám sát (Great Expectations 1.x + Freshness SLA) có khả năng phát hiện lỗi kịp thời, đồng thời hệ thống có khả năng tự phục hồi mà không cần phụ thuộc vào API bên ngoài.

### Cách tôi triển khai
1. **Tiêm 6 lỗi dữ liệu:** Tôi lập trình hàm `corrupt_clean_dataframe()` sử dụng các thao tác cắt lát, gán giá trị và nhân bản dòng trên Pandas DataFrame.
2. **Tái tạo ngữ cảnh embedding:** Tôi xây dựng hàm helper `_format_text_for_embedding()` để tự động tổng hợp lại chuỗi "Title: ...\nAuthors: ...\nPublished: ...\nCategories: ...\nSummary: ...", đảm bảo khi đưa vào ChromaDB thì vector biểu diễn phản ánh đúng dữ liệu đã bị làm bẩn.
3. **Cơ chế Idempotent Self-Healing:** Tôi xây dựng hàm `repair_from_raw_snapshot()` đọc lại bản snapshot thô ban đầu `data/raw/crossref_records.json` để chạy lại bước clean. Cơ chế này đảm bảo tính tất định (deterministic): chạy lại bao nhiêu lần thì kết quả vẫn luôn đồng nhất và không tiêu tốn thêm quota gọi API bên ngoài.

### Input, Output và Contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Pandas DataFrame sạch (24 dòng) chứa các cột: `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`. |
| **Output** | DataFrame bị làm bẩn (22 dòng: 24 ban đầu - 4 bài bị drop + 2 bài nhân bản), file JSON/CSV corrupted, file log `corruption_log.json`. |
| **Module phụ thuộc** | `core/config.py` (đường dẫn), `core/utils.py` (hàm I/O json/csv). |
| **Module sử dụng output** | `retrieval/index.py` (để embed vào ChromaDB), `evaluation/metrics.py` (đánh giá sụt giảm RAG). |
| **Điều kiện lỗi cần xử lý** | DataFrame rỗng (trả về log rỗng an toàn); ngày tháng sai định dạng (xử lý ngoại lệ fallback an toàn). |

### Cách tôi tự xác minh kết quả Bước 7

Tôi chạy lệnh kiểm thử trên dòng lệnh:
```powershell
python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Tín hiệu hoàn thành: Corrupted {len(c)} dòng')"
```
- Kết quả mong đợi: Console in ra chuỗi "Tín hiệu hoàn thành: Corrupted 22 dòng".
- Kết quả thực tế tôi đạt được: Code chạy thành công, console in ra đúng 22 dòng và file `corruption_log.json` được tạo mới với đầy đủ 6 nhóm lỗi chi tiết.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi tiêm lỗi vào các cột `title`, `summary`, `published`, nếu tôi chỉ thay đổi giá trị trên các cột rời rạc của DataFrame mà không tái tạo lại cột `text_for_embedding`, Vector Index trong ChromaDB sẽ vẫn mang ngữ cảnh của văn bản cũ hoặc bị lệch pha so với dữ liệu hiển thị.
- **Các phương án tôi đã cân nhắc:**
  1. Phương án A: Chỉ thay đổi giá trị trên các cột rời rạc (`title`, `summary`) và để nguyên cột `text_for_embedding`.
  2. Phương án B: Viết logic đồng bộ hóa, tự động gọi hàm tái cấu trúc `_format_text_for_embedding()` để tính toán lại toàn bộ cột `text_for_embedding` ngay sau khi làm bẩn dữ liệu.
- **Phương án tôi đã chọn:** Phương án B.
- **Lý do:** Đảm bảo tính nhất quán dữ liệu (Data Consistency) tuyệt đối giữa bảng dữ liệu dạng bảng và không gian vector embedding. Nhờ vậy, khi mô hình tìm kiếm ngữ nghĩa cosine similarity hoạt động trên ChromaDB, sự suy giảm về độ tương đồng và trượt tài liệu (Hit Rate drop) mới diễn ra một cách trung thực nhất.

---

## 6. Một lỗi hoặc blocker tôi đã trực tiếp xử lý

- **Triệu chứng lỗi nguyên văn:**
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode character '\u1ec7' in position 6: character maps to <undefined>
  ```
- **Lệnh hoặc bước tái hiện:** Khi tôi chạy lệnh kiểm tra trên Windows PowerShell có lệnh print in chuỗi tiếng Việt có dấu ("Tín hiệu hoàn thành...").
- **Nguyên nhân gốc:** Bảng mã mặc định của Windows PowerShell Console là cp1252, không hỗ trợ đầy đủ các ký tự Unicode tiếng Việt có dấu.
- **Cách tôi xử lý:** 
  1. Tôi đã thiết lập biến môi trường `$env:PYTHONIOENCODING = "utf-8"` trong PowerShell trước khi thực thi script.
  2. Tôi kiểm tra và đảm bảo toàn bộ hàm `write_json()` và `write_text()` trong `core/utils.py` đều có tham số `encoding="utf-8"`.
- **Cách tôi xác minh sau khi sửa:** Chạy lại script kiểm thử, console in ra chuỗi tiếng Việt trơn tru mà không còn gặp ngoại lệ mã hóa.

---

## 7. Hiểu biết của tôi về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**  
   Dữ liệu được truy vấn từ Crossref REST API qua HTTP -> Lưu bản thô nguyên bản vào `crossref_response.json` và `crossref_records.json` -> Module cleaning chuẩn hóa văn bản, tính toán `age_days`, khử trùng lặp và ghép chuỗi `text_for_embedding` -> Mô hình `all-MiniLM-L6-v2` chuyển đổi văn bản thành các vector 384 chiều -> Lưu trữ liên tục (persistent) vào ChromaDB collection với metric khoảng cách Cosine.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**  
   Bộ test set gồm 10 câu hỏi chuẩn hóa kèm `ground_truth_doc_ids` (DOI bài báo chứa đáp án) và `ground_truth` (nội dung câu trả lời chuẩn). Khi chạy RAG:
   - Retrieval Hit Rate: Kiểm tra xem danh sách top-k document IDs truy xuất được có chứa `ground_truth_doc_ids` hay không.
   - Token F1 & Judge Score: Đo lường mức độ trùng khớp từ vựng và sử dụng mô hình thẩm định mức độ chính xác ngữ nghĩa của câu trả lời được sinh ra so với ground-truth.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**  
   - Quality checks (Great Expectations 1.x): Tập trung vào tính toàn vẹn cấu trúc và quy tắc dữ liệu nội tại (Schema validation, số lượng dòng trong khoảng 5 đến 5000, độ dài chuỗi summary tối thiểu 30 ký tự, tính duy nhất của khóa chính paper_id).
   - Freshness monitoring (Data Observability SLA): Tập trung vào tính kịp thời của dữ liệu theo thời gian thực (độ tuổi `age_days`). Nếu tỷ lệ bài báo cũ quá hạn (> 180 ngày) vượt ngưỡng cho phép (> 25%), hệ thống sẽ báo động vi phạm Freshness SLA dù dữ liệu hoàn toàn đúng schema.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**  
   Để đảm bảo tính khách quan khoa học (Controlled Experiment). Việc cố định tập câu hỏi kiểm định (Ground Truth) là biến độc lập duy nhất cho phép chúng tôi đo lường chính xác tác động của biến phụ thuộc (chất lượng dữ liệu từ Sạch -> Bẩn -> Phục hồi) lên hiệu năng của mô hình AI.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**  
   - Artifact: Tồn tại file `papers_clean_repaired.json`, `papers_clean_repaired.csv` và collection ChromaDB `papers-repaired`.
   - Metric & Signal: 
     + Data Quality Gate đạt `success = True` (100% checks pass).
     + Freshness SLA chuyển về `is_fresh = True`.
     + Chỉ số `retrieval_hit_rate` và `mean_token_f1` phục hồi hoàn toàn về mức 100% và 1.0000 tương đương với Baseline.

---

## 8. Phân tích kết quả thực nghiệm

### Bảng đối chiếu chỉ số 3 trạng thái tôi thu được từ pipeline thực tế

| Chỉ số / Tín hiệu | 1. Baseline | 2. Corrupted | 3. Repaired | Nhận xét của tôi |
| :--- | :---: | :---: | :---: | :--- |
| **`retrieval_hit_rate`** | **100.0%** | **80.0%** (Giảm 20.0%) | **100.0%** (Phục hồi 100%) | Giảm xuống 80% do 4 bài mới bị loại bỏ, phục hồi hoàn toàn 100% sau repair. |
| **`mean_token_f1`** | **1.0000** | **0.7720** (Giảm 0.2280) | **1.0000** (Phục hồi 100%) | Giảm rõ rệt do tóm tắt bị xóa trắng và chèn chuỗi ký tự rác. |
| **`judge_accuracy`** | **100.0%** | **80.0%** (Giảm 20.0%) | **100.0%** (Phục hồi 100%) | Mô hình trả lời sai ngữ cảnh khi tài liệu nguồn bị làm bẩn (Silent Failure). |
| **`mean_judge_score`** | **5.00** | **4.00** (Giảm 1.00) | **5.00** (Phục hồi 100%) | Điểm đánh giá chất lượng giảm sút rõ rệt trên tập dữ liệu bẩn. |
| **Data Quality Gate** | **PASS** | **FAIL** | **PASS** | Great Expectations 1.x phát hiện chính xác lỗi trùng khóa chính và tóm tắt rỗng. |
| **Freshness SLA** | **Fresh** (4.17% stale) | **Stale Alert** (31.82% stale) | **Fresh** (4.17% stale) | Phát hiện tỷ lệ bài báo cũ 31.82% vượt quá ngưỡng cho phép 25%. |

### Kết luận rút ra từ số liệu thực tế

1. **Chuỗi nguyên nhân và bằng chứng 1 (Khi tiêm lỗi):**
   Data corruption (Drop 20% bài mới, xóa và chèn nhiễu tóm tắt) -> Quality gate báo FAIL và Freshness phát cảnh báo Stale Alert (31.82% bài cũ) -> Retrieval Hit Rate giảm từ 100% xuống 80%, Token F1 giảm từ 1.0000 xuống 0.7720.
2. **Chuỗi nguyên nhân và bằng chứng 2 (Khi tự phục hồi):**
   Idempotent Repair từ raw snapshot gốc -> Quality gate chuyển về PASS và Freshness trở lại chuẩn an toàn (4.17% bài cũ) -> Retrieval Hit Rate và Token F1 phục hồi hoàn toàn về mức 100% và 1.0000.

- **Dạng lỗi gây ảnh hưởng rõ nhất:** Lỗi loại bỏ bài mới (Drop latest records) và xóa tóm tắt (Blank summary) gây ảnh hưởng nặng nề nhất, vì hệ thống RAG hoàn toàn phụ thuộc vào việc tìm đúng tài liệu liên quan và đọc được đoạn tóm tắt để tổng hợp câu trả lời cho người dùng.

---

## 9. Điều tôi học được và hướng cải thiện

### Ba bài học quan trọng nhất
1. **Kiến trúc Idempotent Pipeline:** Tôi hiểu sâu sắc tầm quan trọng của việc bảo toàn dữ liệu thô (Raw Preservation) làm điểm neo phục hồi (Lineage Anchor) để cứu vãn hệ thống khi có sự cố mà không phát sinh thêm chi phí hay rủi ro gọi lại API bên ngoài.
2. **Data Observability chặn đứng Silent Failure:** Tôi thấy được giá trị thực tế của Great Expectations và Freshness SLA trong việc phát hiện sớm sự suy thoái dữ liệu trước khi dữ liệu độc hại kịp lan sang mô hình AI phục vụ người dùng.
3. **Mối quan hệ nhân quả giữa Dữ liệu và AI:** Chất lượng câu trả lời của mô hình ngôn ngữ lớn phụ thuộc quyết định vào độ sạch và tính kịp thời của dữ liệu đầu vào. Dữ liệu rác thì AI trả lời sai.

### Nếu có thêm thời gian
Tôi sẽ xây dựng cơ chế tự động kích hoạt phục hồi theo thời gian thực (Automated Self-Healing Trigger): Ngay khi Great Expectations hoặc Freshness SLA phát hiện tín hiệu FAIL, hệ thống sẽ tự động kích hoạt tiến trình rollback và chạy hàm `repair_from_raw_snapshot()` ngay lập tức mà không cần sự can thiệp thủ công của kỹ sư vận hành.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa .env, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Người báo cáo:** Thân Thị Kim Chi  
**Ngày xác nhận:** 2026-09-26
