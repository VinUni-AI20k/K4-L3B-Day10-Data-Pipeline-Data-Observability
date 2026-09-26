# HƯỚNG DẪN PHÂN CÔNG TEAMWORK - DAY 10

> **Tổng thời gian:** 240 phút (4 tiếng)
> **Nguyên tắc:** Mỗi người làm TRÊN BRANCH RIÊNG, không conflict

---

## 📊 TỔNG QUAN FILES & TRẠNG THÁI

### ✅ ĐÃ HOÀN THÀNH (Không cần làm)

| File                              | Trạng thái          |
| --------------------------------- | --------------------- |
| `src/core/config.py`            | ✅ Hoàn thành       |
| `src/core/utils.py`             | ✅ Hoàn thành       |
| `src/retrieval/embeddings.py`   | ✅ Hoàn thành       |
| `src/retrieval/index.py`        | ✅ Hoàn thành       |
| `src/retrieval/llm.py`          | ✅ Hoàn thành       |
| `src/retrieval/agent.py`        | ✅ Hoàn thành       |
| `src/retrieval/qa.py`           | ✅ Hoàn thành       |
| `src/evaluation/metrics.py`     | ✅ Hoàn thành       |
| `script/run_phase1.py`          | ✅ Wrapper sẵn sàng |
| `script/run_corruption_flow.py` | ✅ Wrapper sẵn sàng |

### ⚠️ CẦN HOÀN THIỆN (TODO)

| File                                 | Người phụ trách   |
| ------------------------------------ | --------------------- |
| `src/ingestion/crossref.py`        | 👤**NGƯỜI 1** |
| `src/ingestion/cleaning.py`        | 👤**NGƯỜI 1** |
| `src/ingestion/corruption.py`      | 👤**NGƯỜI 1** |
| `src/observability/quality.py`     | 👤**NGƯỜI 2** |
| `src/observability/reporting.py`   | 👤**NGƯỜI 2** |
| `src/evaluation/testset.py`        | 👤**NGƯỜI 3** |
| `src/pipelines/phase1.py`          | 👤**NGƯỜI 4** |
| `src/pipelines/corruption_flow.py` | 👤**NGƯỜI 4** |

---

## 👤 Gia Huy: DATA INGESTION MODULE

**Branch:** `giahuy-ingestion`
**Thời gian:** 0 - 90 phút
**Files:** 3 files trong `src/ingestion/`

> 📤 **OUTPUT cần tạo (để người khác dùng):**
> - `data/raw/crossref_response.json`
> - `data/raw/crossref_records.json`
> - `data/clean/papers_clean.json`
> - `data/clean/papers_clean.csv`

### 1.1 `src/ingestion/crossref.py` (3 functions)

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

### 1.2 `src/ingestion/cleaning.py` (1 function)

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

### 1.3 `src/ingestion/corruption.py` (1 function)

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

---

## 👤 Mạnh Hùng: OBSERVABILITY MODULE

**Branch:** `manhhung-observability`
**Thời gian:** 60 - 120 phút (⏳ **PHỤ THUỘC GIA HUY** - chỉ bắt đầu sau Checkpoint 1)
**Files:** 2 files trong `src/observability/`

> ⚠️ **QUAN TRỌNG:** Mạnh Hùng phải đợi Gia Huy xong `cleaning.py` và push lên branch trước. Khi `data/clean/papers_clean.json` tồn tại, Mạnh Hùng mới bắt đầu được.

### 2.1 `src/observability/quality.py` (2 functions)

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

### 2.2 `src/observability/reporting.py` (2 functions)

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

## 👤 Anh Minh: EVALUATION MODULE

**Branch:** `anhminh-evaluation`
**Thời gian:** 60 - 120 phút (⏳ **PHỤ THUỘC GIA HUY** - chỉ bắt đầu sau Checkpoint 1)
**Files:** 1 file trong `src/evaluation/`

> ⚠️ **QUAN TRỌNG:** Anh Minh phải đợi Gia Huy xong `cleaning.py` và push lên branch trước. Khi `data/clean/papers_clean.json` tồn tại, Anh Minh mới bắt đầu được.

### 3.1 `src/evaluation/testset.py` (1 function)

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

### ✅ Test sau khi xong:

```bash
python -c "
from core.config import load_settings
from evaluation.testset import build_test_set
import pandas as pd
s = load_settings()
df = pd.read_json(s.paths.clean_json)
ts = build_test_set(df, s.paths.eval_testset)
print(f'✅ Sinh được {len(ts)} câu hỏi test')
"
```

---

## 👤 Minh Tiến: PIPELINE INTEGRATION

**Branch:** `minhtien-pipeline`
**Thời gian:** 120 - 240 phút (⏳ **PHỤ THUỘC GIA HUY + ANH MINH + MẠNH HÙNG** - chỉ bắt đầu sau Checkpoint 3)
**Files:** 2 files trong `src/pipelines/`

> ⚠️ **QUAN TRỌNG:** Minh Tiến phải đợi cả 3 người kia xong và push lên branch trước. Khi:
> - `data/clean/papers_clean.json` tồn tại (từ Gia Huy)
> - `data/eval/test_set.json` tồn tại (từ Anh Minh)
> - `src/observability/` hoàn chỉnh (từ Mạnh Hùng)
> Thì Minh Tiến mới bắt đầu được.

### 4.1 `src/pipelines/phase1.py` (1 function)

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

### 4.2 `src/pipelines/corruption_flow.py` (1 function)

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

---

## 🔗 SƠ ĐỒ PHỤ THUỘC (DEPENDENCY)

### THỨ TỰ BẮT BUỘC:

| Thứ tự | Người | Module | Được phép bắt đầu khi |
|:-------:|-------|--------|-------------------------|
| **1** | 👤 **GIA HUY** | Ingestion | ✅ **LÀM TRƯỚC TIÊN** - Không đợi ai |
| **2** | 👤 **ANH MINH** | Evaluation | ⏳ Đợi Gia Huy xong `cleaning.py` |
| **2** | 👤 **MẠNH HÙNG** | Observability | ⏳ Đợi Gia Huy xong `cleaning.py` |
| **3** | 👤 **MINH TIẾN** | Pipeline | ⏳ Đợi cả 3 người trên xong |

### SƠ ĐỒ:

```
  ┌─────────────────┐
  │  1. GIA HUY     │
  │  (Ingestion)    │
  │  ✅ KHÔNG ĐỢI  │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  data/clean/    │
  │  papers_clean.json│
  └────────┬────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌─────────────┐
│2.ANH MINH│ │2.MẠNH HÙNG │
│Evaluation│ │Observability│
│ ⏳Đợi CP1│ │ ⏳ Đợi CP1 │
└────┬────┘ └──────┬──────┘
     │             │
     └──────┬──────┘
            ▼
  ┌─────────────────┐
  │ data/eval/     │
  │ test_set.json  │
  │ observability/ │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ 3. MINH TIẾN   │
  │   (Pipeline)    │
  │  ⏳ Đợi CP3    │
  └─────────────────┘
```

### ⚠️ THỨ TỰ BẮT BUỘC:

1. **GIA HUY làm TRƯỚC** → Tạo `data/raw/` và `data/clean/`
2. **ANH MINH + MẠNH HÙNG làm SAU** → Cần `data/clean/` từ Gia Huy
3. **MINH TIẾN làm CUỐI CÙNG** → Cần cả 3 người kia xong

---

## 📅 TIMELINE CHI TIẾT (CÓ CHECKPOINT ĐỢI)

