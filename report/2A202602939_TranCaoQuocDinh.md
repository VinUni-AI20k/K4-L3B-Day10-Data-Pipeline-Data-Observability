# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trần Cao Quốc Dinh             |
| MSSV               | 2A202602939                     |
| Khóa/Lớp         | K4-L3B                |
| Tên nhóm         | [Điền tên nhóm]     |
| Vai trò chính    | Source & Environment Owner                 |
| Repository         | K4-L3B-DAY10-Agent-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Môi trường & cấu hình | `.env`, `.venv` (qua `uv`) | `.env.example`, `pyproject.toml` | `.env` hợp lệ, venv Python 3.11 kích hoạt được | Một phần — venv activate được, `uv sync` đang cài dở do mạng chậm |
| Raw ingestion | `src/ingestion/crossref.py`: `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | Crossref API / snapshot `data/raw/crossref_response.json` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành phần code (compile OK); chưa chạy được lệnh nghiệm thu thật vì thiếu dependency |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Viết `docs/PLAN.md` phân công 4 thành viên | Cả nhóm | Chốt schema, thứ tự phụ thuộc và lịch trình 240 phút trước khi code song song |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Implement `parse_crossref_payload` | `src/ingestion/crossref.py` | Map payload Crossref (DOI/title/abstract/author/subject/published) sang `PaperRecord`, bỏ record thiếu field bắt buộc | `python -m py_compile src/ingestion/crossref.py` → pass |
| Implement `fetch_source_records` + `load_raw_records` | `src/ingestion/crossref.py` | Retry 429/503, fallback snapshot offline, ghi `raw_api_response`/`raw_records_json` | *Chưa chạy được* — chờ `uv sync` xong để test bằng lệnh nghiệm thu CP0 |

Output cụ thể: file `src/ingestion/crossref.py` không còn `NotImplementedError`, đã compile sạch. Chưa có artifact JSON thực chạy để đối chiếu — sẽ cập nhật báo cáo này sau khi verify.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi là điểm khởi đầu của toàn bộ pipeline: lấy dữ liệu bài báo từ Crossref (hoặc snapshot offline khi mất mạng/bị rate-limit) và chuẩn hoá thành `PaperRecord` để các module sau (`cleaning.py`, `index.py`, ...) dùng chung một schema ổn định.

### Cách triển khai

- `parse_crossref_payload`: duyệt `payload["message"]["items"]`, dùng DOI làm `paper_id`. Bóc tag JATS khỏi `abstract` bằng regex `<[^>]+>` vì Crossref trả `abstract` dạng XML. Ghép `given family` cho từng author. Lấy `subject[0]` làm `primary_category`. Chuyển `date-parts` (list `[year, month?, day?]`, có thể thiếu month/day) thành chuỗi `YYYY-MM-DD`, mặc định `1` cho phần thiếu. Bọc `try/except` quanh từng item để 1 record lỗi không làm hỏng cả batch; record thiếu `DOI`/`title`/ngày published hợp lệ bị bỏ qua.
- `fetch_source_records`: gọi `GET https://api.crossref.org/works` với `query.bibliographic`, `filter`, `rows` lấy từ `Settings`. Retry tối đa 3 lần với backoff `2**attempt` giây khi gặp `429`/`503` hoặc lỗi mạng (`requests.RequestException`). Nếu vẫn thất bại, fallback đọc lại `settings.paths.raw_api_response` đã có sẵn trên đĩa (đáp ứng yêu cầu chạy được khi offline). Nếu gọi API thành công, ghi đè raw response mới.
- `load_raw_records`: đọc JSON snapshot, `PaperRecord(**item)` cho từng phần tử — dùng ở bước Repair sau này để tái tạo dữ liệu từ nguồn gốc.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `Settings` (từ `core/config.py`): `source_query`, `source_filter`, `max_results`, `paths.*` |
| Output                         | `list[PaperRecord]`; side-effect ghi `data/raw/crossref_response.json` và `data/raw/crossref_records.json` |
| Module phụ thuộc             | `core/config.py` (Settings, Paths), `core/utils.py` (`normalize_whitespace`, `read_json`, `write_json`) |
| Module sử dụng output        | `src/ingestion/cleaning.py` (input `list[PaperRecord]`), `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` (bước Repair gọi `load_raw_records`) |
| Điều kiện lỗi cần xử lý | Mất mạng/API lỗi → fallback snapshot; record thiếu field bắt buộc → bỏ qua; `date-parts` thiếu month/day → mặc định ngày 1 |

