# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Hoàng Ngọc Đức             |
| MSSV               | 2A202602380                |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | T052AI                     |
| Vai trò chính    | Data Foundation & Recovery |
| Repository         | https://github.com/younglonelyboiz/K4-L3B-Day10-T052AI-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Raw Ingestion & Lineage | `src/ingestion/crossref.py` (`fetch_source_records`, `parse_crossref_payload`) | Crossref API params, Local Snapshot | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 papers) | Hoàn thành |
| Data Cleaning & Modeling | `src/ingestion/cleaning.py` (`build_clean_dataframe`) | `list[PaperRecord]`, `run_date` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` (24 rows, 16 cols) | Hoàn thành |
| Idempotent Repair | `build_clean_dataframe` + `load_raw_records` | `data/raw/crossref_records.json` | Khôi phục 24 dòng dữ liệu chuẩn cho `papers_clean_repaired.json` | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Hỗ trợ kiểm định chất lượng dữ liệu | Mai Tiến Huy (`src/observability/quality.py`) | Cung cấp clean DataFrame chuẩn schema có `age_days` và `text_for_embedding` 5 phần có nhãn |
| Hỗ trợ luồng phục hồi dữ liệu | Trịnh Xuân Huy (`src/pipelines/corruption_flow.py`) | Đảm bảo tính Idempotent để khôi phục 100% dữ liệu gốc không bị ảnh hưởng bởi lỗi |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Tải và parse Crossref API | `src/ingestion/crossref.py` | 24 bài báo khoa học chất lượng cao | Lệnh CP0: `Tín hiệu hoàn thành: Đã tải 24 bài báo` |
| Làm sạch và chuẩn hóa schema | `src/ingestion/cleaning.py` | 24 dòng sạch không null, không duplicate | Lệnh CP1: `Tín hiệu hoàn thành: Clean thành công 24 dòng` |
| Tạo trường `text_for_embedding` | `src/ingestion/cleaning.py` | Cột embedding định dạng 5 phần có nhãn rõ ràng | Kiểm tra trực quan cấu trúc `Title / Authors / Published / Categories / Summary` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Bản ghi clean DataFrame hoàn chỉnh 24 dòng x 16 cột lưu trữ đồng thời ở cả hai định dạng `data/clean/papers_clean.csv` và `data/clean/papers_clean.json`, bảo toàn data lineage và cung cấp đầu vào chuẩn cho ChromaDB vector store.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu thu thập từ Crossref REST API thường xuyên có định dạng không đồng nhất, ngày tháng thiếu sót hoặc chứa các thẻ JATS XML (`<jats:p>`). Ngoài ra, nguy cơ mạng chập chờn hoặc giới hạn rate limit (HTTP 429) có thể gây đứt gãy pipeline. Dữ liệu gốc cần được bảo tồn nguyên vẹn (Immutable Raw Snapshot) để có thể truy vết nguồn gốc và phục hồi tự động khi có sự cố.

### Cách triển khai

- **Cơ chế Offline Fallback:** Triển khai hàm `fetch_source_records` với cơ chế kiểm tra cờ `settings.refresh_source`. Khi mất mạng hoặc gặp lỗi API, hàm tự động chuyển sang đọc snapshot local `data/raw/crossref_response.json` hoặc `crossref_records.json`.
- **Row-level Dictionary Projection:** Duyệt qua từng bản ghi thô, sử dụng hàm `normalize_whitespace` và biểu thức chính quy để loại bỏ sạch các thẻ XML/HTML, chuẩn hóa khoảng trắng thừa.
- **Tính toán trường `age_days`:** Phân tích cú pháp ngày xuất bản sang `date` object và tính số ngày chênh lệch với `run_date`: `age_days = max(0, (run_date.date() - published_date).days)`.
- **Sinh cột `text_for_embedding` 5 phần:** Kết hợp `Title`, `Authors`, `Published Date`, `Categories`, và `Summary` có nhãn phân tách rõ ràng.
- **Khử trùng lặp và sắp xếp:** `drop_duplicates(subset=["paper_id"], keep="first")` và sắp xếp ổn định theo `published` DESC, `paper_id` ASC.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | JSON response từ Crossref API hoặc file snapshot `crossref_response.json` |
| Output                         | DataFrame 24 dòng x 16 cột lưu tại `papers_clean.csv` và `papers_clean.json` |
| Module phụ thuộc             | `core.config.Settings`, `core.utils` (`normalize_whitespace`, `compact_join`, `write_json`) |
| Module sử dụng output        | `src/retrieval/index.py` (ChromaDB), `src/observability/quality.py`, `src/evaluation/testset.py` |
| Điều kiện lỗi cần xử lý | Mất mạng, mã lỗi 429/503, bản ghi thiếu trường DOI hoặc ngày xuất bản không đủ năm-tháng-ngày |

### Cách xác minh

```bash
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
```

- **Kết quả mong đợi:** In ra dòng chữ `Tín hiệu hoàn thành: Clean thành công 24 dòng`.
- **Kết quả thực tế:** Trùng khớp 100% với kết quả mong đợi.
- **Artifact/log:** `data/raw/crossref_records.json`, `data/clean/papers_clean.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn cách cấu trúc trường `text_for_embedding` và kiến trúc chuyển đổi DataFrame trong `cleaning.py`.
- **Các phương án đã cân nhắc:**
  1. *Phương án 1 (Row-level Dictionary Projection):* Duyệt từng dòng bằng Python loop, format text 5 phần có nhãn rõ ràng (`Title: ...\nAuthors: ...`).
  2. *Phương án 2 (Vectorized Pandas .apply):* Nạp raw list thành DataFrame rồi dùng `.apply()` nhiều lần.
