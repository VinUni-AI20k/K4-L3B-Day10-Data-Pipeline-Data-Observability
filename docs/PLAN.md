# KẾ HOẠCH THỰC HIỆN DỰ ÁN — Data Pipeline & Data Observability for RAG

> Tài liệu này gộp toàn bộ ngữ cảnh dự án (README, CHECKPOINTS, RUBRIC, SUBMISSION, report/README) thành **một kế hoạch hành động duy nhất**: đang có gì, còn thiếu gì, làm theo thứ tự nào, và ai làm phần nào nếu nhóm có đúng 4 thành viên.
> Đọc file này **sau** khi đã đọc [README.md](../README.md) và **trước khi** bắt đầu code.

---

## 1. Tổng quan dự án

**Mục tiêu:** Xây một RAG Agent trả lời câu hỏi trên tập metadata bài báo khoa học (nguồn Crossref API), đồng thời chứng minh 3 năng lực:

1. **Data Observability** — Great Expectations 1.x (4 expectations) + Freshness SLA (`age_days > 180`).
2. **Chống chịu lỗi dữ liệu (Corruption)** — tiêm 6 kịch bản làm bẩn dữ liệu, đo mức suy giảm hiệu năng RAG (Hit Rate, Token F1).
3. **Tự phục hồi (Idempotent Repair)** — khôi phục từ raw snapshot, đo lại metrics, xuất bảng so sánh 3 trạng thái **Baseline vs Corrupted vs Repaired**.

**Ràng buộc:** 240 phút, làm nhóm, deadline 23:59:59 cùng ngày, mỗi cá nhân tự nộp link repo lên LMS ([SUBMISSION.md](SUBMISSION.md)). Điểm dựa trên artifact + log thực chạy, không được bịa số liệu ([RUBRIC.md](RUBRIC.md)).

### Luồng dữ liệu end-to-end

```
Crossref API (hoặc data/raw/crossref_response.json khi offline)
   -> raw records (PaperRecord)                         [crossref.py]
   -> cleaned dataframe (+ age_days, text_for_embedding) [cleaning.py]
   -> ChromaDB index "papers-baseline" (MiniLM)          [index.py — ĐÃ CÓ SẴN]
   -> evaluation test set (10 câu, 4 loại)               [testset.py]
   -> baseline metrics (Hit Rate, Token F1)              [phase1.py + metrics.py]
   -> data quality + freshness report                    [quality.py]
   -> phase1_report.md                                   [reporting.py]
   -> corrupt dataframe (6 kịch bản)                      [corruption.py]
   -> ChromaDB index "papers-corrupted" -> corrupted metrics
   -> repair từ raw -> ChromaDB "papers-repaired" -> repaired metrics
   -> corruption_report.md (Baseline vs Corrupted vs Repaired) [reporting.py + corruption_flow.py]
```

---

## 2. Repo hiện có gì? (trạng thái scaffold — đã kiểm tra source thực tế)

| Module | Trạng thái | Việc cần làm |
|---|---|---|
| `core/config.py`, `core/utils.py` | ✅ Đã xong | Đọc để hiểu `Settings`/`Paths`, không cần sửa |
| `retrieval/embeddings.py`, `retrieval/index.py`, `retrieval/agent.py`, `retrieval/llm.py`, `retrieval/qa.py` | ✅ Đã xong | Không có `TODO`; chỉ cần **verify/chạy thử**, không cần viết lại |
| `evaluation/metrics.py` | ✅ Đã xong | Cung cấp Hit Rate / Token F1 sẵn cho `phase1.py` gọi |
| `ingestion/crossref.py` | 🔴 TODO | `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` |
| `ingestion/cleaning.py` | 🔴 TODO | `build_clean_dataframe` (dedup, `age_days`, `text_for_embedding`) |
| `evaluation/testset.py` | 🔴 TODO | `build_test_set` (10 câu, 4 loại: summary/authors/date/categories) |
| `observability/quality.py` | 🔴 TODO | `run_data_quality_checks` (GX 1.x), `build_freshness_report` |
| `observability/reporting.py` | 🔴 TODO | `generate_phase1_report`, `generate_corruption_report` |
| `ingestion/corruption.py` | 🔴 TODO | `corrupt_clean_dataframe` (6 kịch bản lỗi) |
| `pipelines/phase1.py` | 🔴 TODO | Nối toàn bộ luồng baseline end-to-end |
| `pipelines/corruption_flow.py` | 🔴 TODO | Nối luồng corrupt → evaluate → repair → compare |