### Cách xác minh

```bash
source .venv/bin/activate
export PYTHONPATH=src
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
```

- **Kết quả mong đợi:** `Tín hiệu hoàn thành: Đã tải 24 bài báo`.
- **Kết quả thực tế:** *Chưa chạy được* — `uv sync` chưa cài xong dependency (`ModuleNotFoundError: No module named 'dotenv'` khi thử lần đầu vì venv gần như trống). Sẽ cập nhật sau khi `uv sync` hoàn tất.
- **Artifact/log:** sẽ là `data/raw/crossref_response.json`, `data/raw/crossref_records.json` sau khi chạy thành công.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `fetch_source_records` cần vừa gọi API thật vừa chạy được khi không có mạng (yêu cầu CHECKPOINTS CP0).
- **Các phương án đã cân nhắc:**
  1. Chỉ gọi API, không có fallback — đơn giản nhưng crash ngay khi mất mạng hoặc gặp `429`.
  2. Luôn ưu tiên đọc snapshot local trước, chỉ gọi API nếu chưa có snapshot — tránh gọi API thật nhưng dữ liệu dễ bị cũ.
  3. Ưu tiên gọi API thật kèm retry, chỉ fallback snapshot khi API thất bại hẳn — cân bằng giữa dữ liệu mới và khả năng chạy offline.