- **Phương án đã chọn:** Phương án 1 (Row-level Dictionary Projection).
- **Lý do:** Giúp xử lý ngoại lệ kiểu dữ liệu lồng nhau (`list[str]` trong authors, categories) triệt để, tránh các cảnh báo lệch timezone của Pandas datetime, và cấu trúc 5 phần có nhãn giúp embedding model (`all-MiniLM-L6-v2`) định vị chính xác ngữ nghĩa cho 4 nhóm câu hỏi benchmark.
- **Bằng chứng quyết định phù hợp:** Đạt Retrieval Hit Rate 100.0% và Mean Token F1 1.000 trong bài đánh giá Baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `NotImplementedError: Student task: implement source fetching` khi chạy lệnh nghiệm thu CP0.
- **Lệnh hoặc bước tái hiện:** `python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s)"`
- **Nguyên nhân gốc:** Hàm `parse_crossref_payload` và cơ chế fallback offline trong `src/ingestion/crossref.py` chưa được hiện thực hóa.
- **Cách xử lý:** Bổ sung hàm bóc tách dữ liệu từ JSON payload của Crossref, parse định dạng ngày `date-parts`, nối chuỗi họ tên tác giả, lọc bỏ thẻ `<jats:...>`, và thiết lập nhánh đọc file dự phòng khi có ngoại lệ kết nối mạng.
- **Cách xác minh sau khi sửa:** Chạy lại lệnh CP0, console in ra chính xác `Tín hiệu hoàn thành: Đã tải 24 bài báo`.
- **Điều học được:** Data Ingestion trong môi trường thực chiến luôn cần cơ chế Circuit Breaker / Offline Fallback để đảm bảo tính liên tục của Data Pipeline.

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

Kịch bản `drop_latest_records` (mất bản ghi mới nhất) và `blank_summary` + `inject_noise` gây ảnh hưởng nặng nề nhất, vì làm mất hoàn toàn vector tương ứng trong ChromaDB hoặc làm biến dạng không gian embedding, khiến cosine similarity không thể match câu hỏi với ngữ cảnh cần tìm.

Kết quả nào khác với kỳ vọng ban đầu?

Ban đầu nhóm kỳ vọng khi dữ liệu bị lỗi nặng thì agent sẽ ném exception và crash hệ thống; tuy nhiên trong thực tế hệ thống vẫn phản hồi nhưng câu trả lời sai lệch hoặc ảo giác (Silent Failure). Điều này khẳng định tầm quan trọng của Data Observability để phát hiện lỗi ngầm.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Về data pipeline: Tính Idempotent và việc bảo tồn bản lưu trữ thô bất biến (Immutable Raw Snapshot) là điều kiện tiên quyết để hệ thống có khả năng tự phục hồi mà không phụ thuộc vào trạng thái lỗi trước đó.
2. Về data quality/observability: Data Observability không chỉ là log kiểm tra thụ động mà phải là Quality Gate chủ động chặn đứng Silent Failure trước khi dữ liệu bẩn xâm nhập vào vector store.
3. Về ảnh hưởng của data đến RAG agent: RAG Agent hoàn toàn bất lực và sinh ảo giác nếu dữ liệu đầu vào bị thiếu hoặc nhiễu; chất lượng của AI bắt đầu từ chất lượng của Data Pipeline.

### Nếu có thêm thời gian

Tôi sẽ tích hợp thêm cơ chế tự động phát hiện Schema Drift thời gian thực (schema monitoring) và thiết lập dashboard Streamlit hiển thị biểu đồ phân bố độ tuổi bài báo cùng cảnh báo vi phạm SLA theo thời gian thực (hạng mục điểm thưởng Bonus B1/B2).

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hoàng Ngọc Đức  
**Ngày xác nhận:** 2026-09-26
