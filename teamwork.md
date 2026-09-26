# HƯỚNG DẪN PHÂN CÔNG TEAMWORK - DAY 10

> **Tổng thời gian:** 240 phút (4 tiếng)
> **Nguyên tắc:** Mỗi người làm TRÊN BRANCH RIÊNG, không conflict

---

## 👥 DANH SÁCH THÀNH VIÊN

| # | Tên | Branch | Module | Files |
|---|------|--------|--------|-------|
| 1 | 👤 **Gia Huy** | `giahuy-ingestion` | Data Foundation | 2 files |
| 2 | 👤 **Mạnh Hùng** | `manhhung-observability` | Data Observability | 2 files |
| 3 | 👤 **Anh Minh** | `anhminh-evaluation` | Evaluation + Corruption | 2 files |
| 4 | 👤 **Thế Việt** | `theviet-pipeline` | Pipeline Orchestration | 2 files |
| 5 | 👤 **Minh Tiến** | `minhtien-support` | Support + Integration | Review + Docs |

---

## 📊 TỔNG QUAN FILES & TRẠNG THÁI

### ✅ ĐÃ HOÀN THÀNH (Không cần làm)

| File | Trạng thái |
|------|------------|
| `src/core/config.py` | ✅ Hoàn thành |
| `src/core/utils.py` | ✅ Hoàn thành |
| `src/retrieval/embeddings.py` | ✅ Hoàn thành |
| `src/retrieval/index.py` | ✅ Hoàn thành |
| `src/retrieval/llm.py` | ✅ Hoàn thành |
| `src/retrieval/agent.py` | ✅ Hoàn thành |
| `src/retrieval/qa.py` | ✅ Hoàn thành |
| `src/evaluation/metrics.py` | ✅ Hoàn thành |
| `script/run_phase1.py` | ✅ Wrapper sẵn sàng |
| `script/run_corruption_flow.py` | ✅ Wrapper sẵn sàng |

### ⚠️ CẦN HOÀN THIỆN (TODO)

| File | Người phụ trách |
|------|------------------|
| `src/ingestion/crossref.py` | 👤 **Gia Huy** |
| `src/ingestion/cleaning.py` | 👤 **Gia Huy** |
| `src/observability/quality.py` | 👤 **Mạnh Hùng** |
| `src/observability/reporting.py` | 👤 **Mạnh Hùng** |
| `src/evaluation/testset.py` | 👤 **Anh Minh** |
| `src/ingestion/corruption.py` | 👤 **Anh Minh** |
| `src/pipelines/phase1.py` | 👤 **Thế Việt** |
| `src/pipelines/corruption_flow.py` | 👤 **Thế Việt** |

---

## 🔗 SƠ ĐỒ PHỤ THUỘC (DEPENDENCY)

### THỨ TỰ BẮT BUỘC:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. GIA HUY (TRƯỚC TIÊN)                                                  │
│     └─── ✅ KHÔNG ĐỢI AI                                                    │
│         ├── crossref.py                                                     │
│         └── cleaning.py ────────► tạo data/clean/                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
┌─────────────────────────────────┐    ┌─────────────────────────────────────┐
│  2. MẠNH HÙNG                 │    │  2. ANH MINH                       │
│     Observability               │    │     Evaluation + Corruption         │
│     ⏳ Đợi Gia Huy xong       │    │     ⏳ Đợi Gia Huy xong            │
│     ├── quality.py              │    │     ├── testset.py                  │
│     └── reporting.py            │    │     └── corruption.py               │
└─────────────────────────────────┘    └─────────────────────────────────────┘
                    │                                 │
                    └────────────────┬────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. THẾ VIỆT (CUỐI CÙNG)                                                 │
│     Pipeline Orchestration                                                  │
│     ⏳ Đợi Gia Huy + Mạnh Hùng + Anh Minh xong                           │
│     ├── phase1.py                                                          │
│     └── corruption_flow.py                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. MINH TIẾN (SUPPORT + INTEGRATION)                                      │
│     ⏳ Đợi Thế Việt xong phase1.py                                        │
│     ├── Review & Fix bugs                                                  │
│     ├── Hoàn thiện reports                                                 │
│     ├── Điền TEAM.md                                                      │
│     └── Final E2E test                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### BẢNG PHỤ THUỘC:

| Người | Bắt đầu khi | Kết thúc khi |
|-------|--------------|--------------|
| 👤 **Gia Huy** | ✅ Ngay lập tức | GIA HUY xong |
| 👤 **Mạnh Hùng** | ⏳ Gia Huy xong `cleaning.py` | MẠNH HÙNG xong |
| 👤 **Anh Minh** | ⏳ Gia Huy xong `cleaning.py` | ANH MINH xong |
| 👤 **Thế Việt** | ⏳ Mạnh Hùng + Anh Minh xong | THẾ VIỆT xong |
| 👤 **Minh Tiến** | ⏳ Thế Việt xong `phase1.py` | MỌI THỨ hoàn tất |

---

## 👤 GIA HUY: DATA FOUNDATION (TRƯỚC TIÊN)

**Branch:** `giahuy-ingestion`
**Thời gian:** 0 - 90 phút
**Files:** 2 files trong `src/ingestion/`

> ⚠️ **QUAN TRỌNG:** Gia Huy làm TRƯỚC TIÊN. Không đợi ai. Các bạn khác phụ thuộc vào output của Gia Huy.

> 📤 **OUTPUT cần tạo (để người khác dùng):**
> - `data/raw/crossref_response.json`
> - `data/raw/crossref_records.json`
> - `data/clean/papers_clean.json`
> - `data/clean/papers_clean.csv`

### 1.1 `src/ingestion/crossref.py`

```python
# Function 1: parse_crossref_payload(payload: dict) -> list[PaperRecord]
# - Duyệt payload["message"]["items"]
# - Trích xuất: DOI, title, abstract, authors, subject, dates, URLs
# - Chuẩn hóa text, loại bỏ record không hợp lệ
# - Trả về list PaperRecord

# Function 2: fetch_source_records(settings: Settings) -> list[PaperRecord]
# - Tạo params từ settings.source_query, source_filter, max_results
# - Gọi Crossref API với retry (429/503)
# - Lưu raw response vào settings.paths.raw_api_response
# - Parse payload bằng parse_crossref_payload
# - Lưu records vào settings.paths.raw_records_json

# Function 3: load_raw_records(path: Path) -> list[PaperRecord]
# - Đọc JSON snapshot
# - Map thành list PaperRecord
# - Fallback: đọc từ data/raw/crossref_response.json nếu API fail
```

### 1.2 `src/ingestion/cleaning.py`

```python
# build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame
# 1. Normalize title, summary, authors, categories
# 2. Parse published/updated date
# 3. Tính age_days = (run_date - published).days
# 4. Tạo các cột helper:
#    - authors_joined: ", ".join(authors)
#    - categories_joined: ", ".join(categories)
#    - summary_chars: len(summary)
#    - text_for_embedding: ghép 5 phần
#        "Title: {title}\nAuthors: {authors_joined}\nPublished: {published}\nCategories: {categories_joined}\nSummary: {summary}"
# 5. Drop duplicates theo paper_id
# 6. Sort dataframe và return
```

### ✅ Test sau khi xong:

```bash
python -c "
from datetime import datetime, timezone
from core.config import load_settings
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
s = load_settings()
r = load_raw_records(s.paths.raw_records_json)
df = build_clean_dataframe(r, datetime.now(timezone.utc))
print(f'✅ Clean thành công {len(df)} dòng')
"
```

### ✅ Checkpoint để bạn khác bắt đầu:

```bash
# Khi có output này, Mạnh Hùng & Anh Minh mới được bắt đầu:
ls data/clean/papers_clean.json  # File phải tồn tại
```

---

## 👤 MẠNH HÙNG: DATA OBSERVABILITY

**Branch:** `manhhung-observability`
**Thời gian:** 60 - 120 phút
**Files:** 2 files trong `src/observability/`

> ⏳ **PHỤ THUỘC:** Chỉ bắt đầu khi `data/clean/papers_clean.json` tồn tại (do Gia Huy tạo)

### 2.1 `src/observability/quality.py`

