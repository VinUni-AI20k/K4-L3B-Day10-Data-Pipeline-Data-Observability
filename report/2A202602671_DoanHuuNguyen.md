# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Doãn Hữu Nguyên |
| MSSV               | 2A202602671 |
| Khóa/Lớp         | K4 (K4-L3-DAY10) |
| Tên nhóm         | hihi |
| Vai trò chính    | Trưởng nhóm — Vai trò A: Data & Ingestion |
| Repository         | https://github.com/nace1504/K4-L3B-Day10-hihi-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Raw ingestion (CP0) | `src/ingestion/crossref.py`: `parse_crossref_payload`, `fetch_source_records`, `_fetch_from_api`, `load_raw_records` | Crossref `GET /works` (query/filter/rows từ `Settings`) hoặc snapshot `data/raw/crossref_response.json` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `list[PaperRecord]` (24 records) | Hoàn thành |
| Cleaning & data modeling (phần cleaning của CP1) | `src/ingestion/cleaning.py`: `build_clean_dataframe`, `build_text_for_embedding` | `list[PaperRecord]` + `run_date` | `pd.DataFrame` 24 dòng, 14 cột, có `age_days` và `text_for_embedding` | Hoàn thành |

Output của tôi là input trực tiếp cho: `quality.py` / `testset.py` (Vũ Đình Thư — cần dataframe sạch có `paper_id` duy nhất, `age_days`, `summary`), và `phase1.py` / `corruption_flow.py` (Lê Quang Ngọc — gọi `fetch_source_records`, `load_raw_records`, `build_clean_dataframe`; luồng repair dựng lại dữ liệu từ `crossref_records.json`).

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Cập nhật tài liệu nhóm (trưởng nhóm) | `docs/TEAM.md`, `report/group_report.md` | Điền thông tin nhóm, phân công, phần ingestion/cleaning; các phần CP2–CP5 để Thư/Ngọc tự cập nhật |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Parse Crossref JSON, bỏ tag JATS, bỏ record thiếu DOI/title/abstract | `crossref.py::parse_crossref_payload` | 24 `PaperRecord` từ 24 items của snapshot; 0 summary còn ký tự `<` | Lệnh CP0 + kiểm tra payload giả có tag JATS (mục 4) |
| Fetch có retry/backoff + fallback offline | `crossref.py::fetch_source_records`, `_fetch_from_api` | Mất mạng hoặc 429 x3 → vẫn trả 24 records từ snapshot | Mock `requests.get` (mục 4) |
| Clean dataframe, `age_days`, `text_for_embedding`, dedupe | `cleaning.py::build_clean_dataframe` | 24 dòng, `paper_id` duy nhất | Lệnh CP1 (cleaning) |

Output cụ thể mà phần việc của tôi tạo ra:

- `data/raw/crossref_response.json` (24 items) và `data/raw/crossref_records.json` (24 records).
- DataFrame sạch 24 dòng với 14 cột: `paper_id, title, summary, authors_joined, categories_joined, primary_category, published, updated, abs_url, pdf_url, comment, age_days, summary_chars, text_for_embedding`.
- Tại `run_date` 2026-09-26: `published` từ 2026-03-28 đến 2026-07-22, `age_days` từ 66 đến 182 (không có giá trị null), `summary_chars` từ 193 đến 296.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Đưa metadata bài báo từ Crossref (nguồn sống, có thể lỗi mạng / rate limit, abstract chứa markup JATS, record thiếu trường) thành một dataset sạch, ổn định, có định danh duy nhất để embed vào vector index và dùng làm nguồn đáng tin cậy cho bước repair.

### Cách triển khai

