# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trần Tuấn Hoàng      |
| MSSV               | 2A202602832               |
| Khóa/Lớp         | K4-H202      |
| Tên nhóm         | 4aesieunhan         |
| Vai trò chính    | Xử lý dữ liệu từ các bài báo |
| Repository         | https://github.com/TuTu99999/K4-L3B-DAY10-4aesieunhan-DataPipelineDataObservability/tree/main    |
| Ngày hoàn thành | [2026-09-26]               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Thu thập metadata từ Crossref API và cất giữ bản gốc | `src/ingestion/crossref.py`: `parse_crossref_payload()`, `fetch_source_records()`, `load_raw_records()` | File snapshot `data/raw/crossref_response.json` hoặc response từ Crossref REST API | `data/raw/crossref_response.json` (raw JSON gốc), `data/raw/crossref_records.json` (danh sách PaperRecord đã bóc tách) | Hoàn thành |
| Làm sạch dữ liệu và chuẩn bị văn bản cho embedding | `src/ingestion/cleaning.py`: `build_clean_dataframe()` | `list[PaperRecord]` từ `load_raw_records()` | `data/clean/papers_clean.json`, `data/clean/papers_clean.csv` (24 dòng sạch, có cột `text_for_embedding`, `age_days`) | Hoàn thành |
| Thiết lập chốt kiểm soát chất lượng dữ liệu với Great Expectations 1.x | `src/observability/quality.py`: `run_data_quality_checks()`, `evaluate_freshness_sla()`, `build_freshness_report()` | DataFrame sạch từ `papers_clean.json` | Report JSON trong `data/quality/`, freshness report | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Sửa lỗi tương thích Python 3.10 (`datetime.UTC` không tồn tại ở phiên bản này) | `core/config.py`, `core/utils.py` | Thay `datetime.UTC` bằng `timezone.utc` để toàn bộ pipeline chạy được trên máy nhóm |
| Tối ưu `requirements.txt` cho máy CPU (không GPU) | Toàn nhóm | Thêm `--extra-index-url` trỏ về PyTorch CPU, loại bỏ các gói provider không dùng. Thời gian cài đặt giảm từ hơn 30 phút xuống dưới 5 phút |
| Chuyển import lazy cho `src/retrieval/llm.py` | Module retrieval | Các SDK provider không cài đặt (anthropic, openai, ollama) sẽ không gây crash khi import |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Parse payload Crossref, loại bỏ thẻ XML rác trong abstract, chuẩn hóa tên tác giả và ngày tháng | `src/ingestion/crossref.py` → `parse_crossref_payload()` | 24 bản ghi PaperRecord hợp lệ, lưu vào `data/raw/crossref_records.json` | `python script/run_clean.py` in ra "Thành công: Đã lưu 24 dòng" |
| Xây dựng DataFrame sạch với `text_for_embedding` theo cấu trúc 5 phần, tính `age_days`, khử trùng lặp theo `paper_id` | `src/ingestion/cleaning.py` → `build_clean_dataframe()` | `data/clean/papers_clean.json` và `papers_clean.csv` với 24 dòng | Lệnh kiểm tra bước 3 in ra "Clean thành công 24 dòng" |
| Cài đặt 4 Expectations bắt buộc trên GX 1.x ephemeral context, kết hợp đánh giá Freshness SLA | `src/observability/quality.py` → `run_data_quality_checks()` | Quality report JSON trong `data/quality/`, tất cả 31 metrics pass | `python script/test_step4.py` in ra "Quality check status = True" |

Một output cụ thể minh chứng cho phần việc: chạy `python script/test_step4.py` sẽ thấy progress bar `Calculating Metrics: 100%|██████████| 31/31` và kết quả `Quality check status = True`. File report tự động được ghi ra `data/quality/test_quality_report.json` chứa chi tiết từng expectation và trạng thái freshness.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu metadata bài báo khoa học thu về từ Crossref API ở dạng JSON thô, chứa các thẻ XML lẫn trong abstract (ví dụ `<jats:p>`, `</jats:p>`), ngày tháng ở dạng mảng lồng nhau (`date-parts: [[2026, 5, 20]]`), và tên tác giả tách riêng `given`/`family`. Dữ liệu ở trạng thái này chưa thể đưa vào mô hình embedding hay vector database được. Ngoài ra, cần có cơ chế kiểm soát để đảm bảo dữ liệu sạch trước khi đi vào hệ thống phục vụ (serving layer), tránh tình trạng Silent Failure khi dữ liệu bị lỗi mà không ai hay biết.