```python
# Function 1: run_data_quality_checks(df, settings, report_name) -> dict
# Sử dụng Great Expectations 1.x Ephemeral Context:
#
# from great_expectations import gx
# context = gx.get_context(mode="ephemeral")
# data_source = context.data_sources.add_pandas(name="papers_source")
# data_asset = data_source.add_dataframe_asset(name="papers_asset")
# batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
# batch = batch_def.get_batch(batch_parameters={"dataframe": df})
#
# 4 Expectations bắt buộc:
# 1. ExpectTableRowCountToBeBetween: 5-5000 rows
# 2. ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding
# 3. ExpectColumnValuesToBeUnique: paper_id
# 4. ExpectColumnValueLengthsToBeBetween: summary >= 30 chars
#
# Ghi results vào settings.paths.baseline_quality_report

# Function 2: build_freshness_report(df, settings, report_path) -> dict
# - Tính stale_count = rows có age_days > 180
# - stale_ratio = stale_count / total
# - is_fresh = (stale_ratio <= 0.25)
# - Ghi JSON report
```

### 2.2 `src/observability/reporting.py`

```python
# Function 1: generate_phase1_report(report_path, source_summary, metrics, quality, freshness)
# Tạo markdown với:
# - Source summary (số records, ngày fetch)
# - Metrics (Hit Rate, Token F1, Judge Score)
# - Quality check results
# - Freshness report
# Lưu vào settings.paths.baseline_report

# Function 2: generate_corruption_report(report_path, baseline, corrupted, repaired, ...)
# Tạo markdown SO SÁNH 3 trạng thái:
# | Metric | Baseline | Corrupted | Repaired |
# |--------|---------|----------|----------|
# | Hit Rate | 0.x | 0.y | 0.z |
# ...
```

### ✅ Test sau khi xong:

```bash
python -c "
from core.config import load_settings
from observability.quality import run_data_quality_checks
import pandas as pd
s = load_settings()
df = pd.read_json(s.paths.clean_json)
res = run_data_quality_checks(df, s, 'baseline')
print(f'✅ Quality check status = {res[\"success\"]}')
"
```

---

## 👤 ANH MINH: EVALUATION + CORRUPTION

**Branch:** `anhminh-evaluation`
**Thời gian:** 60 - 120 phút
**Files:** 2 files

> ⏳ **PHỤ THUỘC:** Chỉ bắt đầu khi `data/clean/papers_clean.json` tồn tại (do Gia Huy tạo)

### 3.1 `src/evaluation/testset.py`

```python
# build_test_set(df: pd.DataFrame, output_path) -> list[dict]
# Tạo 10 câu hỏi, phân bổ đều 4 types:
# - summary (3 câu): "What is the summary of paper 'X'?"
# - authors (3 câu): "Who authored paper 'X'?"
# - date (2 câu): "When was paper 'X' published?"
# - categories (2 câu): "What categories does paper 'X' belong to?"

# Format mỗi câu:
# {
#   "id": "eval_001",
#   "question_type": "summary",
#   "question": "What is the summary of the paper 'Title Here'?",
#   "ground_truth": "Nội dung câu trả lời đúng",
#   "ground_truth_doc_ids": ["doi_của_bài_báo"]
# }

# Lưu vào data/eval/test_set.json
```

### 3.2 `src/ingestion/corruption.py`

```python
# corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame
# Tiêm 6 corruption scenarios:
# 1. Drop latest records: bỏ 20% records mới nhất
# 2. Blank summary: xóa trắng summary ở 30% rows
# 3. Inject noise: chèn "!!!CORRUPTED!!!" vào text
# 4. Truncate title: cắt title < 8 ký tự
# 5. Stale date: lùi published về 365 ngày trước
# 6. Duplicate rows: nhân đôi 20% rows
# Rebuild text_for_embedding sau khi corrupt
# Ghi corruption_log.json với chi tiết từng lỗi
```

### ✅ Test sau khi xong:

```bash
# Test testset
python -c "
from core.config import load_settings
from evaluation.testset import build_test_set
import pandas as pd
s = load_settings()
df = pd.read_json(s.paths.clean_json)
ts = build_test_set(df, s.paths.eval_testset)
print(f'✅ Sinh được {len(ts)} câu hỏi test')
"

# Test corruption
python -c "
from core.config import load_settings
from ingestion.corruption import corrupt_clean_dataframe
import pandas as pd
s = load_settings()
df = pd.read_json(s.paths.clean_json)
c = corrupt_clean_dataframe(df, s.paths.corruption_log)
print(f'✅ Corrupted {len(c)} dòng')
"
```