```
PHÚT  | HOẠT ĐỘNG                              | NGƯỜI     | ĐỢI GÌ?
------|----------------------------------------|-----------|----------
0-30  | Gia Huy: crossref.py                   | GIA HUY   | -
30-60 | Gia Huy: cleaning.py                   | GIA HUY   | -
      |                                          |           |
      │  ⏸️ CHECKPOINT 1: GIA HUY PUSH           |           |
      │  → Có data/clean/papers_clean.json       |           |
      │                                          |           |
60-90 | Gia Huy: corruption.py + push            | GIA HUY   | -
      | Anh Minh: testset.py (bắt đầu sau CP1)  | ANH MINH  | ⏳ Đợi CP1
      | Mạnh Hùng: quality.py (bắt đầu sau CP1)| MẠNH HÙNG | ⏳ Đợi CP1
      │                                          |           |
      │  ⏸️ CHECKPOINT 2: GIA HUY PUSH           |           |
      │  → Có đủ ingestion module hoàn chỉnh    |           |
      │                                          |           |
90-120| Gia Huy: Review & support               | GIA HUY   | -
      | Anh Minh: testset.py (tiếp)              | ANH MINH  | ⏳ Từ CP1
      | Mạnh Hùng: reporting.py                 | MẠNH HÙNG | ⏳ Từ CP1
      │                                          |           |
      │  ⏸️ CHECKPOINT 3: ANH MINH + MẠNH HÙNG PUSH |     |
      │  → Có data/eval/test_set.json           |           |
      │  → Có observability module hoàn chỉnh    |           |
      │                                          |           |
120-150| Gia Huy: Support                        | GIA HUY   | -
      | Anh Minh: Review & support               | ANH MINH  | -
      | Mạnh Hùng: Review & support            | MẠNH HÙNG | -
      | Minh Tiến: phase1.py (bắt đầu sau CP3) | MINH TIẾN | ⏳ Đợi CP3
      │                                          |           |
      │  ⏸️ CHECKPOINT 4: MINH TIẾN PUSH          |           |
      │  → run_phase1.py chạy thành công        |           |
      │                                          |           |
150-180| Minh Tiến: corruption_flow.py            | MINH TIẾN | ⏳ Từ CP4
      │                                          |           |
      │  ⏸️ CHECKPOINT 5: RUN E2E                 |           |
      │  → run_corruption_flow.py thành công    |           |
      │                                          |           |
180-210| Tất cả: Fix bugs, test lại             | TẤT CẢ   | -
210-230| Hoàn thiện reports, TEAM.md            | TẤT CẢ   | -
230-240| Final check & submit                    | TẤT CẢ   | -
```

---

## 🚦 CHECKPOINT SIGNALS (ĐỂ BIẾT KHI NÀO NGƯỜI SAU ĐƯỢC BẮT ĐẦU)

### Checkpoint 1: GIA HUY xong `cleaning.py`
```
# Anh Minh & Mạnh Hùng CHỈ được bắt đầu khi:
python -c "
from core.config import load_settings
import json
settings = load_settings()
data = json.loads(settings.paths.clean_json.read_text())
print(f'✅ Có {len(data)} records sạch')
"
# Output: ✅ Có 24 records sạch
```

### Checkpoint 2: GIA HUY xong `ingestion/` module
```
# Cần có:
# - data/raw/crossref_response.json
# - data/raw/crossref_records.json  
# - data/clean/papers_clean.json
# - data/clean/papers_clean.csv
```

### Checkpoint 3: ANH MINH xong `testset.py`
```
# Minh Tiến CHỈ được bắt đầu pipeline khi:
python -c "
from core.config import load_settings
import json
data = json.loads(settings.paths.eval_testset.read_text())
print(f'✅ Có {len(data)} câu hỏi test')
"
# Output: ✅ Có 10 câu hỏi test
```

### Checkpoint 4: MẠNH HÙNG xong `observability/` module
```
# Cần có:
# - src/observability/quality.py hoàn chỉnh
# - src/observability/reporting.py hoàn chỉnh
```

### Checkpoint 5: MINH TIẾN xong `phase1.py`
```
# Test bằng:
python script/run_phase1.py
# Exit code phải = 0
```

---

## 🚀 CÁCH BẮT ĐẦU

### Bước 1: Mỗi người tạo branch riêng

```bash
# Người 1
git checkout -b giahuy-ingestion

# Người 2
git checkout -b manhhung-observability

# Người 3
git checkout -b anhminh-evaluation

# Người 4
git checkout -b minhtien-pipeline
```

### Bước 2: Sau khi xong file của mình - commit & push

```bash
# Sau khi hoàn thành tất cả files trong module
git add src/ingestion/
git commit -m "feat: complete ingestion module"

git push origin giahuy-ingestion
```

### Bước 3: Merge theo thứ tự (Người 4 làm)

```bash
# Người 4 checkout main
git checkout main
git pull origin main

# Merge theo thứ tự
git merge giahuy-ingestion   # Trước
git merge manhhung-observability # Sau
git merge anhminh-evaluation  # Sau
git merge minhtien-pipeline    # Cuối cùng

# Push lên main
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
2. **Nếu cần import từ module khác** - đợi họ push lên branch, sau đó rebase
3. **Test từng function** trước khi commit
4. **Commit thường xuyên** - tránh mất code
5. **Nếu conflict xảy ra** - chỉ người phụ trách file đó mới sửa

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
