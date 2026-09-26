# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Dương Đức Vương |
| MSSV | 2A202602944 |
| Khóa/Lớp | K4 |
| Tên nhóm | Bar |
| Vai trò chính | Data Engineering & Data Corruption/Recovery |
| Repository | https://github.com/masao1112/K4-L3B-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data cleaning & pre-embedding modeling | `src/ingestion/cleaning.py` — `build_clean_dataframe()` | `list[PaperRecord]`, `run_date` | DataFrame sạch, `papers_clean.csv`/`.json` | Hoàn thành |
| Synthetic corruption suite | `src/ingestion/corruption.py` — `corrupt_clean_dataframe()` | Clean DataFrame | Corrupted DataFrame, `corruption_log.json` | Hoàn thành |
| Idempotent repair | `src/pipelines/corruption_flow.py` — `repair_from_raw_snapshot()` | `crossref_records.json` | Repaired DataFrame, `papers_clean_repaired.csv`/`.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Sửa router trả lời theo loại câu hỏi tiếng Việt | `src/retrieval/qa.py` | Câu hỏi về tác giả, ngày công bố, lĩnh vực và summary lấy đúng metadata/summary của tài liệu top-1 |
| Tích hợp luồng corruption → repair → comparison | `src/pipelines/corruption_flow.py` | Luồng lưu artifact corrupted/repaired, gọi index/evaluation và tạo cấu trúc báo cáo ba trạng thái |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Làm sạch corpus | `build_clean_dataframe()` | 24 bản ghi sạch; có `age_days`, `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding` | Gọi hàm với raw snapshot và kiểm tra `len(df) == 24`, `paper_id` là duy nhất |
| Tiêm lỗi thực nghiệm | `corrupt_clean_dataframe()`; `data/results/corruption_log.json` | 21 dòng sau corruption, 15 log entries thuộc đủ 6 action | Kiểm tra log và các điều kiện summary rỗng, title ngắn, `paper_id` trùng |
| Phục hồi từ raw snapshot | `repair_from_raw_snapshot()` | 24 dòng repaired, không trùng `paper_id` | Chạy repair trực tiếp và kiểm tra số dòng/khóa duy nhất |
| Sửa QA metadata routing | `_extract_answer()` | Trả đúng tác giả, ngày, categories và toàn bộ summary | Kiểm tra cục bộ bốn mẫu câu hỏi benchmark |

Artifact cụ thể do phần việc của tôi tạo hoặc kiểm chứng là `data/results/corruption_log.json`. Nhật ký lưu action, `paper_id` và giá trị trước/sau đối với từng dòng bị biến đổi, giúp truy vết nguyên nhân khi metrics suy giảm.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Raw metadata không thể đưa thẳng vào vector store vì có thể chứa markup, khoảng trắng thừa, ngày chưa chuẩn hóa và bản ghi trùng. Ngoài ra, cần mô phỏng các lỗi dữ liệu thực tế để chứng minh rằng RAG có thể suy giảm mà không ném exception, rồi phục hồi từ một nguồn raw đáng tin cậy.

### Cách triển khai

`build_clean_dataframe()` chuẩn hóa HTML/XML và khoảng trắng, chuẩn hóa các list authors/categories, parse ngày theo UTC, tính `age_days`, loại dòng thiếu khóa/title/summary/ngày, rồi loại trùng theo `paper_id`. Hàm ghép context chuẩn năm phần: Title, Authors, Published, Categories và Summary.

`corrupt_clean_dataframe()` làm việc trên bản sao của DataFrame để giữ nguyên baseline. Nó xác định 20% record mới nhất để drop, sau đó blank summary, inject noise, truncate title dưới tám ký tự, đặt ngày xuất bản lùi 365 ngày và append dòng trùng. Sau khi thay đổi, hàm cập nhật lại `summary_chars` và `text_for_embedding`, rồi ghi log JSON.

Repair không vá từng lỗi. `repair_from_raw_snapshot()` đọc lại `data/raw/crossref_records.json` và chạy lại cleaning để tái tạo artifact mới. Cách làm này idempotent: chạy nhiều lần vẫn cho cùng trạng thái sạch từ cùng snapshot.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input cleaning | `list[PaperRecord]` có DOI, title, summary, authors, categories, published và metadata liên quan |
| Output cleaning | DataFrame có `paper_id` duy nhất và `text_for_embedding` sẵn sàng cho embedding |
| Input corruption | Clean DataFrame chứa các cột metadata và context đã chuẩn hóa |
| Output corruption | DataFrame bẩn và log JSON có thể đối chiếu từng thay đổi |
| Module phụ thuộc | `ingestion.crossref`, `core.utils`, `pandas` |
| Module sử dụng output | `retrieval.index`, `observability.quality`, `evaluation.metrics`, `pipelines.corruption_flow` |
| Điều kiện lỗi xử lý | Thiếu các cột bắt buộc khi corruption, ngày không parse được, record thiếu khóa/title/summary |

### Cách xác minh

```bash
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(len(df))"

