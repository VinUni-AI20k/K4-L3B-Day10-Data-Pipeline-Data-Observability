# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Hà Thị Mỹ Linh             |
| MSSV               | 2A202602619                     |
| Khóa/Lớp         | K4 - Lớp B              |
| Tên nhóm         | Enigma     |
| Vai trò chính    | Data Observability, Corruption Suite & Reporting (`quality.py`, `corruption.py`, `reporting.py`) |
| Repository         | https://github.com/hungdq1306/K4-L3B-Day10-Enigma-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Great Expectations 1.x Quality Gate | `src/observability/quality.py` | Cleaned dataframe 24 dòng | `data/quality/baseline_quality_report.json` | Đang thực hiện |
| Freshness SLA Monitoring | `src/observability/quality.py` | Dataframe age_days | `data/quality/freshness_report.json` | Đang thực hiện |
| Synthetic Corruption Suite | `src/ingestion/corruption.py` | Cleaned dataframe | `data/results/corruption_log.json`, corrupted data | Đang thực hiện |
| 3-State Markdown Report | `src/observability/reporting.py` | Baseline, Corrupted, Repaired metrics | `data/reports/corruption_report.md` | Đang thực hiện |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Kiểm tra Freshness logic | Đặng Quang Hưng (`cleaning.py`) | Đảm bảo tính toán `age_days` chuẩn theo ngày chạy |
| Tích hợp kết quả đánh giá | Nguyễn Anh Tuấn (`corruption_flow.py`) | Định dạng bảng so sánh 3 trạng thái rõ ràng |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Xây dựng GX 1.x Quality Gate | `src/observability/quality.py` | 4 expectations chuẩn hóa | `quality check status = True` |
| Triển khai 6 kịch bản tiêm lỗi | `src/ingestion/corruption.py` | Ghi log đầy đủ 6 dạng lỗi | `corruption_log.json` |
| Sinh báo cáo đối chiếu 3 trạng thái | `src/observability/reporting.py` | `corruption_report.md` | Kiểm tra file markdown sinh ra |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Phát hiện sớm sự cố chất lượng dữ liệu và kiểm soát độ tươi (Freshness) trước khi đưa vào kho vector, tránh hiện tượng Silent Failure làm suy thoái mô hình AI trong sản xuất.

### Cách xác minh
```bash
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Tín hiệu hoàn thành: Quality check status = {res[\"success\"]}')"
```

## 5. Quyết định kỹ thuật & Điều học được
Áp dụng Great Expectations 1.x với cú pháp `ephemeral context` mới nhất, tách biệt rõ ràng giữa Data Quality Gate và Freshness SLA để theo dõi hai khía cạnh độc lập của dữ liệu.

## 6. Cam kết của thành viên
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** Hà Thị Mỹ Linh  
**Ngày xác nhận:** 2026-09-26