- **Parse:** duyệt `message.items`; `paper_id = DOI`; abstract được xóa mọi tag `<...>` bằng regex (thay bằng khoảng trắng để không dính chữ) rồi `normalize_whitespace`. Record thiếu DOI, title hoặc abstract bị loại ngay tại ingestion. Ngày lấy từ `published.date-parts`, fallback `created`; thiếu tháng/ngày thì bù `01`. Link dùng `URL`, fallback `https://doi.org/{doi}`.
- **Fetch:** mặc định (`REFRESH_SOURCE` không bật) đọc snapshot có sẵn → pipeline tái lập được. Khi refresh: tối đa 3 lần gọi, 429/503 hoặc `RequestException` thì chờ 1s rồi 2s (exponential backoff), không chờ sau lần cuối. Hết retry mà có snapshot cũ → fallback đọc snapshot; không có snapshot → raise lỗi.
- **Clean:** chuẩn hóa text, bỏ author/category rỗng, `age_days = (run_date - published).days` (gán timezone của `run_date` cho ngày không có tz), `text_for_embedding` gồm 5 dòng `Title / Authors / Categories / Published / Summary`, `drop_duplicates(subset=["paper_id"], keep="first")`, lọc title/summary rỗng, sort `published` giảm dần.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Crossref `/works` JSON (`message.items[]`: `DOI`, `title[]`, `abstract`, `author[]`, `subject[]`, `published`/`created`, `URL`) hoặc snapshot; `run_date` (UTC) |
| Output                         | `list[PaperRecord]` (11 trường); `crossref_response.json`, `crossref_records.json`; DataFrame sạch 14 cột |
| Module phụ thuộc             | `core/config.py` (`Settings`, paths), `core/utils.py` (`read_json`, `write_json`, `normalize_whitespace`, `compact_join`) |
| Module sử dụng output        | `observability/quality.py`, `evaluation/testset.py`, `retrieval/index.py`, `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Mất mạng, HTTP 429/503, record thiếu DOI/title/abstract, abstract có tag JATS, date-parts thiếu tháng/ngày, record trùng `paper_id` |

### Cách xác minh

```bash
python -c "import chromadb, great_expectations, sentence_transformers; print('Môi trường sẵn sàng')"
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
```

(Chạy bằng `.venv` của project với `PYTHONPATH=src`.)

- **Kết quả mong đợi:** `Môi trường sẵn sàng`, `Tín hiệu hoàn thành: Đã tải 24 bài báo`, `Tín hiệu hoàn thành: Clean thành công 24 dòng`.
- **Kết quả thực tế:** đúng cả 3 dòng trên (chạy ngày 2026-09-26). Lưu ý: `REFRESH_SOURCE` không bật nên lệnh CP0 đọc snapshot `crossref_response.json` có sẵn, không gọi API thật.
- **Kiểm tra bổ sung (mock, không ghi đè dữ liệu):**
  - `requests.get` ném `ConnectionError` → trả 24 records từ snapshot, sleep `[1, 2]`.
  - `requests.get` trả 429 cả 3 lần → 3 lần gọi, sleep `[1, 2]`, fallback 24 records.
  - Payload giả có abstract `<jats:title>Abstract</jats:title><jats:p>Hello <jats:italic>world</jats:italic></jats:p>` → summary `"Abstract Hello world"`; 2 record thiếu DOI/abstract bị loại; `date-parts [[2026, 3]]` → `2026-03-01`; không có `subject` → `Uncategorized`; không có `URL` → `https://doi.org/10.1/x`.
  - Đưa 24 records + 3 bản trùng (27) vào `build_clean_dataframe` → 24 dòng, `paper_id` duy nhất.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Crossref có thể rate limit (429) hoặc không truy cập được khi cả lớp cùng gọi, nhưng CP0 yêu cầu luôn ra 24 bài và các bước sau (repair, so sánh 3 trạng thái) cần dữ liệu ổn định.