---

## 👤 THẾ VIỆT: PIPELINE ORCHESTRATION

**Branch:** `theviet-pipeline`
**Thời gian:** 120 - 200 phút
**Files:** 2 files trong `src/pipelines/`

> ⏳ **PHỤ THUỘC:** Chỉ bắt đầu khi Mạnh Hùng + Anh Minh xong

### 4.1 `src/pipelines/phase1.py`

```python
# main() -> None
# Orchestrate toàn bộ phase 1:
#
# 1. Load settings
#    from core.config import load_settings
#    settings = load_settings()
#
# 2. Load hoặc fetch raw records
#    from ingestion.crossref import load_raw_records, fetch_source_records
#    if settings.refresh_source or not raw_path.exists():
#        records = fetch_source_records(settings)
#    else:
#        records = load_raw_records(settings.paths.raw_records_json)
#
# 3. Clean data
#    from ingestion.cleaning import build_clean_dataframe
#    from core.utils import now_utc, write_csv, write_json
#    from datetime import datetime, timezone
#    df = build_clean_dataframe(records, now_utc())
#    write_csv(df, settings.paths.clean_csv)
#    write_json(settings.paths.clean_json, df.to_dict(orient='records'))
#
# 4. Quality checks
#    from observability.quality import run_data_quality_checks, build_freshness_report
#    quality = run_data_quality_checks(df, settings, 'baseline')
#    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
#
# 5. Build ChromaDB index
#    from retrieval.index import LocalEmbeddingIndex
#    index = LocalEmbeddingIndex.build(df, settings)
#
# 6. Evaluation
#    from evaluation.metrics import evaluate_pipeline
#    bundle = evaluate_pipeline(
#        settings=settings,
#        index=index,
#        test_set_path=settings.paths.eval_testset,
#        metrics_output_path=settings.paths.baseline_metrics,
#        answers_output_path=settings.paths.baseline_answers
#    )
#
# 7. Generate report
#    from observability.reporting import generate_phase1_report
#    generate_phase1_report(
#        report_path=settings.paths.baseline_report,
#        source_summary={"records": len(records)},
#        metrics=bundle.summary,
#        quality=quality,
#        freshness=freshness
#    )
#
# 8. Print summary
#    print(f'✅ Phase 1 hoàn tất! Hit Rate: {bundle.summary[\"retrieval_hit_rate\"]:.2%}')
```

### 4.2 `src/pipelines/corruption_flow.py`

```python
# main() -> None
# Orchestrate corruption -> evaluate -> repair -> compare:
#
# 1. Load settings & baseline metrics
#    settings = load_settings()
#    from core.utils import read_json
#    baseline_metrics = read_json(settings.paths.baseline_metrics)
#    baseline_df = pd.read_json(settings.paths.clean_json)
#
# 2. Corrupt data
#    from ingestion.corruption import corrupt_clean_dataframe
#    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
#    corrupted_df.to_json(settings.paths.corrupted_clean_json)
#    corrupted_df.to_csv(settings.paths.corrupted_clean_csv)
#
# 3. Quality checks on corrupted
#    from observability.quality import run_data_quality_checks
#    corrupted_quality = run_data_quality_checks(corrupted_df, settings, 'corrupted')
#    # => Phải thất bại!
#
# 4. Build corrupted index & evaluate
#    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
#    corrupted_bundle = evaluate_pipeline(...)
#    corrupted_metrics = corrupted_bundle.summary
#
# 5. REPAIR: Load từ raw records
#    from ingestion.crossref import load_raw_records
#    from ingestion.cleaning import build_clean_dataframe
#    raw_records = load_raw_records(settings.paths.raw_records_json)
#    repaired_df = build_clean_dataframe(raw_records, now_utc())
#    repaired_df.to_json(settings.paths.repaired_clean_json)
#
# 6. Build repaired index & evaluate
#    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
#    repaired_bundle = evaluate_pipeline(...)
#    repaired_metrics = repaired_bundle.summary
#
# 7. Generate comparison report
#    from observability.reporting import generate_corruption_report
#    generate_corruption_report(
#        report_path=settings.paths.comparison_report,
#        baseline_metrics=baseline_metrics,
#        corrupted_metrics=corrupted_metrics,
#        repaired_metrics=repaired_metrics,
#        corrupted_quality=corrupted_quality,
#        repaired_quality=repaired_quality,
#        ...
#    )
#
# 8. Print comparison table
```

