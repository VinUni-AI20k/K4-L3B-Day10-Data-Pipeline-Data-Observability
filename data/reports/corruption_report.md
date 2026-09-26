# Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired

> **Mục tiêu:** Đo lường tác động của lỗi dữ liệu (Data Corruption) lên hệ thống RAG Agent (hiện tượng Silent Failure), hiệu quả của chốt kiểm dịch Data Observability (Great Expectations 1.x & Freshness SLA), và năng lực tự phục hồi an toàn (Idempotent Repair).

## 1. Bảng So Sánh Hiệu Năng & Đo Lường Suy Giảm (Silent Failure)

| Tiêu chí / Chỉ số đánh giá | 1. Baseline (Sạch) | 2. Corrupted (Bị Tiêm Lỗi) | 3. Repaired (Sau Phục Hồi) | Mức độ thay đổi & Phục hồi |
|---|:---:|:---:|:---:|:---:|
| **Retrieval Hit Rate** | **100.0%** | **60.0%** | **100.0%** | Giảm 40.0% ➔ Phục hồi +40.0% |
| **Mean Token F1** | **1.0000** | **0.5000** | **1.0000** | Giảm 0.5000 ➔ Phục hồi +0.5000 |
| **Judge Accuracy** | 100.0% | 50.0% | 100.0% | Sụt giảm trong pha lỗi ➔ Hồi phục 100% |
| **Mean Judge Score (1-5)** | 5.00 | 3.00 | 5.00 | Suy giảm chất lượng ngữ nghĩa ➔ Phục hồi hoàn toàn |
| **Great Expectations 1.x** | **PASSED (True)** | **FAILED (False)** | **PASSED (True)** | Bắt trúng vi phạm schema/uniqueness/length |
| **Freshness SLA (>180 ngày)** | **FRESH (True)** | **STALE (False)** | **FRESH (True)** | Bắt trúng dữ liệu cũ quá hạn |

## 2. Phân Tích Hiện Tượng Silent Failure
- **Bản chất sự cố:** Khi 6 kịch bản lỗi (Drop 20% bài mới, Blank summary, Inject noise, Truncate title, Stale date, Duplicate rows) được tiêm vào dữ liệu, hệ thống Agent và Vector Database **không hề crash hoặc ném ra exception**.
- **Hậu quả định lượng:** Tỷ lệ truy vấn đúng bài báo (Hit Rate) sụt giảm từ **100.0%** xuống **60.0%** (mất 40.0%), và Token F1 giảm từ **1.0000** xuống **0.5000**. Người dùng vẫn nhận được câu trả lời từ AI nhưng câu trả lời bị sai lệch hoặc thiếu thông tin mà không có cảnh báo hệ thống.
- **Vai trò của Observability Gate:** Nhờ các Expectations (độ dài title, tính duy nhất paper_id, tỷ lệ null) và Freshness SLA, hệ thống phát hiện và chặn đứng dữ liệu bẩn trước khi phục vụ người dùng.

## 3. Cơ Chế Tự Phục Hồi Idempotent Repair
- **Nguyên lý:** Nhờ chính sách bảo toàn bản gốc (Raw Snapshot Preservation) tại `data/raw/crossref_records.json`, hệ thống có thể tái lập trạng thái sạch ban đầu hoàn toàn offline mà không phụ thuộc vào API ngoài hay dữ liệu hỏng.
- **Tính Idempotent:** Chạy pipeline sửa chữa nhiều lần vẫn cho ra cùng một kết quả nhất quán (Deterministic).
- **Kết quả phục hồi:** Sau khi kích hoạt Repair, Retrieval Hit Rate đạt **100.0%** và Token F1 đạt **1.0000**, phục hồi trọn vẹn 100% so với trạng thái Baseline.