- **Các phương án đã cân nhắc:** (1) Luôn gọi API, lỗi thì dừng pipeline; (2) Luôn gọi API, lỗi thì fallback snapshot; (3) Mặc định đọc snapshot, chỉ gọi API khi bật `REFRESH_SOURCE`, và khi gọi mà lỗi thì vẫn fallback snapshot.
- **Phương án đã chọn:** (3).
- **Lý do:** Tái lập được (reproducibility) — cùng input cho baseline/corrupted/repaired và giữa các thành viên; không phụ thuộc mạng khi demo; vẫn cho phép lấy dữ liệu mới có kiểm soát. Trade-off: dữ liệu có thể cũ nếu quên refresh — freshness do `quality.py` giám sát.
- **Bằng chứng quyết định phù hợp:** Lệnh CP0 ra 24 bài không cần mạng; test mock mất mạng / 429 x3 vẫn trả 24 records.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'core'` khi chạy script kiểm tra riêng.
- **Lệnh hoặc bước tái hiện:** chạy `.venv/Scripts/python.exe <script>.py` (script import `core.config`) mà không đặt `PYTHONPATH`.
- **Nguyên nhân gốc:** Package `core`, `ingestion`... nằm trong `src/`; khi chạy file ở thư mục khác, `src/` không nằm trong `sys.path`.
- **Cách xử lý:** chạy với `PYTHONPATH=src` (hoặc cài project bằng `pip install -e .` / `uv sync`).
- **Cách xác minh sau khi sửa:** chạy lại script với `PYTHONPATH=src` → in đủ kết quả kiểm tra ở mục 4.
- **Điều học được:** lệnh kiểm tra phải chạy trong cùng cấu hình môi trường (venv + đường dẫn package) với pipeline, nếu không lỗi môi trường sẽ bị nhầm thành lỗi code.

Ngoài ra, trong `_fetch_from_api` tôi sửa việc sleep thừa sau lần retry cuối (trước đây chờ thêm 4s trước khi fallback); sau khi sửa, test mock cho thấy chỉ sleep `[1, 2]`.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. `fetch_source_records` lấy JSON Crossref (hoặc snapshot) → `parse_crossref_payload` thành `PaperRecord` → lưu `data/raw/` → `build_clean_dataframe` tạo `text_for_embedding` → `LocalEmbeddingIndex.build` embed bằng `sentence-transformers/all-MiniLM-L6-v2` và nạp vào ChromaDB, mỗi document định danh bằng `paper_id` (DOI).
2. `testset.py` sinh câu hỏi 4 loại (`summary`, `authors`, `date`, `categories`) từ dataframe sạch, mỗi câu kèm `ground_truth` và `ground_truth_doc_ids = [paper_id]`. Retrieval đúng khi top-k (k=4) chứa doc id đó (`retrieval_hit_rate`); câu trả lời so với `ground_truth` (`mean_token_f1`, judge).
3. Quality checks (GX 1.x) kiểm tra cấu trúc/giá trị của từng bản dữ liệu: số dòng, not-null, unique `paper_id`, độ dài chuỗi. Freshness đo độ mới theo thời gian (`age_days` > 180 ngày chiếm quá 25% → không fresh) — dữ liệu có thể hợp lệ về schema nhưng vẫn cũ.
4. Để chênh lệch metric chỉ phản ánh thay đổi của dữ liệu, không phải do câu hỏi khác nhau.
5. Repair dựng lại dữ liệu từ `data/raw/crossref_records.json` (qua `load_raw_records` + `build_clean_dataframe` — phần của tôi), re-index rồi đánh giá lại; thành công khi `repaired_metrics.json` và quality/freshness trở về mức baseline, thể hiện trong `data/reports/corruption_report.md`. Phần chạy và số liệu CP5 do Lê Quang Ngọc phụ trách.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | N/A | N/A | N/A | N/A - do Lê Quang Ngọc phụ trách CP3/CP5 |
| `mean_token_f1`      | N/A | N/A | N/A | N/A - do Lê Quang Ngọc phụ trách CP3/CP5 |
| `judge_accuracy`     | N/A | N/A | N/A | N/A - do Lê Quang Ngọc phụ trách CP3/CP5 |
| `mean_judge_score`   | N/A | N/A | N/A | N/A - do Lê Quang Ngọc phụ trách CP3/CP5 |
| Quality checks         | N/A | N/A | N/A | N/A - GX suite do Vũ Đình Thư phụ trách (`quality.py`) |
| Freshness status       | N/A | N/A | N/A | N/A - do Vũ Đình Thư phụ trách. Dữ liệu đầu vào từ phần của tôi: 1/24 bài có `age_days` > 180 (tại 2026-09-26) |

### Kết luận từ số liệu

N/A - do Lê Quang Ngọc phụ trách CP3/CP5. Phần việc của tôi dừng ở dataset sạch 24 dòng; tôi chưa chạy các bước corruption/repair nên không đưa ra kết luận về metric.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** raw snapshot bất biến là nền tảng cho tái lập và repair — mọi bước sau đều có thể dựng lại từ đó.
2. **Data quality/observability:** nên chặn dữ liệu xấu ngay ở biên ingestion (thiếu trường, markup JATS, trùng `paper_id`), và fallback phải có kiểm chứng (test mất mạng / 429) chứ không chỉ viết `try/except`.
3. **Ảnh hưởng tới RAG agent:** `text_for_embedding` quyết định retriever "nhìn thấy" gì — nếu summary còn tag hoặc bị trùng document, vector sẽ nhiễu và retrieval lệch khỏi ground-truth doc id.

### Nếu có thêm thời gian

Ghi thêm metadata cho mỗi lần ingest (thời điểm fetch, nguồn là API hay snapshot, số record bị loại và lý do) vào một file log trong `data/raw/`. Lý do: hiện chưa biết chính xác snapshot được lấy lúc nào và bao nhiêu record bị loại ở bước parse. Cách đo: so sánh số items trong response với số records sau parse và sau clean qua các lần chạy.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Doãn Hữu Nguyên
**Ngày xác nhận:** [2026-09-26]
