# Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired

## 1. Bảng So Sánh Hiệu Năng & Đo Lường Suy Giảm (Silent Failure)

| Tiêu chí / Chỉ số đánh giá | 1. Baseline (Sạch) | 2. Corrupted (Bị Tiêm Lỗi) | 3. Repaired (Sau Phục Hồi) | Mức độ thay đổi |
|---|:---:|:---:|:---:|:---:|
| **Retrieval Hit Rate** | **100.0%** | **60.0%** | **100.0%** | Giảm 40.0% ➔ Phục hồi 100.0% |
| **Mean Token F1** | **1.0000** | **0.5000** | **1.0000** | Giảm 0.5000 ➔ Phục hồi 1.0000 |
| **Judge Accuracy** | 100.0% | 50.0% | 100.0% | Sụt giảm trong pha lỗi ➔ Hồi sinh |
| **Mean Judge Score (1-5)** | 5.00 | 3.00 | 5.00 | Chất lượng ngữ nghĩa hồi phục |
| **Great Expectations 1.x** | **PASSED (True)** | **FAILED (False)** | **PASSED (True)** | Chốt kiểm dịch bắt lỗi thành công |
| **Freshness SLA (>180 ngày)** | **FRESH (True)** | **STALE (False)** | **FRESH (True)** | Cảnh báo vi phạm SLA chính xác |

## 2. Phân Tích Hiện Tượng Silent Failure
- **Bản chất sự cố:** Khi 6 kịch bản lỗi (Drop latest records, Blank summary, Inject noise, Truncate title, Stale date, Duplicate rows) được tiêm vào dữ liệu, hệ thống Agent và Vector Database **không hề crash hoặc ném ra exception**.
- **Hậu quả định lượng:** Tỷ lệ truy vấn đúng bài báo (Hit Rate) sụt giảm từ **100.0%** xuống **60.0%**, và Token F1 giảm từ **1.0000** xuống **0.5000**. Điều này chứng minh nguy cơ nghiêm trọng của việc không có Data Observability Gate.

## 3. Cơ Chế Tự Phục Hồi Idempotent Repair
- **Nguyên lý:** Nhờ chính sách bảo toàn bản gốc (Raw Preservation) tại `data/raw/crossref_records.json`, hệ thống có thể tái lập trạng thái sạch ban đầu hoàn toàn offline mà không phụ thuộc vào API ngoài hay dữ liệu hỏng.
- **Kết quả:** Sau khi kích hoạt Repair, Retrieval Hit Rate đạt **100.0%** và Token F1 đạt **1.0000**, ngang bằng với trạng thái Baseline.