### Cách triển khai

Phần thu thập (`crossref.py`) được thiết kế theo hướng ưu tiên ổn định. Hàm `fetch_source_records` sẽ thử gọi Crossref REST API trước, nhưng nếu gặp lỗi mạng, timeout, hoặc bị rate limit (429), nó tự động chuyển sang đọc từ file snapshot local đã có sẵn trong repo (`data/raw/crossref_response.json`). Cơ chế fallback này giúp nhóm vẫn làm việc bình thường kể cả khi mạng yếu hoặc không có internet. Mọi dữ liệu gốc đều được lưu nguyên vẹn trước khi xử lý, để sau này nếu pipeline lỗi ở bước nào thì có thể chạy lại từ bản thô mà không phải gọi API lần nữa.

Phần làm sạch (`cleaning.py`) duyệt qua từng PaperRecord, chuẩn hóa khoảng trắng cho tất cả các trường text, parse ngày tháng từ chuỗi `YYYY-MM-DD` sang đối tượng `date` để tính `age_days`, rồi ghép nối 5 trường thông tin (title, authors, published, categories, summary) thành một đoạn văn bản có cấu trúc rõ ràng cho embedding. Cuối cùng, DataFrame được khử trùng lặp theo `paper_id` và sắp xếp theo ngày xuất bản giảm dần.

Phần kiểm soát chất lượng (`quality.py`) sử dụng Great Expectations 1.x theo đúng mẫu ephemeral context mới. Bốn expectations được thiết lập: kiểm tra số dòng nằm trong khoảng hợp lý (5 đến 5000), các cột quan trọng không được null, `paper_id` phải duy nhất, và `summary` phải đủ dài (tối thiểu 30 ký tự). Ngoài ra, hàm `evaluate_freshness_sla` tính tỷ lệ bài báo có `age_days > 180` và gắn cờ cảnh báo `is_fresh = False` nếu tỷ lệ này vượt quá 25%.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `data/raw/crossref_response.json` (JSON payload gốc từ Crossref) hoặc response trực tiếp từ API |
| Output | `data/raw/crossref_records.json` (danh sách PaperRecord), `data/clean/papers_clean.json` và `.csv` (DataFrame sạch), `data/quality/*.json` (báo cáo chất lượng) |
| Module phụ thuộc | `core/config.py` (settings, paths), `core/utils.py` (normalize_whitespace, read_json, write_json) |
| Module sử dụng output | `retrieval/index.py` (đọc DataFrame sạch để tạo ChromaDB index), `evaluation/testset.py` (đọc DataFrame để sinh câu hỏi test), `pipelines/phase1.py` (gọi toàn bộ chuỗi xử lý) |
| Điều kiện lỗi cần xử lý | API trả về 429/503 hoặc mất mạng (fallback sang snapshot local), file raw chưa tồn tại (raise FileNotFoundError rõ ràng), record thiếu DOI hoặc title (bỏ qua, không crash) |

### Cách xác minh

```bash
python script/run_clean.py
```

Kết quả mong đợi: In ra "Thành công: Đã lưu 24 dòng vào:" kèm đường dẫn JSON và CSV.

Kết quả thực tế: Đúng như mong đợi. File `papers_clean.json` chứa 24 bản ghi, mỗi bản ghi có đầy đủ `text_for_embedding`, `age_days`, `authors_joined`, `categories_joined`.

```bash
python script/test_step4.py
```

Kết quả mong đợi: `Quality check status = True`.

Kết quả thực tế: `Calculating Metrics: 100%|██████████| 31/31` → `Tín hiệu hoàn thành: Quality check status = True`.

Artifact: `data/quality/test_quality_report.json`, `data/clean/papers_clean.json`, `data/raw/crossref_records.json`.

## 5. Một quyết định kỹ thuật quan trọng

Bối cảnh: Khi parse abstract từ Crossref, dữ liệu gốc chứa các thẻ XML lồng nhau như `<jats:p>`, `<jats:italic>`, `<title>`. Câu hỏi đặt ra là nên dùng thư viện parser XML chuyên dụng (ví dụ BeautifulSoup hoặc lxml) hay chỉ dùng regex đơn giản.

Các phương án đã cân nhắc: (1) Dùng BeautifulSoup để parse chính xác cây DOM rồi lấy text. Ưu điểm là xử lý đúng mọi trường hợp lồng nhau, nhược điểm là thêm dependency nặng và chậm hơn. (2) Dùng regex `re.sub(r"<[^>]+>", " ", text)` để xóa toàn bộ thẻ. Ưu điểm là không cần thêm thư viện, nhanh, đủ chính xác cho trường hợp abstract đơn giản của Crossref.

