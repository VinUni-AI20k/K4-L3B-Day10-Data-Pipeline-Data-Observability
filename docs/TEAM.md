# Nhóm Trike — K4-L3B-DAY10

Repository: [K4-L3B-DAY10-Trike-DataPipelineDataObservability](https://github.com/hoang9605/K4-L3B-DAY10-Trike-DataPipelineDataObservability)

## Thành viên và phân công đã xác nhận

| MSSV | Thành viên | Phần việc Phase 1 | Báo cáo cá nhân |
| --- | --- | --- | --- |
| 02489 | Hải Hoàng | Làm sạch dữ liệu; tích hợp và chạy baseline pipeline | [02489_HaiHoang.md](../report/02489_HaiHoang.md) |
| 02623 | Tuấn Đạt | Thu thập và lưu raw data Crossref; tạo benchmark test set | [02623_TuanDat.md](../report/02623_TuanDat.md) |
| 02853 | Hoàng Nam | Great Expectations quality gate; kiểm tra độ tươi mới | [02853_HoangNam.md](../report/02853_HoangNam.md) |

## Phạm vi đã có bằng chứng

- **Đạt:** `src/ingestion/crossref.py` chuẩn hóa payload Crossref thành `PaperRecord`, lưu nguyên bytes JSON API khi lấy trực tuyến, ghi danh sách records, và dùng snapshot khi API không khả dụng; `src/evaluation/testset.py` sinh 10 câu hỏi thuộc bốn loại.
- **Hoàng:** `src/ingestion/cleaning.py` chuẩn hóa văn bản/ngày tháng, tính `age_days`, tạo `text_for_embedding`, khử DOI trùng; `src/pipelines/phase1.py` nối các bước ingest, clean, quality gate, Chroma, benchmark và báo cáo.
- **Nam:** `src/observability/quality.py` chạy Great Expectations 1.x bằng Ephemeral Context, kiểm tra sáu expectation của bốn loại yêu cầu và SLA dữ liệu cũ.

Kết quả Phase 1 và giới hạn được ghi trong [báo cáo nhóm](../report/group_report.md). Tính đến 2026-09-26, thư mục artifact có 24 bản ghi sạch, 10 câu hỏi benchmark, Hit Rate 100%, Token F1 0,8 và quality gate đạt. Hai câu hỏi về lĩnh vực không có metadata `subject` trong snapshot hiện dùng; kết quả loại câu hỏi này có Token F1 bằng 0. Không có artifact corruption/repair để ghi nhận là đã hoàn thành.