**8 hàm/module cần code thật sự** — đây là khối lượng việc để chia cho 4 người.

---

## 3. Phân công 4 thành viên

Áp dụng đúng cấu hình đã được khuyến nghị sẵn trong [`report/README.md`](../report/README.md) mục "Nhóm 4 thành viên" — đây là cách chia **cân bằng nhất theo khối lượng TODO thực tế** (không chia máy móc theo thư mục, vì `retrieval/` đã xong sẵn nên không cần một người riêng cho nó).

| # | Vai trò | File sở hữu | Output phải bàn giao |
|---|---|---|---|
| **1** | **Source & Environment Owner** | `src/ingestion/crossref.py`, `.env` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` |
| **2** | **Data Model & Evaluation-Set Owner** | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` | `data/clean/papers_clean.{csv,json}`, `data/eval/test_set.json` |
| **3** | **Observability Owner** | `src/observability/quality.py`, `src/observability/reporting.py` | `data/quality/*.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` |
| **4** | **Corruption & Integration Owner** | `src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | `data/results/corruption_log.json`, `baseline/corrupted/repaired_metrics.json`, 2 flow chạy được end-to-end |

> Khớp với [`TEAM.md`](TEAM.md): điền đúng 4 dòng trong bảng thành viên theo vai trò trên. Nếu tên vai trò trong `TEAM.md` ghi khác chữ (vd. "Trưởng nhóm / Pipeline Integrator"), gán người đó vào **Thành viên 4** vì đây là vai trò điều phối tích hợp.
>
> ⚠️ Thành viên 4 gánh khối lượng tích hợp lớn nhất nhưng **vai trò là điều phối, không phải tự sửa lỗi của 3 module còn lại** — nếu module 1/2/3 lỗi, chủ module đó phải tự fix.
>
> Mọi thành viên vẫn phải hiểu toàn bộ luồng end-to-end để trả lời Q&A ở CP6 (GX 1.x, Freshness SLA, embeddings, tính idempotent).

### Checklist chi tiết từng người

**Thành viên 1 — Source & Environment (CP0, 0–30')**
- [ ] Tạo `.venv`, cài dependencies (`uv sync` hoặc `pip install -r requirements.txt`)
- [ ] Copy `.env.example` → `.env`, điền `GOOGLE_API_KEY` (hoặc provider khác)
- [ ] `parse_crossref_payload()`: duyệt `payload["message"]["items"]`, map DOI/title/abstract/authors/subject/dates/URLs → `PaperRecord`, bỏ record thiếu field bắt buộc
- [ ] `fetch_source_records()`: build params từ `settings.source_query/source_filter/max_results`, gọi API có retry cho `429/503`, lưu raw response, parse, lưu `raw_records_json`
- [ ] `load_raw_records()`: đọc JSON snapshot, map lại thành `PaperRecord` (dùng cho nhánh offline & cho bước Repair ở CP5)
- [ ] Verify: lệnh nghiệm thu CP0 trong [CHECKPOINTS.md](CHECKPOINTS.md#checkpoint-0) in ra "Đã tải 24 bài báo"
- [ ] Sau khi xong (~30'): hỗ trợ Thành viên 4 build thử ChromaDB index ở CP2, chuẩn bị `.env` demo cho CP6

**Thành viên 2 — Data Model & Evaluation-Set (CP1–CP2, 30–95')**
- [ ] `build_clean_dataframe()`: chuẩn hoá title/summary/authors/categories, parse `published`/`updated`, tính `age_days = (run_date - published).days`, tạo `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`, dedup theo `paper_id`, drop row xấu, sort
- [ ] Xuất `papers_clean.csv` / `papers_clean.json` — chốt schema này với Thành viên 3 & 4 trước khi họ code tiếp (contract dùng chung)
- [ ] `build_test_set()`: chọn paper đại diện, sinh câu hỏi 4 loại (`summary`, `authors`, `date`, `categories`), mỗi row có `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`; ghi `data/eval/test_set.json` (10 câu)
- [ ] Verify: lệnh nghiệm thu CP1 & CP2 trong CHECKPOINTS.md ("Clean thành công 24 dòng", "Sinh được 10 câu hỏi test")

**Thành viên 3 — Observability (CP1, CP3, CP5 — chạy song song với 2 & 4)**
- [ ] `run_data_quality_checks()`: dùng ephemeral context GX 1.x (`gx.get_context(mode="ephemeral")` → `add_pandas` → `add_dataframe_asset` → `add_batch_definition_whole_dataframe` → `get_batch`), định nghĩa 4 expectations: `ExpectTableRowCountToBeBetween`, `ExpectColumnValuesToNotBeNull`, `ExpectColumnValuesToBeUnique` (trên `paper_id`), `ExpectColumnValueLengthsToBeBetween`; ghi kết quả `data/quality/`
- [ ] `build_freshness_report()`: tìm `latest_published`/`oldest_published`, đếm `stale_rows` (`age_days > 180`), tính `is_fresh` (cảnh báo nếu tỷ lệ stale > 25%), ghi `freshness_report.json`
- [ ] Có thể bắt đầu code 2 hàm trên với dataframe giả (fixture nhỏ) ngay từ CP0, không cần chờ Thành viên 2 xong hẳn — chỉ cần thống nhất tên cột trước
- [ ] `generate_phase1_report()`: gom source summary + metrics + quality + freshness → markdown `phase1_report.md` (gọi trong CP3, sau khi Thành viên 4 wire xong `phase1.py`)
- [ ] `generate_corruption_report()`: bảng so sánh 3 trạng thái Baseline/Corrupted/Repaired (gọi trong CP5, sau khi Thành viên 4 wire xong `corruption_flow.py`)
- [ ] Verify: `Quality check status = True` (CP1), `phase1_report.md` sinh hoàn chỉnh (CP3), `corruption_report.md` có đủ 3 cột so sánh (CP5)

**Thành viên 4 — Corruption & Integration (CP3–CP5, 95–210' — nặng nhất, cần bắt tay sớm với 3 người kia)**
- [ ] CP2 (rảnh tay khi 2&3 đang code): thử gọi `LocalEmbeddingIndex.build(df, settings)` (đã có sẵn, không cần sửa) để build ChromaDB `papers-baseline`, đảm bảo import path đúng
- [ ] `phase1.py::main()` — nối theo đúng 10 bước đã có sẵn trong docstring: load settings → load/fetch raw → clean → save clean CSV/JSON → build Chroma index → tạo/load eval set → evaluate (dùng `evaluation/metrics.py`) → chạy quality+freshness → gọi `reporting.generate_phase1_report` → (optional) demo agent trên vài câu
- [ ] `corruption.py::corrupt_clean_dataframe()`: 6 kịch bản — drop latest 20% records, blank summary một số dòng, inject noise vào text, truncate title (<8 ký tự), lùi `published` về quá khứ, duplicate rows — rebuild `text_for_embedding`, ghi `corruption_log.json`
- [ ] `corruption_flow.py::main()` — nối theo 8 bước có sẵn: load baseline metrics + clean dataset → tạo corrupted dataframe → save artifacts → rebuild index + evaluate → quality/freshness trên corrupted → **repair** (dùng lại `load_raw_records` + `build_clean_dataframe` của Thành viên 1&2, tái tạo từ raw, không patch tay dữ liệu bẩn) → evaluate repaired → gọi `reporting.generate_corruption_report`
- [ ] Verify: `python script/run_phase1.py` và `python script/run_corruption_flow.py` chạy exit code 0, đủ `baseline/corrupted/repaired_metrics.json`

---

## 4. Lịch trình 240 phút — ai làm gì, khi nào sync

| Checkpoint | Thời gian | Việc chính | Ai chủ trì | Điểm sync bắt buộc |
|---|---|---|---|---|
| CP0 | 0–30' | Env, `.env`, `crossref.py` | TV1 | TV2/3/4 cài env song song, thống nhất schema `PaperRecord` với TV1 |
| CP1 | 30–65' | `cleaning.py`, `quality.py` | TV2, TV3 | TV2 chốt schema clean dataframe (tên cột) càng sớm càng tốt để TV3 code `quality.py` đúng cột |
| CP2 | 65–95' | `testset.py`, build Chroma index | TV2, TV4 | TV4 verify index build được từ clean dataframe của TV2 |
| CP3 | 95–120' | `phase1.py` wiring, `phase1_report.md` | TV4, TV3 | Chạy `run_phase1.py` — cả nhóm xem output cùng lúc |
| CP4 | 120–165' | `corruption.py` (6 kịch bản) | TV4 | TV1 xác nhận raw snapshot còn nguyên vẹn (dùng để repair) |
| CP5 | 165–210' | `corruption_flow.py`, `corruption_report.md` | TV4, TV3 | Chạy `run_corruption_flow.py` — cả nhóm review bảng 3 trạng thái |
| CP6 | 210–240' | Demo, Q&A, nộp bài | Cả nhóm | Checklist [SUBMISSION.md](SUBMISSION.md#8-checklist-trước-khi-nộp-link-lên-vlearn) |

**Nguyên tắc phối hợp** (đầy đủ hơn xem [report/README.md §3, §6](../report/README.md)):
- Chốt trước khi code song song: tên cột clean schema, cách tạo `paper_id`, schema câu hỏi eval set, đường dẫn artifact (dùng đúng `settings.paths.*`, không hardcode).
- Không ai sửa chữ ký hàm mà module khác đang gọi mà không báo cả nhóm.
- Baseline, corrupted, repaired phải dùng **chung một** `test_set.json` để so sánh có ý nghĩa.

---

## 5. Trước khi nộp bài (tóm tắt — chi tiết xem [SUBMISSION.md](SUBMISSION.md))

- [ ] `python script/run_phase1.py` và `python script/run_corruption_flow.py` exit code 0
- [ ] Đủ artifact: raw (2 file), clean, eval, quality, results (baseline/corrupted/repaired metrics + corruption_log), reports (2 file `.md`)
- [ ] `TEAM.md` điền đủ tên/MSSV/vai trò + phần tự khai cá nhân từng người
- [ ] Không commit `.env` hay bất kỳ API key nào
- [ ] GitHub Insights → Contributors: 100% thành viên có commit trên `main`
- [ ] Mỗi người tự nộp link repo lên VLearn LMS trước 23:59:59

## 6. Rủi ro dễ mất điểm (xem đầy đủ [RUBRIC.md §3](RUBRIC.md))

- Dùng cú pháp Great Expectations **cũ** (không phải GX 1.x ephemeral context) → -10đ, có thể crash
- Hardcode đường dẫn tuyệt đối (`C:\...`, `/home/...`) thay vì dùng `settings.paths` → -5đ
- Bịa số liệu trong report không khớp file JSON thực chạy → -20đ
- Thiếu file `TEAM.md`/`SUBMISSION.md`/`CHECKPOINTS.md` hoặc thiếu phần tự khai cá nhân → -5đ/lỗi

---

**Bonus (chỉ làm sau khi đạt ≥85đ phần bắt buộc, xem [RUBRIC.md §2](RUBRIC.md)):** B1 Dashboard quan sát (Streamlit/Gradio), B2 Self-healing pipeline tự động, B3 Pytest CI coverage >80%. Giao cho thành viên nào xong việc chính trước, không bắt buộc phân công cứng.
