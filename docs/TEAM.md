# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên nhóm:** Buddy
- **Mã lớp / Bài lab:** `K4-L3B-DAY10`
- **Repository nộp bài:** `K4-L3B-DAY10-Buddy-DataPipelineDataObservability`
- **Kế hoạch chi tiết:** [PHAN_CONG_NHOM.md](PHAN_CONG_NHOM.md)

## 1. Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò | Báo cáo cá nhân dự kiến |
|---:|---|---|---|---|---|
| 1 | Nguyễn Đình Thái | 2A202602718 | nguyendinhthai943@gmail.com | Trưởng nhóm · Pipeline & RAG | `report/<MSSV>_NguyenDinhThai.md` |
| 2 | Vũ Tiến Linh | 2A202602657 | vutienlinh95@gmail.com | Data Foundation & Recovery | `report/<MSSV>_VuTienLinh.md` |
| 3 | Dương Đình Long | 2A202602474 | dinhlongrmx@gmail.com | Observability & Evaluation | `report/<MSSV>_DuongDinhLong.md` |

## 2. Phạm vi phụ trách và sản phẩm bàn giao

### Nguyễn Đình Thái — Trưởng nhóm · Pipeline & RAG

- **Module:** `src/core/`, `src/pipelines/`, `src/retrieval/`, `script/`.
- **Môi trường và cấu hình:** phụ trách `pyproject.toml`, `.env.example`, `src/core/config.py`, `src/core/utils.py`; xác minh cài đặt, đường dẫn và provider, bổ sung alias `google` → `gemini` theo kế hoạch.
- **RAG:** kiểm chứng `src/retrieval/embeddings.py`, `index.py`, `qa.py`, `llm.py`, `agent.py`; dùng MiniLM, quản lý 3 collection riêng biệt và xác minh QA/Agent.
- **Pipeline:** hoàn thiện `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`; kiểm chứng `script/run_phase1.py`, `script/run_corruption_flow.py`.
- **Tài liệu và điều phối:** cập nhật `README.md`, `docs/TEAM.md`; điều phối merge cuối mỗi checkpoint, chạy tích hợp, sinh bộ artifacts nộp bài và dẫn demo.
- **Đầu vào nhận:** raw/clean/corrupted data và các hàm của Linh; Quality Gate, benchmark và hàm báo cáo của Long.
- **Bàn giao:** hai entrypoint chạy thành công, 3 collection độc lập, đầy đủ artifacts Baseline–Corrupted–Repaired và hướng dẫn chạy lại.

### Vũ Tiến Linh — Data Foundation & Recovery

- **Module:** `src/ingestion/`.
- **`src/ingestion/crossref.py`:** hoàn thiện `parse_crossref_payload()`, `fetch_source_records()`, `load_raw_records()`; hỗ trợ retry/fallback offline, lưu đủ raw response và raw records, giữ `paper_id` ổn định.
- **`src/ingestion/cleaning.py`:** hoàn thiện `build_clean_dataframe()`; làm sạch JATS/XML, chuẩn hóa trường dữ liệu, khử trùng lặp, tính `age_days` và các cột phụ, tạo `text_for_embedding` đủ 5 phần.
- **`src/ingestion/corruption.py`:** hoàn thiện `corrupt_clean_dataframe()` với 6 lỗi: mất bản ghi mới, blank summary, noise, title ngắn, stale date, duplicate rows; cập nhật lại cột phụ và embedding text, xuất log.
- **Repair:** bảo đảm `load_raw_records()` → `build_clean_dataframe()` phục hồi từ raw; Thái tích hợp chuỗi này vào pipeline. Linh kiểm tra idempotent với cùng raw và `run_date`.
- **Bàn giao:** 2 raw JSON, dataframe sạch, dataframe lỗi, corruption log và bằng chứng phục hồi; không sửa baseline/raw khi tạo dữ liệu lỗi.

### Dương Đình Long — Observability & Evaluation

