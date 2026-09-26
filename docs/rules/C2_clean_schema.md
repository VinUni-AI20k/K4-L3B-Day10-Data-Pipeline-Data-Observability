# C2 — Clean Dataframe Contract (M2 → M1, M3, M4, retrieval)

> **Owner:** M2 · **Consumer:** M1 (`corruption.py`), M3 (`quality.py`), M4 (pipelines), `retrieval/index.py` (đóng băng) · **Version:** v1.0

## 1. Chữ ký hàm (KHÔNG đổi)

```python
build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame
compose_text_for_embedding(row: Mapping[str, Any]) -> str      # MỚI — public, M2 push đầu tiên
CLEAN_COLUMNS: list[str]                                         # MỚI — hằng số thứ tự cột
```

Hai symbol mới nằm trong `src/ingestion/cleaning.py`. M1 import: `from ingestion.cleaning import compose_text_for_embedding`.

## 2. Schema — đúng 16 cột, đúng thứ tự `CLEAN_COLUMNS`

| # | Cột | Kiểu | Ràng buộc | Ai dùng |
|---|---|---|---|---|
| 1 | `paper_id` | `str` | not null, **unique**, giữ nguyên từ C1 | tất cả, test set ground truth |
| 2 | `title` | `str` | len ≥ 8 | index lookup, test set |
| 3 | `summary` | `str` | len ≥ 50 | QA answer, GX |
| 4 | `authors` | `list[str]` | | |
| 5 | `categories` | `list[str]` | | |
| 6 | `primary_category` | `str` | | |
| 7 | `published` | `str` `YYYY-MM-DD` | **giữ dạng string**, không để Timestamp | index metadata, freshness, date question |
| 8 | `updated` | `str` `YYYY-MM-DD` | | |
| 9 | `abs_url` | `str` | | index metadata |
| 10 | `pdf_url` | `str` | | index metadata |
| 11 | `comment` | `str` | | |
| 12 | `age_days` | `int` | ≥ 0 | freshness |
| 13 | `authors_joined` | `str` | `", ".join(authors)` | QA answer "authors" |
| 14 | `categories_joined` | `str` | `", ".join(categories)` | QA answer "categories" |
| 15 | `summary_chars` | `int` | `len(summary)` | GX, report |
| 16 | `text_for_embedding` | `str` | xem §3 | index |

**Không có giá trị `None`/`NaN` ở bất kỳ ô nào** (chuỗi rỗng dùng `""`).

## 3. `text_for_embedding` — 5 phần, cố định từng ký tự

```python
def compose_text_for_embedding(row) -> str:
    return "\n".join([
        f"Title: {row['title']}",
        f"Authors: {row['authors_joined']}",
        f"Published: {row['published']}",
        f"Categories: {row['categories_joined']}",
        f"Summary: {row['summary']}",
    ])
```

## 4. Quy tắc xử lý (theo thứ tự)

1. Chuẩn hoá lại `title`, `summary` (bỏ tag còn sót, `normalize_whitespace`) — idempotent với dữ liệu đã sạch.
2. `age_days = max(0, (run_date.date() - date.fromisoformat(published)).days)`.
3. Lọc bỏ dòng có `paper_id`/`title`/`summary` rỗng.
4. Dedupe theo `paper_id`, `keep="first"` (theo thứ tự record đầu vào).
5. Tính cột 13–16.
6. Sort `published` **giảm dần**, rồi `paper_id` tăng dần; `reset_index(drop=True)`; reorder theo `CLEAN_COLUMNS`.
7. In đúng 1 dòng: `[cleaning] input=<n> dropped_invalid=<a> dropped_duplicates=<b> output=<m>` (số liệu này dùng cho group report §5).

`run_date` luôn là `datetime` có timezone UTC, do **caller (M4)** truyền vào — cleaning không tự gọi `now()`.

## 5. Ghi file (do M4 gọi, M2 không ghi)

- `settings.paths.clean_json`: `df.to_json(path, orient="records", force_ascii=False, indent=2)`
- `settings.paths.clean_csv`: `core.utils.write_csv(df, path)` (list được ghi dạng repr — CSV chỉ để xem, **JSON là nguồn chuẩn**).
- Đọc lại: `pd.read_json(path)` — đã kiểm chứng giữ `published` là string.

## 6. Nghiệm thu (M2 tự chạy)

```bash
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import PaperRecord; from core.utils import read_json; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe([PaperRecord(**r) for r in read_json(s.paths.raw_records_json)], datetime.now(timezone.utc)); df.to_json(s.paths.clean_json, orient='records', force_ascii=False, indent=2); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
python script/check_contracts.py clean
```

(Dòng trên tự dựng `PaperRecord` để **không chờ** `load_raw_records` của M1.) Kỳ vọng: 24 dòng. Nhớ **không commit** file clean sinh ra.

## Changelog
| Version | Thay đổi | Người duyệt |
|---|---|---|
| v1.0 | Chốt ban đầu; thêm `compose_text_for_embedding`, `CLEAN_COLUMNS` | cả nhóm |