python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_csv(s.paths.clean_csv); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(len(c))"
```

- **Kết quả thực tế đã kiểm tra:** clean/repair tạo 24 dòng duy nhất; corruption tạo 21 dòng và 15 log entries.
- **Artifact/log:** `data/clean/papers_clean.csv`, `data/results/corruption_log.json`, `data/clean/papers_clean_repaired.csv`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn cách repair khi corpus bị lỗi.
- **Các phương án đã cân nhắc:** (1) vá từng record theo corruption log; (2) rebuild toàn bộ từ raw snapshot.
- **Phương án đã chọn:** Rebuild từ `data/raw/crossref_records.json`.
- **Lý do:** Log hữu ích để quan sát nhưng không nên là nguồn để tái tạo dữ liệu. Snapshot raw giữ lineage rõ ràng, tránh bỏ sót lỗi và đảm bảo chạy lặp lại cho cùng kết quả.
- **Bằng chứng:** Repair từ snapshot đã tạo lại 24 record với `paper_id` duy nhất sau khi corruption tạo duplicate và làm mất record.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `NotImplementedError: Student task: implement raw record loading.`
- **Bước tái hiện:** Chạy lệnh clean với `load_raw_records(s.paths.raw_records_json)`.
- **Nguyên nhân gốc:** Hàm đọc snapshot raw chưa được cài đặt nên pipeline dừng trước cleaning.
- **Cách xử lý:** Phối hợp với phần ingestion để dùng `load_raw_records()` đọc JSON và map thành `PaperRecord`; sau đó cleaning nhận đúng kiểu input.
- **Cách xác minh sau khi sửa:** Clean và repair đọc được raw snapshot, trả về 24 dòng sạch.
- **Điều học được:** Các contract giữa ingestion và cleaning cần được kiểm tra trước khi debug thuật toán biến đổi DataFrame.

## 7. Hiểu biết về luồng end-to-end

1. Crossref API hoặc snapshot local được parse thành `PaperRecord`, sau đó cleaning chuẩn hóa dữ liệu và tạo `text_for_embedding`. Embedding model biến context thành vector để ChromaDB lưu cùng metadata.
2. Test set giữ câu hỏi, ground truth và DOI đích. Retrieval Hit Rate kiểm tra DOI đích có nằm trong top-k; Token F1 và Judge đánh giá nội dung answer so với ground truth.
3. Quality checks kiểm tra tính đầy đủ, uniqueness và độ dài dữ liệu. Freshness monitoring đo độ cũ theo `age_days` và tỷ lệ stale so với SLA.
4. Cùng test set phải được dùng cho cả ba trạng thái để thay đổi metric chỉ phản ánh thay đổi corpus/index, không phải thay đổi độ khó của câu hỏi.
5. Repair thành công khi artifact repaired được rebuild từ raw snapshot, quality/freshness trở về trạng thái mong muốn và metrics quay lại gần baseline.

## 8. Phân tích kết quả

Các số liệu dưới đây được đối chiếu từ báo cáo nhóm và các artifact metrics của pipeline.

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | Drop record làm DOI đích không còn trong index; rebuild khôi phục corpus |
| `mean_token_f1` | 1.0000 | 0.5817 | 1.0000 | Summary rỗng và context bị mất làm answer kém khớp ground truth |
| `judge_accuracy` | 1.0000 | 0.6000 | 1.0000 | Chất lượng answer suy giảm cùng retrieval |
| `mean_judge_score` | 5.00 | 3.20 | 5.00 | Repair tái lập lại ngữ cảnh đúng |
| Quality checks | PASS | FAIL | PASS | Duplicate và blank summary phải bị gate phát hiện |
| Freshness status | FRESH | FRESH | FRESH | Corruption làm stale ratio tăng nhưng vẫn dưới ngưỡng SLA 25% |

Chuỗi bằng chứng chính là: drop latest records và blank summary làm Quality Gate phát hiện vi phạm, đồng thời giảm context truy xuất đúng nên Hit Rate/F1 giảm. Repair rebuild từ snapshot raw làm dữ liệu sạch trở lại, vì vậy index repaired có thể phục hồi metrics về baseline.

Lỗi ảnh hưởng rõ nhất là drop latest records, vì nó loại bỏ hẳn tài liệu đích thay vì chỉ làm nhiễu một phần text. Inject noise ít nghiêm trọng hơn do dense embedding vẫn có thể khai thác phần ngữ cảnh còn lại.

## 9. Điều học được và hướng cải thiện

1. Raw snapshot là cơ sở của data lineage và repair đáng tin cậy; không nên sửa trực tiếp artifact serving để phục hồi.
2. Data quality phải được kiểm tra trước indexing vì lỗi duplicate hoặc summary rỗng có thể tạo vector sai nhưng không làm chương trình crash.
3. Retrieval đúng là điều kiện cần cho answer đúng; Silent Failure nguy hiểm vì hệ thống vẫn trả lời dù dữ liệu bên dưới đã hỏng.

Nếu có thêm thời gian, tôi sẽ thêm test tự động cho cleaning/corruption với fixed input, đồng thời chặn bước index khi Quality Gate fail. Hiệu quả được đo bằng việc corrupted dataset không thể ghi đè collection serving.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Các kết quả kỹ thuật được đối chiếu với artifact hoặc báo cáo nhóm.
- [x] Tôi không ghi API key, token hoặc secret trong báo cáo.
- [x] Báo cáo này được viết riêng theo phần việc Data Engineering/Corruption Recovery.

**Họ và tên:** Dương Đức Vương  
**Ngày xác nhận:** 2026-09-26
