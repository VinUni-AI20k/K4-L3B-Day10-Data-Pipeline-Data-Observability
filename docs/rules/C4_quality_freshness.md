# C4 — Quality Gate & Freshness Contract (M3 → M4, M3-reporting)

> **Owner:** M3 · **Consumer:** M4 (pipelines), M3 (`reporting.py`) · **Input:** dataframe đúng C2 · **Version:** v1.0

## 1. Chữ ký hàm (KHÔNG đổi)

```python
run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]
build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]
```

- `report_name` ∈ `{"baseline", "corrupted", "repaired"}` (CP1 dùng `"test"` cũng phải chạy được).
- Bắt buộc cú pháp **GX 1.x ephemeral** (CHECKPOINTS CP1). Cấm API cũ (`ge.from_pandas`, `validator.expect_*`) → −10đ.

## 2. Bộ check — ID & tham số CỐ ĐỊNH (report và metrics tham chiếu theo ID)

| ID | GX Expectation / cách tính | Tham số | Dimension |
|---|---|---|---|
| `row_count` | `ExpectTableRowCountToBeBetween` | `min_value=ceil(0.95*settings.max_results)` (=23), `max_value=settings.max_results` (=24) | Volume |
| `paper_id_not_null` | `ExpectColumnValuesToNotBeNull` | `column="paper_id"` | Completeness |
| `title_not_null` | `ExpectColumnValuesToNotBeNull` | `column="title"` | Completeness |
| `summary_not_null` | `ExpectColumnValuesToNotBeNull` | `column="summary"` | Completeness |
| `paper_id_unique` | `ExpectColumnValuesToBeUnique` | `column="paper_id"` | Uniqueness |
| `title_length` | `ExpectColumnValueLengthsToBeBetween` | `column="title", min_value=8` | Validity |
| `summary_length` | `ExpectColumnValueLengthsToBeBetween` | `column="summary", min_value=50` | Completeness/Validity |
| `summary_no_noise` | `ExpectColumnValuesToNotMatchRegex` | `column="summary", regex=r"[@#$%&*~^]{4,}"` | Validity |
| `freshness_sla` | Không phải GX: `stale_ratio <= 0.25` (xem §4) | `threshold_days=settings.freshness_threshold_days` | Timeliness |

8 check đầu chạy trong **một** `ExpectationSuite` tên `papers_suite_{report_name}` qua `ValidationDefinition`.

## 3. Dict trả về của `run_data_quality_checks` — đúng các key

```json
{
  "report_name": "baseline",
  "success": true,
  "gx_success": true,
  "row_count": 24,
  "passed_checks": 9,
  "failed_checks": 0,
  "total_checks": 9,
  "checks": [
    {"id": "row_count", "expectation": "ExpectTableRowCountToBeBetween", "column": null,
     "dimension": "Volume", "success": true, "observed_value": 24, "unexpected_count": 0,
     "threshold": "23..24"}
  ],
  "freshness": {"stale_rows": 1, "total_rows": 24, "stale_ratio": 0.0417, "is_fresh": true},
  "generated_at": "2026-09-26T03:00:00+00:00"
}
```

- `checks`: đủ 9 phần tử, **đúng thứ tự bảng §2**. `column` = `null` cho `row_count`, `freshness_sla`. `observed_value` là số/chuỗi JSON-serializable (row count, % unexpected, hoặc stale_ratio). `unexpected_count` = `0` nếu không áp dụng.
- `success = gx_success and freshness.is_fresh`.
- Ghi file: `settings.paths.quality_dir / f"{report_name}_quality_report.json"` (→ `baseline_quality_report.json`, `corrupted_quality_report.json` khớp `config.py`; `repaired_quality_report.json`). Dùng `core.utils.write_json`.
- In: `[quality] <report_name>: success=<bool> passed=<p>/<t> failed=[<id>,...]`.

## 4. `build_freshness_report` — đúng các key

```json
{
  "latest_published": "2026-07-22",
  "oldest_published": "2026-03-28",
  "stale_rows": 1,
  "total_rows": 24,
  "stale_ratio": 0.0417,
  "threshold_days": 180,
  "max_stale_ratio": 0.25,
  "is_fresh": true,
  "generated_at": "2026-09-26T03:00:00+00:00"
}
```

- `stale_rows = (df.age_days > settings.freshness_threshold_days).sum()`; `stale_ratio = round(stale_rows/total_rows, 4)` (0 nếu rỗng); `is_fresh = stale_ratio <= 0.25`.
- Ghi đúng `report_path` do caller truyền (M4 truyền: baseline → `settings.paths.freshness_report`; corrupted → `quality_dir/"corrupted_freshness_report.json"`; repaired → `quality_dir/"repaired_freshness_report.json"`).
- `run_data_quality_checks` tính `freshness` bằng **cùng công thức** (có thể gọi hàm helper nội bộ, không ghi file freshness).

## 5. Kết quả kỳ vọng (để M1/M4 đối chiếu corruption có "trúng" gate)

| Check | Baseline | Corrupted (theo C5) | Repaired |
|---|---|---|---|
| `row_count` | ✅ 24 | ❌ 21 | ✅ 24 |
| `paper_id_unique` | ✅ | ❌ (2 duplicate) | ✅ |
| `title_length` | ✅ | ❌ (3 title 6 ký tự) | ✅ |
| `summary_length` | ✅ | ❌ (3 summary rỗng) | ✅ |
| `summary_no_noise` | ✅ | ❌ (3 dòng noise) | ✅ |
| `freshness_sla` | ✅ ~4% stale | ❌ ≥ 28% stale | ✅ |
| `*_not_null` | ✅ | ✅ (blank là `""`, không phải null → minh hoạ "silent") | ✅ |

Nếu kết quả thật khác bảng này → **ghi đúng thực tế**, báo M1/M4 để tìm nguyên nhân, không sửa tay.

## 6. Nghiệm thu

```bash
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json('docs/rules/fixtures/clean.sample.json'); print(run_data_quality_checks(df, s, 'test')['checks'][0])"
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Tín hiệu hoàn thành: Quality check status = {res[\"success\"]}')"
python script/check_contracts.py quality data/quality/test_quality_report.json
```

(Fixture 12 dòng sẽ fail `row_count` — đúng kỳ vọng, dùng để test nhánh fail.)

## Changelog
| Version | Thay đổi | Người duyệt |
|---|---|---|
| v1.0 | Chốt ban đầu | cả nhóm |