- **Module:** `src/observability/`, `src/evaluation/`.
- **`src/observability/quality.py`:** hoàn thiện `run_data_quality_checks()` bằng GX 1.x với kiểm tra số dòng, not-null, uniqueness và độ dài chuỗi; hoàn thiện `build_freshness_report()` với ngưỡng stale `age_days > 180`, vi phạm SLA khi tỷ lệ vượt 25%.
- **`src/evaluation/testset.py`:** hoàn thiện `build_test_set()` tạo 10 câu thuộc `summary`, `authors`, `date`, `categories`; ground truth lấy từ baseline và dùng chung cho cả 3 trạng thái.
- **`src/evaluation/metrics.py`:** kiểm chứng `evaluate_pipeline()`, metrics và answers; phân biệt LLM judge với fallback heuristic.
- **`src/observability/reporting.py`:** hoàn thiện `generate_phase1_report()`, `generate_corruption_report()` từ số liệu thực tế.
- **`report/group_report.md`:** tổng hợp đóng góp, kết quả, bằng chứng và hạn chế của nhóm.
- **Đầu vào nhận:** schema/raw ở CP0, clean ở CP1, baseline ở CP3, corrupted/repaired ở CP4–CP5.
- **Bàn giao:** benchmark cố định, Quality Gate, quality/freshness reports, hàm sinh báo cáo và báo cáo nhóm khớp artifacts.

## 3. Phân công theo checkpoint và thời điểm phối hợp

Mốc thời gian tính từ lúc bắt đầu bài lab; dành khoảng 5 phút cuối mỗi checkpoint để bàn giao và kiểm tra.

| Mốc | Nguyễn Đình Thái | Vũ Tiến Linh | Dương Đình Long | Phối hợp / Bàn giao |
|---|---|---|---|---|
| **CP0 · 0–30 phút** | Môi trường, cấu hình | Raw ingestion và 2 JSON | Chuẩn bị quality, schema benchmark | Phút 0–10 chốt giao diện; phút 25–30 Linh bàn giao raw cho Thái và Long. |
| **CP1 · 30–65 phút** | Chuẩn bị index, orchestration | Cleaning | GX và freshness | Khoảng phút 45 Linh đưa dataframe mẫu; phút 60–65 cả nhóm kiểm tra schema, 24 dòng chuẩn và quality/freshness. |
| **CP2 · 65–95 phút** | Index và QA | Kiểm chứng clean, chuẩn bị corruption | Benchmark 10 câu | Phút 90–95 ghép clean → index → benchmark → QA; cố định raw, benchmark và cấu hình so sánh. |
| **CP3 · 95–120 phút** | Chạy baseline | Sửa lỗi dữ liệu nếu có | Metrics và báo cáo baseline | Phút 115–120 kiểm tra baseline hoàn chỉnh trước khi đo corruption. |
| **CP4 · 120–165 phút** | Tích hợp index/evaluation corrupted | Hoàn thiện 6 lỗi và log | Kiểm định dữ liệu lỗi | Khoảng phút 140 bàn giao dữ liệu lỗi; phút 160–165 kiểm tra log, quality và metrics thực tế. |
| **CP5 · 165–210 phút** | Tích hợp repair | Đối chiếu raw/clean/repaired | Báo cáo 3 trạng thái | Khoảng phút 185 chạy repair; phút 200–210 chạy lại kiểm tra idempotent và chốt artifacts. |
| **CP6 · 210–240 phút** | Dẫn demo, rà soát bài nộp | Trình bày corruption/repair, báo cáo cá nhân | Trình bày quality/metrics, báo cáo nhóm và cá nhân | Demo thử chung, kiểm tra hồ sơ và commit của cả 3 người. |

## 4. Quy tắc phối hợp và nghiệm thu