Phương án đã chọn: Regex.

Lý do: Abstract từ Crossref thực tế chỉ chứa vài loại thẻ JATS đơn giản, không có cấu trúc lồng phức tạp. Regex hoạt động chính xác trong trường hợp này và giúp giữ `requirements.txt` nhẹ (không phải cài thêm BeautifulSoup). Với 24 bài báo, hiệu năng không phải vấn đề, nhưng việc giữ ít dependency giúp cài đặt môi trường nhanh hơn cho cả nhóm.

Bằng chứng: Sau khi chạy `parse_crossref_payload`, kiểm tra trường `summary` trong `data/raw/crossref_records.json` thấy tất cả 24 bản ghi đều sạch, không còn thẻ XML nào sót lại, text đọc được tự nhiên.

## 6. Một lỗi hoặc blocker đã xử lý

Triệu chứng: Khi chạy lệnh kiểm tra bước 3, Python báo `ImportError: cannot import name 'UTC' from 'datetime' (/usr/lib/python3.10/datetime.py)`.

Lệnh tái hiện:

```bash
PYTHONPATH=src python -c "from core.config import load_settings"
```

Nguyên nhân gốc: `datetime.UTC` là constant mới được thêm vào từ Python 3.11. Code gốc của project viết `from datetime import UTC`, nhưng máy của nhóm chạy Python 3.10 nên không có constant này.

Cách xử lý: Thay toàn bộ `from datetime import UTC` thành `from datetime import timezone` và đổi `datetime.now(UTC)` thành `datetime.now(timezone.utc)` trong 3 file: `core/config.py`, `core/utils.py`, và `observability/quality.py`. Cách viết `timezone.utc` tương thích với cả Python 3.10 lẫn 3.11+.

Cách xác minh sau khi sửa:

```bash
python script/run_clean.py
```

Chạy thành công, in ra "Thành công: Đã lưu 24 dòng".

Điều học được: Khi viết code cho dự án nhóm, nên tránh dùng các API chỉ có ở phiên bản Python mới nhất. `timezone.utc` là cách viết an toàn hơn `UTC` vì hoạt động trên mọi phiên bản Python 3.x.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu bắt đầu từ Crossref REST API (hoặc snapshot local). Hàm `fetch_source_records` tải payload JSON gốc về và lưu nguyên vẹn vào `data/raw/crossref_response.json`. Sau đó `parse_crossref_payload` bóc tách thành danh sách PaperRecord, lưu vào `data/raw/crossref_records.json`. Tiếp theo `build_clean_dataframe` chuẩn hóa text, tính `age_days`, ghép `text_for_embedding` và lưu ra file CSV/JSON sạch. Cuối cùng, module `retrieval/index.py` đọc DataFrame sạch, dùng mô hình `all-MiniLM-L6-v2` để sinh vector embedding cho mỗi tài liệu, rồi nạp vào ChromaDB collection. Như vậy dữ liệu đi từ API thô qua 3 lớp biến đổi (raw → clean → vector) trước khi sẵn sàng phục vụ truy vấn.

2. Evaluation set gồm 10 câu hỏi thuộc 4 nhóm nghiệp vụ (summary, authors, date, categories), mỗi câu đi kèm `ground_truth` (đáp án đúng) và `ground_truth_doc_ids` (danh sách `paper_id` chứa câu trả lời). Khi đánh giá, hệ thống gửi câu hỏi cho Agent, Agent truy vấn ChromaDB để lấy context rồi sinh câu trả lời. Retrieval hit rate đo xem trong top-k tài liệu trả về có chứa ít nhất một `paper_id` nằm trong `ground_truth_doc_ids` hay không. Token F1 so sánh mức độ trùng khớp từ ngữ giữa câu trả lời và ground truth. Nhờ có bộ test cố định, ta mới so sánh công bằng được giữa các trạng thái dữ liệu khác nhau.

3. Quality checks (GX 1.x) tập trung vào tính hợp lệ của schema dữ liệu tại một thời điểm: số dòng có đủ không, có null không, có trùng lặp không, summary có đủ dài không. Đây là kiểm tra tĩnh, trả lời câu hỏi "dữ liệu hiện tại có đúng format không". Freshness monitoring thì khác, nó đo lường khía cạnh thời gian: tỷ lệ bài báo quá cũ (`age_days > 180`) có vượt ngưỡng 25% hay không. Một dataset có thể pass toàn bộ quality check nhưng vẫn fail freshness nếu phần lớn bài báo đã quá hạn. Hai lớp kiểm tra bổ sung cho nhau, cùng quyết định `success` tổng thể.