- **Phương án đã chọn:** Phương án 3.
- **Lý do:** Đảm bảo dữ liệu mới nhất khi có mạng, nhưng vẫn không chặn tiến độ nhóm khi mạng lab không ổn định hoặc bị Crossref rate-limit giữa buổi.
- **Bằng chứng quyết định phù hợp:** *Sẽ bổ sung sau khi chạy thực tế và log được số lần retry/fallback xảy ra trong buổi lab.*

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ImportError: cannot import name 'AttrsInstance' from 'attr'` khi chạy `python -c "import chromadb..."`.
- **Lệnh hoặc bước tái hiện:** Chạy `python -c "import chromadb..."` ngay sau `uv sync` mà không activate venv.
- **Nguyên nhân gốc:** Lệnh dùng `python3` hệ thống (`/usr/bin/python3`, 3.10) thay vì `.venv` của project; máy có sẵn package `attrs`/`attr` xung đột từ môi trường Python khác (ROS) cài ở `~/.local/lib/python3.10/site-packages`.
- **Cách xử lý:** `source .venv/bin/activate` trước khi chạy bất kỳ lệnh `python` nào của project; luôn kiểm tra `which python` trỏ đúng vào `.venv/bin/python`.
- **Cách xác minh sau khi sửa:** `which python` → `.../.venv/bin/python`; `python --version` → `Python 3.11.15`. (Đã xác minh xong bước activate.)
- **Điều học được:** Không được giả định `python`/`pip` mặc định trỏ đúng venv — luôn kiểm tra path trước khi debug sâu hơn vào code.

Blocker còn tồn đọng:

- **Phạm vi bị ảnh hưởng:** Toàn bộ lệnh nghiệm thu CP0 chưa chạy được vì `.venv` chưa cài đủ package (`uv sync` bị timeout mạng giữa chừng khi tải `websocket-client`/`torch`).
- **Những gì đã loại trừ:** Không phải lỗi code (`crossref.py` compile sạch); không phải lỗi cấu hình `.env` (đã sửa `LLM_PROVIDER` đúng); là vấn đề cài đặt dependency do mạng chậm.
- **Bước tiếp theo:** Chạy lại `uv sync` (có thể cần `UV_HTTP_TIMEOUT=180`), chờ chạy xong hẳn rồi verify CP0.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref → `fetch_source_records`/`parse_crossref_payload` tạo `PaperRecord` → `cleaning.py` chuẩn hoá thành dataframe sạch (`text_for_embedding`, `age_days`) → `index.py` (đã có sẵn) sinh embedding MiniLM và nạp vào ChromaDB.
2. Evaluation set (`testset.py`) sinh câu hỏi kèm `ground_truth_doc_ids` trỏ về `paper_id` trong index, dùng để tính Hit Rate (retrieval có tìm đúng document không) và Token F1 (câu trả lời agent có khớp ground truth không).
3. Quality checks (GX 1.x) kiểm tra cấu trúc dữ liệu tĩnh (row count, null, unique, độ dài) tại một thời điểm; freshness monitoring theo dõi riêng `age_days` để cảnh báo dữ liệu quá hạn theo SLA — hai việc khác mục tiêu dù cùng nằm trong `quality.py`.
4. Phải dùng chung một `test_set.json` cho baseline/corrupted/repaired vì nếu đổi bộ câu hỏi giữa các lần đo, chênh lệch metric có thể do câu hỏi khác nhau chứ không phải do chất lượng dữ liệu thay đổi — làm mất ý nghĩa so sánh.
5. Repair được coi là thành công khi: `repaired_metrics.json` gần khôi phục lại mức của `baseline_metrics.json` (không nhất thiết y hệt), và quality/freshness report trên dữ liệu repaired trở lại trạng thái `success=True`/`is_fresh=True` như baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |  *chưa có* |  *chưa có* |  *chưa có* | Pipeline chưa chạy end-to-end (blocker ở mục 6) |
| `mean_token_f1`      |  *chưa có* |  *chưa có* |  *chưa có* | — |
| `judge_accuracy`     |  *chưa có* |  *chưa có* |  *chưa có* | — |
| `mean_judge_score`   |  *chưa có* |  *chưa có* |  *chưa có* | — |
| Quality checks         |  *chưa có* |  *chưa có* |  *chưa có* | — |
| Freshness status       |  *chưa có* |  *chưa có* |  *chưa có* | — |

### Kết luận từ số liệu

*Sẽ hoàn thiện phần này sau khi `script/run_phase1.py` và `script/run_corruption_flow.py` chạy xong và sinh đủ artifact thật — không ghi số liệu suy đoán ở đây.*

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data lineage: luôn giữ nguyên raw snapshot (`crossref_response.json`) trước khi biến đổi, vì đó là nguồn duy nhất để Repair sau này.
2. Data quality/observability: cơ chế fallback offline cũng là một dạng "graceful degradation" cần thiết kế có chủ đích, không phải xử lý lỗi tuỳ tiện.
3. Ảnh hưởng của môi trường thực thi: một lỗi tưởng như "lỗi code" (`ImportError` khi import chromadb) thực chất là lỗi môi trường (sai interpreter) — luôn kiểm tra `which python` trước khi debug logic.

### Nếu có thêm thời gian

Viết thêm 1 test nhỏ (không cần pytest đầy đủ) cho `parse_crossref_payload` với vài payload giả (thiếu DOI, thiếu date-parts, abstract có nhiều tag lồng nhau) để chắc chắn hàm không crash trên dữ liệu Crossref thật đa dạng hơn snapshot mẫu.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách. *(cần ôn thêm phần corruption/repair trước khi demo)*
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu. *(mục 8 đang để trống đúng vì chưa có artifact thật)*
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Cao Quốc Dinh
**Ngày xác nhận:** 2026-09-26
