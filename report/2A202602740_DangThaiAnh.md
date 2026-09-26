# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đặng Thái Anh             |
| MSSV               | 2A202602740               |
| Khóa/Lớp         | K4 - Lớp B (Ca Sáng)      |
| Tên nhóm         | Team 03 - DataObservability |
| Vai trò chính    | Data Foundation, Ingestion & Idempotent Recovery |
| Repository         | K4-L3B-DAY10-Team03-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| Thu thập dữ liệu Crossref & Snapshot Fallback | `src/ingestion/crossref.py` (`fetch_source_records`, `parse_crossref_payload`, `load_raw_records`) | Crossref REST API hoặc `data/raw/crossref_response.json` | `data/raw/crossref_records.json` (24 bản ghi thô) | Hoàn thành |
| Tiền xử lý, Cleaning & Mô hình hóa dữ liệu | `src/ingestion/cleaning.py` (`build_clean_dataframe`, `_clean_text`) | `list[PaperRecord]`, `run_date` | `data/clean/papers_clean.csv`, `papers_clean.json` | Hoàn thành |
| Synthetic Data Corruption Suite | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | Clean DataFrame | DataFrame bị tiêm 6 lỗi, `data/results/corruption_log.json` | Hoàn thành |
| Thuật toán Idempotent Repair | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py` | Snapshot thô bất biến `data/raw/crossref_records.json` | Tái tạo hoàn hảo 24 bản ghi sạch, khử trùng lặp | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Thiết kế trường phục vụ Observability | Đỗ Trung Tuyến (`quality.py`) | Cung cấp cột `age_days` chuẩn xác giúp tính toán Freshness SLA |
| Kiểm thử tính Idempotent của Repair | Nguyễn Đức Anh (`corruption_flow.py`) | Đảm bảo nạp lại dữ liệu nhiều lần không gây lỗi duplicate ID hay lệch số lượng dòng |
| Tích hợp kiểm thử Ingestion trong Pytest | Bộ test chung (`tests/test_pipeline.py`) | Viết unit tests kiểm thử cơ chế fallback và cấu trúc 5 phần `text_for_embedding` |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Ingestion & Fallback Logic | `src/ingestion/crossref.py` | Lưu trữ 2 raw artifacts đảm bảo Data Lineage | File `data/raw/crossref_records.json` tồn tại, 24 records |
| Cleaning & 5-part Embedding Text | `src/ingestion/cleaning.py` | Tạo cột `text_for_embedding` có Title, Authors, Categories, Published, Summary | `python -c "import pandas as pd; df=pd.read_json('data/clean/papers_clean.json'); print(len(df))"` in 24 |
| Tiêm 6 kịch bản suy thoái dữ liệu | `src/ingestion/corruption.py` | Ghi log chi tiết 6 lỗi tổng hợp | `data/results/corruption_log.json` ghi nhận đủ 6 scenarios |
| Khôi phục dữ liệu Idempotent | `src/pipelines/corruption_flow.py` | Khôi phục 24 bản ghi sạch 100% | Bảng đối chiếu so sánh cho thấy Hit Rate hồi phục 100% |

**Output cụ thể:**
File lưu trữ thô `data/raw/crossref_records.json` bảo toàn toàn bộ cấu trúc dữ liệu gốc của 24 bài báo khoa học và file nhật ký làm bẩn dữ liệu `data/results/corruption_log.json`.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Dữ liệu từ API bên ngoài (Crossref) thường chứa thẻ XML/JATS không mong muốn (`<jats:p>`), khoảng trắng bất thường, và phụ thuộc đường truyền mạng (nguy cơ lỗi 429 Too Many Requests hoặc ngắt mạng). Cần cơ chế phòng thủ (Resilient Ingestion) có khả năng tự động đọc từ snapshot local.
2. Mô hình Embedding MiniLM cần một ngữ cảnh đầy đủ nhưng súc tích. Nếu chỉ embed tiêu đề hoặc chỉ embed tóm tắt, mô hình sẽ không trả lời được các câu hỏi về tác giả hay ngày xuất bản.
3. Để chứng minh năng lực tự phục hồi (Self-Healing), cần một bộ công cụ tiêm lỗi dữ liệu chuẩn xác mô phỏng các sự cố dữ liệu thực tế trong sản xuất.

### Cách triển khai
1. **Module Ingestion với Resilience Fallback:** Hàm `fetch_source_records` ưu tiên gọi API có timeout 10 giây; nếu mất mạng hoặc cờ `REFRESH_SOURCE=False`, hệ thống lập tức chuyển sang đọc từ file local snapshot `data/raw/crossref_response.json`. Dữ liệu sau đó được parse thành dataclass `PaperRecord` và lưu vào `crossref_records.json` để bảo toàn Data Lineage.
2. **Cấu trúc 5 phần của `text_for_embedding`:**
   ```text
   Title: <title>
   Authors: <author_1, author_2>
   Categories: <category_1, category_2>
   Published: <YYYY-MM-DD>
   Summary: <abstract đã khử JATS XML>
   ```
3. **Bộ 6 kịch bản Synthetic Corruption:**
   - *Kịch bản 1:* Xóa 20% bản ghi mới nhất (Drop latest records) để mô phỏng mất mát dữ liệu stream.
   - *Kịch bản 2:* Xóa rỗng trường summary tại 2 dòng đầu để mô phỏng lỗi trích xuất dữ liệu rỗng.
   - *Kịch bản 3:* Chèn chuỗi rác ngẫu nhiên để gây nhiễu không gian vector.
   - *Kịch bản 4:* Cắt ngắn tiêu đề thành "Bad" (< 8 ký tự) để vi phạm schema expectation.
   - *Kịch bản 5:* Đặt lại ngày xuất bản về năm 2018 (`age_days = 3000`) cho 8 dòng để kích hoạt vi phạm Freshness SLA.
   - *Kịch bản 6:* Nhân bản dòng trùng lặp `paper_id` để vi phạm tính duy nhất.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | JSON response từ Crossref API hoặc local JSON snapshot |
| Output | `PaperRecord` instances, `papers_clean.csv`, `papers_clean.json`, `corruption_log.json` |
| Module phụ thuộc | `core/config.py`, `core/utils.py` |
| Module sử dụng output | `retrieval/index.py`, `observability/quality.py`, `evaluation/testset.py` |
| Điều kiện lỗi cần xử lý | Bản ghi thiếu DOI hoặc thiếu tiêu đề (tự động bỏ qua), trường date-parts bị khuyết |

### Cách xác minh

```bash
# Kiểm tra Ingestion và Cleaning
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Da clean thanh cong {len(df)} dong, text_for_embedding hop le: {\"Title:\" in df.iloc[0][\"text_for_embedding\"]}')"
```

- **Kết quả mong đợi:** In ra `Da clean thanh cong 24 dong, text_for_embedding hop le: True`.
- **Kết quả thực tế:** Đúng như mong đợi 100%.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn cách thức lưu trữ dữ liệu thô (Raw Data Storage) sau khi nhận payload từ Crossref REST API.
- **Các phương án đã cân nhắc:**
  - *Phương án 1:* Chỉ lưu trực tiếp DataFrame sạch vào file CSV/JSON, không lưu payload thô vì tốn dung lượng ổ đĩa.
  - *Phương án 2:* Lưu song song 2 tầng: tầng raw API response (`crossref_response.json`) và tầng raw parsed records (`crossref_records.json`) trước khi chuyển sang bước Cleaning.
- **Phương án đã chọn:** Phương án 2 (Bảo toàn 2 file Raw Artifacts).
- **Lý do:** Đây là nguyên tắc cốt lõi của Data Lineage. Nếu có sự thay đổi trong logic cleaning hoặc phát hiện thuật toán tính `age_days` bị sai, nhóm có thể re-process bất kỳ lúc nào từ raw snapshot mà không phụ thuộc vào Crossref API (tránh nguy cơ API thay đổi dữ liệu hoặc bị rate-limit). Hơn nữa, việc này là nền tảng sống còn cho cơ chế Idempotent Repair.
- **Bằng chứng quyết định phù hợp:** Trong Pha 3, hệ thống đã khôi phục dữ liệu sạch hoàn toàn từ `crossref_records.json` chỉ trong 0.2 giây mà không cần gọi ra Internet.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  TypeError: can't subtract offset-naive and offset-aware datetimes
  ```
- **Lệnh tái hiện:** Chạy hàm `build_clean_dataframe` khi `run_date` truyền vào là `datetime.now(timezone.utc)` (có timezone) trong khi `pub_date` parse từ chuỗi ISO string của bài báo là naive datetime (không có timezone).
- **Nguyên nhân gốc:** Python 3.12 cấm thực hiện phép trừ thời gian giữa một datetime có thông tin múi giờ (aware) và một datetime không có thông tin múi giờ (naive).
- **Cách xử lý:** 
  Bổ sung logic đồng bộ hóa timezone linh hoạt trong `src/ingestion/cleaning.py`:
  ```python
  pub_date = datetime.fromisoformat(published)
  if run_date.tzinfo and not pub_date.tzinfo:
      pub_date = pub_date.replace(tzinfo=run_date.tzinfo)
  elif not run_date.tzinfo and pub_date.tzinfo:
      pub_date = pub_date.replace(tzinfo=None)
  age_days = max(0, (run_date - pub_date).days)
  ```
- **Cách xác minh sau khi sửa:** Chạy test `pytest tests/test_pipeline.py -k test_ingestion_and_cleaning`, kiểm tra pass thành công và `age_days` luôn là số nguyên chính xác.
- **Điều học được:** Khi xử lý dữ liệu thời gian trong Data Pipeline, luôn phải chuẩn hóa triệt để timezone (khuyến nghị dùng UTC) để tránh các lỗi logic ngầm.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu thô từ Crossref API qua tầng Ingestion được bảo lưu vào raw snapshot $\rightarrow$ qua tầng Cleaning loại bỏ rác XML, tính độ tuổi bài báo, ghép văn bản nhúng $\rightarrow$ chuyển sang tầng Retrieval để mô hình `all-MiniLM-L6-v2` mã hóa thành vector 384 chiều và lưu trữ trên ChromaDB.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Mỗi câu hỏi có ID tài liệu gốc (`ground_truth_doc_ids`). Sau khi ChromaDB tìm kiếm top_k kết quả, nếu tài liệu gốc nằm trong danh sách trả về thì tính là Hit (đo lường độ chính xác tìm kiếm).
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks đo lường tính hợp lệ về cấu trúc dữ liệu tĩnh (schema, null, uniqueness, length). Freshness monitoring đo lường độ trôi dạt (Data Drift) theo thời gian, đảm bảo tài liệu không bị quá cũ ảnh hưởng đến tính thời sự của câu trả lời.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để duy trì tính nhất quán của thước đo (benchmark constancy). Chỉ khi giữ nguyên câu hỏi và ground truth thì mọi sự thay đổi trong metrics mới phản ánh trung thực tác động của chất lượng dữ liệu.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Thành công khi DataFrame tái tạo có đúng 24 dòng sạch, file `repaired_quality_report.json` đạt `success=True`, `repaired_freshness_report.json` đạt `is_fresh=True`, và `repaired_metrics.json` đạt Hit Rate 100.0%.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate`   |   100.0% |     60.0% |   100.0% | Việc xóa 20% bản ghi làm sập Hit Rate trên các bài mới |
| `mean_token_f1`        |   100.0% |     85.1% |   100.0% | Kịch bản blank summary và inject noise làm giảm Token F1 |
| `judge_accuracy`       |   100.0% |     90.0% |   100.0% | Câu trả lời thiếu context bị LLM Judge trừ điểm |
| `mean_judge_score`     |     5.00 |      4.20 |     5.00 | Điểm trung bình giảm từ 5.0 xuống 4.2 |
| Quality checks         |   PASSED |    FAILED |   PASSED | GX 1.x bắt trúng lỗi rỗng summary, title ngắn và duplicate |
| Freshness status       |  HEALTHY |  VIOLATED |  HEALTHY | Kịch bản lùi ngày xuất bản vọt lên 40.9% bài quá hạn |

### Kết luận từ số liệu
- Kịch bản **Drop latest records** và **Inject noise** có sức tàn phá mạnh nhất đến RAG vì vector database hoàn toàn mất dấu vết ngữ nghĩa của tài liệu gốc.
- Việc khôi phục từ Raw snapshot chứng minh rằng dữ liệu thô bất biến là "phao cứu sinh" duy nhất giúp hệ thống AI hồi sinh 100% sau sự cố.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Bảo tồn Raw Data:** Không bao giờ được ghi đè hay biến đổi trực tiếp trên dữ liệu thô.
2. **Kỹ thuật Synthetic Corruption:** Giúp đội ngũ chủ động kiểm thử sức chịu đựng của hệ thống AI trước khi triển khai thực tế.
3. **Data Quality là gốc rễ của AI:** "Garbage In, Garbage Out" - nếu dữ liệu bẩn thì dù mô hình LLM có tiên tiến đến đâu cũng sẽ trả về kết quả sai lệch.

### Nếu có thêm thời gian
Tôi sẽ xây dựng thêm các kịch bản tiêm lỗi nâng cao như Semantic Drift (thay đổi nội dung nhưng giữ nguyên độ dài) để kiểm tra độ nhạy của vector similarity.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đặng Thái Anh  
**Ngày xác nhận:** 2026-09-26
