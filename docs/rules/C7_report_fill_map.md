# C7 — Bản đồ điền báo cáo (group_report + individual_report)

> **Owner:** M4 (ráp bản cuối) · **Version:** v1.0
> Nguyên tắc: **mỗi mục một người viết**, số liệu **chỉ chép từ artifact của official run** (C6-§5). Không có artifact → ghi `N/A` + lý do, không ước lượng.

## 1. `report/group_report.md` — ai viết mục nào, lấy số ở đâu

| Mục | Người viết | Nguồn dữ liệu (file → key) |
|---|---|---|
| §1 Thông tin bài nộp + bảng thành viên | M4 | `docs/TEAM.md` |
| §2 Tóm tắt kết quả (150–250 từ) | M4 viết **sau cùng** | `data/reports/corruption_report.md` §1, §4 |
| §3 Sơ đồ luồng | M4 | C6-§1, §2 |
| §3 Bảng "Trách nhiệm từng khối" | Mỗi người điền **đúng hàng của mình**: Ingestion → M1 · Cleaning → M2 · Embedding/index → M4 · Evaluation → M2 · Observability → M3 · Corruption/repair → M1 (corruption) + M4 (repair) · Orchestration → M4 | C1–C6 |
| §4 Cấu hình + lệnh chạy + kết quả tái hiện | M4 | `phase1_report.md` §1 (`source_summary`), `.env.example`, log console official run |
| §5 Nguồn dữ liệu | M1 | `source_summary.fetch_mode/raw_records`, `data/raw/crossref_response.json` → `message.total-results` |
| §5 Raw & clean schema, quy tắc cleaning | M2 | C2-§2; dòng log `[cleaning] input=… dropped_invalid=… dropped_duplicates=… output=…` |
| §6 Evaluation setup | M2 | `data/eval/test_set.json` (đếm theo `question_type`), `source_summary.test_set_sha256`, `top_k`, `llm_provider` |
| §7 Artifact checklist | M4 | `ls data/*` sau official run |
| §7 Baseline metrics + diễn giải | M3 | `data/results/baseline_metrics.json` |
| §8 Quality checks + Freshness | M3 | `data/quality/baseline_quality_report.json` → `checks[]`; `data/quality/freshness_report.json` |
| §9 Bảng corruption scenarios | M1 | `data/results/corruption_log.json` → `scenarios[]` (+ cột "Quality signal kỳ vọng" theo C4-§5, "Tác động thực tế" từ `corrupted_quality_report.json`) |
| §9 Giải thích repair | M4 | C6-§2 bước 6–7, log `[repair] verified=…` |
| §10 Bảng 3 trạng thái + 2 chuỗi nhân quả | M3 | `data/reports/corruption_report.md` §1 (chép nguyên số); `corrupted_answers.json` để dẫn ví dụ câu cụ thể |
| §11 Vấn đề tích hợp | M4 | lịch sử merge/lỗi thực tế |
| §12 Giới hạn & cải thiện | **Mỗi người 1 hàng** thuộc module mình | — |
| §13 Checklist | M4 tick sau khi rà | — |

**Mapping tên metric** (dùng y nguyên trong mọi báo cáo): `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`, `Quality checks passed (p/t)`, `Freshness is_fresh`.
Cột "Thay đổi do corruption" = `Δ Corruption`; "Mức phục hồi" = `Recovery %` — định nghĩa ở C6-§3.

## 2. `report/<MSSV>_HoTen.md` — gợi ý nội dung theo vai trò

| Mục individual | M1 | M2 | M3 | M4 |
|---|---|---|---|---|
| §2 Phần việc sở hữu | `crossref.py` (3 hàm), `corruption.py` | `cleaning.py`, `testset.py` | `quality.py`, `reporting.py` | `phase1.py`, `corruption_flow.py`, official run |
| §4 Input/Output contract | C1 + C5 | C2 + C3 | C4 + C6-§3 | C6-§1,§2 |
| §4 Lệnh xác minh | Nghiệm thu C1-§4, C5-§5 | C2-§6, C3-§6 | C4-§6 | 2 lệnh `script/run_*.py` |
| §5 Quyết định kỹ thuật gợi ý | Snapshot mặc định vs gọi live; chọn dòng corruption không chồng lấn | Định dạng 5 phần `text_for_embedding`; test set tất định + đóng băng | Chọn ngưỡng/regex cho check; tách `freshness_sla` khỏi GX | Repair từ raw thay vì "sửa ngược" corrupted; một `run_date`/run |
| §8 Metrics | **Cùng một bảng số** từ official run (chép từ `corruption_report.md` §1) — phần "Nhận xét cá nhân" tự viết, nhìn từ góc module mình | ← | ← | ← |

Mọi thành viên vẫn phải tự trả lời §7 (luồng end-to-end) bằng lời của mình — không copy giữa các bản.

## 3. `docs/TEAM.md`

Mỗi người tự điền **hàng + mục cá nhân của mình** (họ tên, MSSV, email, công việc đã hoàn thành). Thiếu phần tự khai = −5đ/người.

## Changelog
| Version | Thay đổi | Người duyệt |
|---|---|---|
| v1.0 | Chốt ban đầu | cả nhóm |