### ✅ Test sau khi xong:

```bash
python script/run_phase1.py
# Exit code phải = 0
```

---

## 👤 MINH TIẾN: SUPPORT + INTEGRATION

**Branch:** `minhtien-support`
**Thời gian:** 0 - 240 phút (xuyên suốt)
**Vai trò:** Support, Review, Docs, Final Integration

> ⏳ **PHỤ THUỘC:** Bắt đầu support sau Checkpoint 1, chính thức integrate sau Checkpoint 3

### Nhiệm vụ chi tiết:

#### 0-60 phút: Chuẩn bị & Support
- Setup `.env` file từ `.env.example`
- Kiểm tra môi trường hoạt động
- Support Gia Huy nếu cần

#### 60-120 phút: Review & Support
- Review code của Gia Huy (crossref, cleaning)
- Review code của Mạnh Hùng + Anh Minh nếu cần

#### 120-180 phút: Integration Support
- Support Thế Việt viết pipeline
- Review logic orchestration

#### 180-240 phút: Final Integration
- Test E2E: `python script/run_phase1.py`
- Test E2E: `python script/run_corruption_flow.py`
- Fix bugs nếu có
- Hoàn thiện reports
- Điền `docs/TEAM.md`

### Output cuối cùng:
```bash
# Kiểm tra tất cả artifacts có mặt:
ls data/results/baseline_metrics.json
ls data/results/corrupted_metrics.json
ls data/results/repaired_metrics.json
ls data/reports/phase1_report.md
ls data/reports/corruption_report.md
```

---

## 📅 TIMELINE CHI TIẾT

```
PHÚT  | HOẠT ĐỘNG                                  | NGƯỜI     | ĐỢI GÌ?
------|--------------------------------------------|-----------|----------
0-30  | Gia Huy: crossref.py                       | GIA HUY   | -
      | Minh Tiến: Setup .env, check env            | MINH TIẾN | -
30-60 | Gia Huy: cleaning.py                       | GIA HUY   | -
      | Minh Tiến: Support Gia Huy                 | MINH TIẾN | -
      |                                              |           |
      |  ⏸️ CHECKPOINT 1: GIA HUY PUSH              |           |
      |  → Có data/clean/papers_clean.json          |           |
      |                                              |           |
60-90 | Gia Huy: Review & Support                  | GIA HUY   | ✅ Xong
      | Mạnh Hùng: quality.py                      | MẠNH HÙNG | ⏳ Từ CP1
      | Anh Minh: testset.py                        | ANH MINH  | ⏳ Từ CP1
      | Minh Tiến: Review Gia Huy code              | MINH TIẾN | ⏳ Từ CP1
      |                                              |           |
90-120| Mạnh Hùng: reporting.py                    | MẠNH HÙNG | ⏳ Đang làm
      | Anh Minh: corruption.py                      | ANH MINH  | ⏳ Đang làm
      |                                              |           |
      |  ⏸️ CHECKPOINT 2: MẠNH HÙNG + ANH MINH PUSH |          |
      |  → Có observability + corruption module    |           |
      |                                              |           |
120-150| Gia Huy: Support                          | GIA HUY   | ✅ Xong
      | Mạnh Hùng: Review & Support               | MẠNH HÙNG | ✅ Xong
      | Anh Minh: Review & Support                  | ANH MINH  | ✅ Xong
      | Thế Việt: phase1.py (bắt đầu)            | THẾ VIỆT | ⏳ Từ CP2
      | Minh Tiến: Support Thế Việt                | MINH TIẾN | ⏳ Từ CP2
      |                                              |           |
      |  ⏸️ CHECKPOINT 3: THẾ VIỆT PUSH              |           |
      |  → run_phase1.py chạy thành công           |           |
      |                                              |           |
150-180| Thế Việt: corruption_flow.py               | THẾ VIỆT | ⏳ Đang làm
      | Minh Tiến: Review Thế Việt code            | MINH TIẾN | ⏳ Từ CP3
      |                                              |           |
      |  ⏸️ CHECKPOINT 4: FINAL E2E                  |           |
      |  → run_corruption_flow.py thành công       |           |
      |                                              |           |
180-200| Thế Việt: Fix bugs nếu có               | THẾ VIỆT | -
      | Minh Tiến: Test E2E                         | MINH TIẾN | -
      |                                              |           |
200-230| Tất cả: Review & Fix bugs                | TẤT CẢ   | -
      | Hoàn thiện reports, TEAM.md                | MINH TIẾN | -
      |                                              |           |
230-240| Final check & submit                       | TẤT CẢ   | -
```

