# Báo cáo cá nhân — Nguyễn Thị Lê Na

## Thông tin

| Trường | Giá trị |
|---|---|
| Họ tên | Nguyễn Thị Lê Na |
| Lớp / nhóm | K4-L3B-Day10 / Saphoaqua |
| Vai trò | Data Ingestion & Recovery Specialist |
| Phạm vi | `src/ingestion/` |
| Ngày hoàn thành | 2026-09-26 |

## Phần việc và bàn giao

| Module | Hàm chính | Đầu vào | Đầu ra |
|---|---|---|---|
| Ingestion | `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | Crossref hoặc snapshot | `data/raw/crossref_response.json`, `crossref_records.json` |
| Cleaning | `build_clean_dataframe` | `PaperRecord`, ngày chạy | DataFrame 16 cột, clean CSV/JSON |
| Corruption | `corrupt_clean_dataframe` | clean DataFrame | corrupted dataset và `corruption_log.json` |

## Thiết kế kỹ thuật

`crossref.py` hỗ trợ payload chuẩn (`message.items`) và snapshot dạng `items`, chuẩn hóa DOI, title, abstract, authors, categories, ngày xuất bản và URL. Abstract được loại thẻ HTML/XML. API có timeout và fallback về snapshot local để pipeline tái lập khi mất mạng/rate-limit; raw luôn được lưu trước downstream.

`cleaning.py` loại record thiếu `paper_id` hoặc title, chuẩn hóa chuỗi/list, tính `age_days`, tạo `text_for_embedding` theo Title/Authors/Published/Categories/Summary và loại duplicate theo `paper_id`. Kết quả clean có 24 dòng và 16 cột.

`corruption.py` mô phỏng sáu lỗi: drop 20% record mới nhất theo `published`, blank summary, thêm noise summary, cắt title, stale date 365 ngày và duplicate rows. Sau mỗi thay đổi, `text_for_embedding` được dựng lại và log JSON được ghi. Logic drop đã được sửa để “latest” dựa trên ngày, không phụ thuộc thứ tự dòng.

## Kiểm chứng

```powershell
$env:PYTHONPATH='src'
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import fetch_source_records, load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); fetch_source_records(s); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(len(df), df.paper_id.nunique())"
```

Kết quả: `24 24`. Corruption test: clean `24 x 16`, corrupted `23 x 16`, còn `20` ID duy nhất do duplicate 3 dòng; log có đủ 6 scenario.

## Kết quả chính sách chất lượng

| Trạng thái | Dòng | Quality gate | Freshness | Hit rate | Token F1 | Judge accuracy |
|---|---:|---|---|---:|---:|---:|
| Baseline | 24 | PASS | FRESH | 100% | 0.6676 | 70% |
| Corrupted | 23 | FAIL | FRESH | 70% | 0.4500 | 50% |
| Repaired | 24 | PASS | FRESH | 100% | 0.6676 | 70% |

Chính sách: dữ liệu phải qua quality gate trước khi index; freshness SLA là 180 ngày; gate fail thì không phát hành corrupted index; repair phải tái tạo từ raw snapshot và chạy lại quality/evaluation. Repair đã khôi phục toàn bộ metric về baseline.

## Phân tích

1. Corruption làm gate `PASS` → `FAIL`, Hit Rate `100%` → `70%`, Token F1 `0.6676` → `0.4500`, Judge accuracy `70%` → `50%`.
2. Re-ingest từ `data/raw/crossref_records.json` khôi phục 24 record unique, gate `PASS`, freshness `FRESH`, F1/Judge về `0.6676`/`70%`.

Hit Rate, Token F1 và Judge accuracy đều suy giảm khi corrupted; quality gate phát hiện lỗi dữ liệu trước khi corrupted index được phát hành.

## Artifact

- `data/raw/crossref_response.json`, `data/raw/crossref_records.json`
- `data/clean/papers_clean.json`, `data/clean/papers_clean_corrupted.json`
- `data/results/corruption_log.json`
- `data/quality/baseline_quality_report.json`, `corrupted_quality_report.json`, `repaired_quality_report.json`

Không ghi API key, token hoặc nội dung `.env` vào báo cáo.
