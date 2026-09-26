# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `hihi`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-Day10-hihi-Data-Pipeline-Data-Observability` — https://github.com/nace1504/K4-L3B-Day10-hihi-Data-Pipeline-Data-Observability

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Doãn Hữu Nguyên | 2A202602671 | doanhuunguyen1504@gmail.com | **Trưởng nhóm** — Vai trò A: Data & Ingestion (`src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, raw data) | `report/2A202602671_DoanHuuNguyen.md` |
| 2 | Vũ Đình Thư | 2A202602652 | vuthu10b9@gmail.com | Vai trò B: Observability & Evaluation (`src/observability/quality.py`, `src/evaluation/testset.py`, `src/observability/reporting.py`) | `report/2A202602652_VuDinhThu.md` |
| 3 | Lê Quang Ngọc | 2A202602664 | ngoclequang12345@gmail.com | Vai trò C: Pipeline & Corruption (`src/pipelines/phase1.py`, `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`) | `report/2A202602664_LeQuangNgoc.md` |

*(Nhóm 3 thành viên — phân công theo bảng "Nhóm 3 thành viên" trong `report/README.md`.)*

---

## # Cá nhân

### ## DoanHuuNguyen-2A202602671
- **Vai trò:** Trưởng nhóm — Vai trò A: Data & Ingestion (CP0, phần cleaning của CP1).
- **Công việc chi tiết đã hoàn thành:**
  - `src/ingestion/crossref.py`:
    - `parse_crossref_payload()`: đọc `message.items` của Crossref, map DOI → `paper_id`, `title[0]`, abstract (bỏ tag JATS `<jats:p>`, `<jats:italic>`... bằng regex rồi chuẩn hóa khoảng trắng), `author[].given + family`, `subject` → `categories` (`primary_category` fallback `Uncategorized`), ngày từ `published`/`created` `date-parts` → `YYYY-MM-DD`, `URL` (fallback `https://doi.org/{doi}`); bỏ record thiếu DOI/title/abstract.
    - `fetch_source_records()`: dùng snapshot `data/raw/crossref_response.json` khi `REFRESH_SOURCE` tắt; khi refresh thì gọi `GET https://api.crossref.org/works`, retry tối đa 3 lần với exponential backoff (1s, 2s) khi gặp 429/503 hoặc lỗi mạng, hết retry thì fallback đọc snapshot cũ; lưu `crossref_response.json` và `crossref_records.json`.
    - `load_raw_records()`: đọc JSON snapshot và map lại thành `PaperRecord`.
    - Sửa `_fetch_from_api` để không sleep thừa sau lần thử cuối và ghi rõ lý do lỗi cuối cùng (HTTP status hoặc exception).
  - `src/ingestion/cleaning.py` — `build_clean_dataframe()`: chuẩn hóa title/summary/authors/categories, tính `age_days = (run_date - published).days`, sinh `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding` 5 phần (Title/Authors/Categories/Published/Summary), dedupe theo `paper_id`, lọc dòng rỗng, sort theo `published` giảm dần.
  - Kết quả chạy thật (2026-09-26): `Môi trường sẵn sàng`, `Đã tải 24 bài báo`, `Clean thành công 24 dòng`. Chi tiết trong `report/2A202602671_DoanHuuNguyen.md`.
- **Điều học được / Đóng góp chính:**
  - Giữ raw snapshot làm nguồn sự thật (source of truth): pipeline chạy lại được khi mất mạng / bị rate limit, và là nguồn để luồng repair (CP5) dựng lại dữ liệu sạch.
  - Dữ liệu nguồn "sống" (Crossref) cần được làm sạch ở biên ingestion (tag JATS, record thiếu trường) để lỗi không lan xuống embedding và retrieval.

### ## VuDinhThu-2A202602652
- **Vai trò:** Vai trò B — Observability & Evaluation.
- **File phụ trách:** `src/observability/quality.py`, `src/evaluation/testset.py`, `src/observability/reporting.py`.
- [Chờ Vũ Đình Thư tự cập nhật phần này]

### ## LeQuangNgoc-2A202602664
- **Vai trò:** Vai trò C — Pipeline & Corruption.
- **File phụ trách:** `src/pipelines/phase1.py`, `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`.
- [Chờ Lê Quang Ngọc tự cập nhật phần này]
