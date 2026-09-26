# C5 — Corruption Contract (M1 → M4, M3-reporting)

> **Owner:** M1 · **Consumer:** M4 (`corruption_flow.py`), M3 (`generate_corruption_report`) · **Input:** dataframe đúng C2 · **Version:** v1.0

## 1. Chữ ký hàm (KHÔNG đổi)

```python
corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame
```

- **Không mutate** `df` đầu vào (`df = df.copy()` ngay dòng đầu) — M4 còn dùng baseline df sau đó.
- Output vẫn **đúng 16 cột C2**, không `None`/`NaN` (Chroma sẽ crash) → giá trị "hỏng" dùng `""`.
- Tất định: `rng = numpy.random.default_rng(42)`. Chạy 2 lần → output và log giống hệt (trừ `generated_at`).

## 2. Thuật toán chọn dòng (cố định)

1. `n0 = len(df)`. Sort `published` giảm dần, `paper_id` tăng dần.
2. **drop_latest_records:** bỏ `k = ceil(0.2 * n0)` dòng đầu (mới nhất). Với 24 dòng → bỏ 5 → còn 19.
3. Còn lại sort theo `paper_id` tăng dần → `order = rng.permutation(len(rest))`. Gán **không chồng lấn** theo thứ tự `order`:
   - 3 dòng đầu → `blank_summary`
   - 3 dòng kế → `inject_noise`
   - 3 dòng kế → `truncate_title`
   - `ceil(0.3 * len(rest))` dòng kế (=6) → `stale_date`
   - 2 dòng kế → `duplicate_rows` (nhân bản dòng **chưa bị làm bẩn**)

## 3. Sáu kịch bản — tên & tham số CỐ ĐỊNH

| # | `name` (key log) | Biến đổi | `params` trong log |
|---|---|---|---|
| 1 | `drop_latest_records` | Xoá k dòng mới nhất | `{"fraction": 0.2, "count": 5}` |
| 2 | `blank_summary` | `summary = ""` | `{"count": 3}` |
| 3 | `inject_noise` | `summary = f"{NOISE} {s[:mid]} {NOISE} {s[mid:]}"`, `mid = len(s)//2`, `NOISE = "@#$%&*~^"` | `{"count": 3, "noise_token": "@#$%&*~^"}` |
| 4 | `truncate_title` | `title = title[:6]` | `{"count": 3, "max_len": 6}` |
| 5 | `stale_date` | `published = published − 400 ngày` (string `YYYY-MM-DD`), `age_days += 400`; `updated` giữ nguyên | `{"count": 6, "shift_days": 400}` |
| 6 | `duplicate_rows` | Append bản sao y hệt (cùng `paper_id`) | `{"count": 2}` |

Sau 6 bước: tính lại `summary_chars = len(summary)` và `text_for_embedding = compose_text_for_embedding(row)` (import từ `ingestion.cleaning`, C2-§3) cho **mọi** dòng; sort lại như C2-§4 bước 6. Kết quả: **21 dòng**.

## 4. Schema `corruption_log.json`

Ghi bằng `core.utils.write_json(output_log_path, log)`:

```json
{
  "seed": 42,
  "input_rows": 24,
  "output_rows": 21,
  "generated_at": "2026-09-26T04:00:00+00:00",
  "scenarios": [
    {
      "name": "drop_latest_records",
      "description": "Drop the 20% most recently published records",
      "params": {"fraction": 0.2, "count": 5},
      "affected_rows": 5,
      "affected_paper_ids": ["10.1145/..."]
    }
  ]
}
```

- `scenarios`: đúng 6 phần tử, **đúng thứ tự bảng §3**.
- In: `[corruption] input=<n0> output=<n> scenarios=6`.

## 5. Nghiệm thu (M1 tự chạy, không cần chờ M2)

```bash
python -c "import pandas as pd; from ingestion.corruption import corrupt_clean_dataframe; df=pd.read_json('docs/rules/fixtures/clean.sample.json'); out=corrupt_clean_dataframe(df, 'data/results/corruption_log.json'); print(len(df), '->', len(out))"
python script/check_contracts.py corruption_log
```

Fixture 12 dòng → drop 3, còn 9 → chỉ đủ 3+3+3 dòng: các bước sau lấy `min(count, số dòng còn lại)` và ghi `affected_rows` thực tế (không crash). Khi có clean thật 24 dòng phải ra đúng 21.

## Changelog
| Version | Thay đổi | Người duyệt |
|---|---|---|
| v1.0 | Chốt ban đầu | cả nhóm |
