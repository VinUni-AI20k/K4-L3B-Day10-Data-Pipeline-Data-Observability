# Danh sách thành viên và phân công nhóm

- **Tên nhóm:** `4aesieunhan`
- **Mã nhóm/Lớp:** `K4-L3B-DAY10`
- **Repository:** `K4-L3B-DAY10-4aesieunhan-DataPipelineDataObservability`
- **Link:** https://github.com/TuTu99999/K4-L3B-DAY10-4aesieunhan-DataPipelineDataObservability

## Thành viên

| STT | Họ và tên | MSSV | Email Git | Vai trò và phạm vi chính | Báo cáo cá nhân |
| --: | --- | --- | --- | --- | --- |
| 1 | Phạm Khắc Tú | 2A202602866 | `canhquat213@gmail.com` | Ingestion, benchmark, baseline integration và kiểm tra tích hợp cuối | `report/2A202602866_PhamKhacTu.md` |
| 2 | Trần Tuấn Hoàng | 2A202602832 | `tranhoangtth123@gmail.com` | Cleaning, data modeling, Great Expectations và freshness | `report/2A202602832-TranTuanHoang.md` |
| 3 | Thân Thị Kim Chi | 2A202602797 | `kimchi19082004@gmail.com` | Corruption suite, repair, Phase 2 integration và comparison reporting | `report/2A202602797-ThanThiKimChi.md` |

## Phân công theo deliverable

| Deliverable | Owner chính | Input | Output bàn giao | Cách xác minh |
| --- | --- | --- | --- | --- |
| Bước 2 — Raw ingestion và lineage | Phạm Khắc Tú | Crossref API hoặc raw snapshot | `data/raw/crossref_response.json`, `crossref_records.json` | Lệnh nghiệm thu Bước 2 trả 24 records |
| Bước 3 — Cleaning và pre-embed modeling | Trần Tuấn Hoàng | Danh sách `PaperRecord` | `data/clean/papers_clean.csv`, `papers_clean.json` | Lệnh nghiệm thu Bước 3 trả 24 dòng |
| Bước 4 — Quality gate và freshness | Trần Tuấn Hoàng | Clean DataFrame | `data/quality/baseline_quality_report.json`, `freshness_report.json` | Quality status `True`, stale ratio `0.0417` |
| Bước 5 — Benchmark test set | Phạm Khắc Tú | Clean DataFrame | `data/eval/test_set.json` | Sinh đúng 10 câu thuộc 4 loại |
| Bước 6 — Baseline pipeline | Phạm Khắc Tú | Các module Phase 1 | Baseline index, answers, metrics và report | `python script/run_phase1.py` exit code 0 |
| Bước 7 — Data corruption suite | Thân Thị Kim Chi | Clean DataFrame | Corrupted dataset và `corruption_log.json` | Đủ 6 loại lỗi, kết quả 22 dòng |
| Bước 8 — Repair và three-state comparison | Thân Thị Kim Chi | Baseline, corrupted data và raw snapshot | Repaired dataset, metrics và `corruption_report.md` | `python script/run_corruption_flow.py` exit code 0 |
| QA/LLM evaluation và kiểm tra cuối | Phạm Khắc Tú | Ba Chroma index và test set cố định | 30 LLM answers, LLM judge results, báo cáo cá nhân/nhóm | `answer_source=llm`, không có heuristic fallback |

## Tự khai đóng góp

| Thành viên | Tỷ lệ đóng góp | Nội dung đóng góp chính | Commit tiêu biểu trên `main` |
| --- | ---: | --- | --- |
| Phạm Khắc Tú | 34% | Ingestion, test set, baseline pipeline/report; tích hợp 9Router cho QA và judge; rà soát và hoàn thiện hồ sơ nộp | `d8b192c`, `e340ec8` |
| Trần Tuấn Hoàng | 33% | Cleaning, `text_for_embedding`, `age_days`, GX 1.x quality gate và freshness SLA | `1dc784d` |
| Thân Thị Kim Chi | 33% | Sáu corruption scenarios, idempotent repair, Phase 2 pipeline và báo cáo ba trạng thái | `c9e045c`, `d943d42` |
| **Tổng** | **100%** |  |  |

## Tự khai chi tiết từng thành viên

### Phạm Khắc Tú — 2A202602866

- Hoàn thiện `src/ingestion/crossref.py`, bảo toàn raw artifacts và offline fallback.
- Hoàn thiện `src/evaluation/testset.py`, tạo 10 câu hỏi benchmark có DOI ground truth.
- Hoàn thiện `src/pipelines/phase1.py` và baseline reporting.
- Tích hợp custom LLM/9Router vào QA và judge, bổ sung provenance `answer_source`.
- Chạy kiểm tra end-to-end, cập nhật báo cáo cá nhân và báo cáo nhóm theo artifact thực tế.

### Trần Tuấn Hoàng — 2A202602832

- Hoàn thiện `build_clean_dataframe()` để chuẩn hóa dữ liệu, tính `age_days`, deduplicate và dựng `text_for_embedding`.
- Hoàn thiện Great Expectations 1.x ephemeral context với các expectation bắt buộc.
- Hoàn thiện freshness SLA và các quality/freshness artifacts.
- Xác minh baseline clean 24 dòng, quality gate PASS và freshness PASS.

### Thân Thị Kim Chi — 2A202602797

- Hoàn thiện `corrupt_clean_dataframe()` với đủ sáu loại sự cố và audit log chi tiết.
- Hoàn thiện `repair_from_raw_snapshot()` và `run_corruption_flow_pipeline()`.
- Tạo các collection/index corrupted và repaired, đánh giá lại trên cùng test set.
- Xuất báo cáo so sánh Baseline–Corrupted–Repaired và chứng minh khả năng phục hồi.

## Trạng thái nghiệm thu chung

- [x] Cả ba thành viên có commit trực tiếp được merge vào `main`.
- [x] Phase 1 và Phase 2 chạy thành công.
- [x] Baseline và repaired quality/freshness PASS; corrupted FAIL đúng thiết kế.
- [x] Báo cáo nhóm và ba báo cáo cá nhân tồn tại.
- [x] `.env`, API key và ChromaDB runtime không được commit.