4. Dùng cùng một bộ test set cho cả 3 trạng thái (baseline, corrupted, repaired) là để đảm bảo phép so sánh công bằng. Nếu mỗi trạng thái dùng bộ câu hỏi khác nhau thì không thể kết luận được sự sụt giảm hay phục hồi là do dữ liệu thay đổi hay do câu hỏi khác nhau. Giữ cố định biến đầu vào (test set) giúp cô lập được biến thay đổi duy nhất là chất lượng dữ liệu.

5. Repair được xem là thành công khi: (a) quality check trên dữ liệu repaired trả về `success = True` (tức là pass cả 4 GX expectations lẫn freshness SLA), và (b) các metric đánh giá RAG (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`) trên dữ liệu repaired quay về mức tương đương hoặc gần bằng baseline. Artifact cụ thể để đối chiếu là `repaired_metrics.json` so với `baseline_metrics.json`, cùng với `corruption_report.md` chứa bảng so sánh 3 cột.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | [Điền] | [Điền] | [Điền] | [Điền sau khi chạy full pipeline] |
| `mean_token_f1` | [Điền] | [Điền] | [Điền] | [Điền sau khi chạy full pipeline] |
| `judge_accuracy` | [Điền] | [Điền] | [Điền] | [Điền sau khi chạy full pipeline] |
| `mean_judge_score` | [Điền] | [Điền] | [Điền] | [Điền sau khi chạy full pipeline] |
| Quality checks | True | [Điền] | [Điền] | Baseline đã pass toàn bộ 4 GX expectations và freshness SLA |
| Freshness status | True | [Điền] | [Điền] | 24 bài báo đều trong khoảng 180 ngày gần đây |

### Kết luận từ số liệu

[Phần này điền sau khi nhóm chạy xong toàn bộ pipeline corruption và repair]

1. [Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi].
2. [Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi hoặc chưa phục hồi].

Corruption nào ảnh hưởng rõ nhất và vì sao: [Điền sau khi có số liệu thực tế].

Kết quả nào khác với kỳ vọng ban đầu: [Điền sau khi có số liệu thực tế].

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Về data pipeline: Việc cất giữ bản gốc (raw preservation) nghe đơn giản nhưng thực sự quan trọng. Khi pipeline lỗi ở bước làm sạch, nhóm có thể sửa code rồi chạy lại từ file raw mà không phải chờ gọi API (vốn hay bị rate limit). Thiết kế cơ chế fallback từ đầu cũng tiết kiệm rất nhiều thời gian debug.

2. Về data quality/observability: Great Expectations 1.x thay đổi khá nhiều so với bản cũ. Cú pháp ephemeral context (`gx.get_context(mode="ephemeral")`) và cách thêm batch definition khác hoàn toàn với tutorial cũ trên mạng. Bài học ở đây là luôn kiểm tra phiên bản thư viện trước khi copy code từ StackOverflow hay AI. Ngoài ra, freshness monitoring bổ sung góc nhìn mà quality check không có: dữ liệu có thể hoàn toàn hợp lệ về schema nhưng đã quá cũ để có giá trị.

3. Về ảnh hưởng của data đến RAG agent: Chất lượng câu trả lời của RAG phụ thuộc rất lớn vào chất lượng dữ liệu nạp vào vector store. Nếu summary bị rỗng hoặc bị chèn ký tự rác, embedding sinh ra sẽ sai lệch, dẫn đến retrieval trả về tài liệu không liên quan, và Agent đưa ra câu trả lời sai mà không hề báo lỗi (Silent Failure). Data observability giúp phát hiện vấn đề này trước khi nó ảnh hưởng đến người dùng.

### Nếu có thêm thời gian

Em sẽ thêm một lớp kiểm tra embedding drift: so sánh phân bố cosine similarity giữa các batch embedding mới và cũ. Nếu phân bố lệch quá nhiều thì có thể dữ liệu đầu vào đã thay đổi bản chất mà quality check schema không bắt được. Cách đo cải thiện là tính KL-divergence giữa hai phân bố và đặt ngưỡng cảnh báo tự động.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Tuấn Hoàng
**Ngày xác nhận:** 2026-09-26
