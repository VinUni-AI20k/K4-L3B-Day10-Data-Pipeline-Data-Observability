# C3 — Evaluation Test Set Contract (M2 → M4, evaluation/metrics.py)

> **Owner:** M2 · **Consumer:** M4 (truyền path cho `evaluate_pipeline`), `evaluation/metrics.py` (đóng băng) · **Version:** v1.0

## 1. Chữ ký hàm (KHÔNG đổi)

```python
build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]
```

Luôn ghi JSON (list) ra `output_path` bằng `core.utils.write_json` và trả về list đó.

## 2. Schema mỗi phần tử — đúng 5 key

| Key | Kiểu | Giá trị |
|---|---|---|
| `id` | `str` | `"q01"` … `"q10"` |
| `question_type` | `str` | một trong `summary`, `authors`, `date`, `categories` |
| `question` | `str` | theo template §3 |
| `ground_truth` | `str` | theo bảng §3 |
| `ground_truth_doc_ids` | `list[str]` | `[paper_id]` của paper được hỏi |

## 3. Template — PHẢI khớp bộ định tuyến trong `retrieval/qa.py`

`qa.py` tìm title nằm trong **dấu nháy đơn** để lookup chính xác và chọn câu trả lời theo từ khoá. Sai template = baseline F1 thấp vô lý.

| `question_type` | `question` | `ground_truth` |
|---|---|---|
| `summary` | `What is the main contribution of the paper '{title}'?` | `core.utils.first_sentence(summary)` |
| `authors` | `Who authored the paper '{title}'?` | `authors_joined` |
| `date` | `When was the paper '{title}' published?` | `published` |
| `categories` | `What categories does the paper '{title}' belong to?` | `categories_joined` |

Câu `summary` **không được** chứa các cụm `who authored`, `list the authors`, `when was`, `publication date`, `published on`, `what categories`.

## 4. Cách chọn paper — tất định (deterministic)

1. `pool = df[~df.title.str.contains("'") & (df.summary.str.len() > 0)].sort_values("paper_id").reset_index(drop=True)`; nếu `len(pool) < 10` → `raise ValueError`.
2. Chọn vị trí `round(i * (len(pool) - 1) / 9)` với `i = 0..9` (10 paper khác nhau).
3. Loại câu hỏi theo vị trí `i`: `[summary, authors, date, categories, summary, authors, date, categories, summary, authors]` → **3 summary / 3 authors / 2 date / 2 categories**.

## 5. Đóng băng test set

- Test set sinh **một lần từ clean baseline** và dùng lại **nguyên file** cho baseline / corrupted / repaired.
- M4 trong `phase1.py`: chỉ gọi `build_test_set` khi file chưa tồn tại **hoặc** `settings.refresh_test_set == True`; ngược lại đọc file.
- `corruption_flow.py` **không bao giờ** gọi `build_test_set`.
- File `data/eval/test_set.json` do M4 commit từ official run; ghi SHA-256 của file vào group report §6.

## 6. Nghiệm thu

```bash
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
python script/check_contracts.py testset
```

Nếu chưa có clean thật: dùng `pd.read_json('docs/rules/fixtures/clean.sample.json')` (fixture chỉ có 12 dòng, vẫn đủ 10).

## Changelog
| Version | Thay đổi | Người duyệt |
|---|---|---|
| v1.0 | Chốt ban đầu | cả nhóm |