- Mỗi file có một người phụ trách chính; lỗi module nào do người phụ trách module đó sửa. Thống nhất trước khi hỗ trợ sửa file của nhau.
- Làm việc trên các nhánh `feat/thai-pipeline-rag`, `feat/linh-data`, `feat/long-observability`; Thái điều phối merge cuối checkpoint và giữ tác giả commit.
- Giữ chữ ký hàm, schema, `paper_id` và đường dẫn trong `Settings.paths` theo kế hoạch. Thay đổi giao diện phải báo cho người gọi trước khi merge.
- Baseline và repair dùng cùng raw và `run_date`; cả 3 trạng thái dùng cùng benchmark. Quality/freshness reports lưu riêng theo trạng thái.
- Baseline và repaired được kiểm định trước khi index. Nhánh thí nghiệm corrupted ghi nhận kiểm định thất bại nhưng tiếp tục đo tác động theo kế hoạch.
- Giữ nguyên cảnh báo freshness nếu snapshot thực sự quá hạn; không sửa ngày hoặc ngưỡng để ép pass.
- Thái sinh bộ artifacts tích hợp; tránh nhiều người đồng thời commit lại cùng metrics, báo cáo tự sinh hoặc ChromaDB.
- Nghiệm thu hai lệnh `python script/run_phase1.py` và `python script/run_corruption_flow.py`; kiểm tra đủ artifacts, 6 dạng lỗi, 3 bộ metrics, 3 collection, báo cáo so sánh và tính idempotent.
- Các kết luận phải dựa trên số liệu thực tế. Kiểm chứng QA và Agent riêng; ghi rõ provider đã thử và hạn chế còn lại.

Chi tiết giao diện, tiêu chí bàn giao từng file và kịch bản kiểm tra nằm trong [PHAN_CONG_NHOM.md](PHAN_CONG_NHOM.md).

## 5. Tự khai đóng góp cá nhân

Mỗi người tự bổ sung sau khi thực hiện, phân biệt phần hoàn thành, thử nghiệm và chưa hoàn thành. Không dùng phân công dự kiến để thay thế bằng chứng đóng góp.

### Nguyễn Đình Thái — 2A202602718

- **Vai trò:** Trưởng nhóm · Pipeline & RAG.
- **Công việc chi tiết đã hoàn thành:** [Tự bổ sung theo thực tế]
- **Checkpoint đã đóng góp:** [Tự bổ sung]
- **Bằng chứng — commit / log / artifact:** [Tự bổ sung]
- **Phần thử nghiệm / Chưa hoàn thành / Blocker:** [Tự bổ sung]
- **Điều học được / Đóng góp chính:** [Tự bổ sung]
- **Báo cáo cá nhân:** `report/2A202602718_NguyenDinhThai.md`.

### Vũ Tiến Linh — 2A202602657

- **Vai trò:** Data Foundation & Recovery.
- **Công việc chi tiết đã hoàn thành:** [Tự bổ sung theo thực tế]
- **Checkpoint đã đóng góp:** [Tự bổ sung]
- **Bằng chứng — commit / log / artifact:** [Tự bổ sung]
- **Phần thử nghiệm / Chưa hoàn thành / Blocker:** [Tự bổ sung]
- **Điều học được / Đóng góp chính:** [Tự bổ sung]
- **Báo cáo cá nhân:** `report/2A202602657_VuTienLinh.md`.

### Dương Đình Long — 2A202602474

- **Vai trò:** Observability & Evaluation.
- **Công việc chi tiết đã hoàn thành:** [Tự bổ sung theo thực tế]
- **Checkpoint đã đóng góp:** [Tự bổ sung]
- **Bằng chứng — commit / log / artifact:** [Tự bổ sung]
- **Phần thử nghiệm / Chưa hoàn thành / Blocker:** [Tự bổ sung]
- **Điều học được / Đóng góp chính:** [Tự bổ sung]
- **Báo cáo cá nhân:** `report/2A202602474_DuongDinhLong.md`.

## 6. Checklist hồ sơ và nộp bài

- [ ] Bổ sung MSSV, email và phần tự khai thực tế của cả 3 thành viên.
- [ ] Mỗi người hoàn thành báo cáo cá nhân; Long tổng hợp `report/group_report.md`.
- [ ] Hai entrypoint chạy thành công; báo cáo khớp artifacts thực tế.
- [ ] Cả 3 thành viên có commit trên `main`; kiểm tra GitHub Insights → Contributors.
- [ ] Không commit `.env`, API key hoặc token.
- [ ] Mỗi người tự nộp link repo lên VLearn LMS trước **23:59:59 ngày 26/09/2026 (GMT+7)**.

Ưu tiên hoàn thành phần bắt buộc; chưa phân công bonus.