---

## 🚦 CHECKPOINT SIGNALS

### Checkpoint 1: GIA HUY xong (60 phút)
```bash
# Mạnh Hùng & Anh Minh CHỈ được bắt đầu khi:
ls data/clean/papers_clean.json  # File phải tồn tại
```

### Checkpoint 2: MẠNH HÙNG + ANH MINH xong (120 phút)
```bash
# Thế Việt CHỈ được bắt đầu khi:
ls src/observability/quality.py    # Tồn tại
ls src/observability/reporting.py  # Tồn tại
ls src/ingestion/corruption.py      # Tồn tại
```

### Checkpoint 3: THẾ VIỆT xong phase1.py (150 phút)
```bash
# Test bằng:
python script/run_phase1.py
# Exit code phải = 0
```

### Checkpoint 4: FINAL E2E (180 phút)
```bash
python script/run_corruption_flow.py
# Exit code phải = 0
```

---

## 🚀 CÁCH BẮT ĐẦU

### Bước 1: Mỗi người tạo branch riêng

```bash
# Gia Huy
git checkout -b giahuy-ingestion

# Mạnh Hùng
git checkout -b manhhung-observability

# Anh Minh
git checkout -b anhminh-evaluation

# Thế Việt
git checkout -b theviet-pipeline

# Minh Tiến
git checkout -b minhtien-support
```

### Bước 2: Sau khi xong file của mình - commit & push

```bash
# Gia Huy
git add src/ingestion/
git commit -m "feat: complete ingestion module by Gia Huy"
git push origin giahuy-ingestion

# Mạnh Hùng
git add src/observability/
git commit -m "feat: complete observability module by Manh Hung"
git push origin manhhung-observability

# Anh Minh
git add src/evaluation/ src/ingestion/corruption.py
git commit -m "feat: complete evaluation and corruption by Anh Minh"
git push origin anhminh-evaluation

# Thế Việt
git add src/pipelines/
git commit -m "feat: complete pipeline orchestration by The Viet"
git push origin theviet-pipeline
```

### Bước 3: Merge theo thứ tự (Minh Tiến làm)

```bash
git checkout main
git pull origin main

# Merge theo thứ tự
git merge giahuy-ingestion           # Trước
git merge manhhung-observability    # Sau
git merge anhminh-evaluation       # Sau
git merge theviet-pipeline          # Sau
git merge minhtien-support          # Cuối cùng

git push origin main
```

### Bước 4: Test E2E

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

---

## ⚠️ LƯU Ý QUAN TRỌNG

1. **KHÔNG edit file của người khác** - chỉ edit trong module của mình
2. **Đợi checkpoint trước khi bắt đầu** - tránh conflict
3. **Test từng function** trước khi commit
4. **Commit thường xuyên** - tránh mất code
5. **Nếu conflict xảy ra** - chỉ người phụ trách file đó mới sửa
6. **Minh Tiến là người support** - giúp đỡ bất kỳ ai cần

---

## ✅ CHECKLIST HOÀN THÀNH

- [ ] `python script/run_phase1.py` → exit code 0
- [ ] `data/results/baseline_metrics.json` tồn tại
- [ ] `data/reports/phase1_report.md` tồn tại
- [ ] `python script/run_corruption_flow.py` → exit code 0
- [ ] `data/results/corrupted_metrics.json` tồn tại
- [ ] `data/results/repaired_metrics.json` tồn tại
- [ ] `data/reports/corruption_report.md` tồn tại
- [ ] Tất cả thành viên có commit trên nhánh `main`
- [ ] `docs/TEAM.md` điền đầy đủ
