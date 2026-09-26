# Báo Cáo Đối Chiếu 3 Trạng Thái Dữ Liệu: Baseline vs Corrupted vs Repaired

> **Mục tiêu:** Chứng minh hiện tượng suy giảm hiệu năng âm thầm (Silent Failure) khi dữ liệu bị lỗi, năng lực phát hiện sớm của Great Expectations 1.x & Freshness SLA, và khả năng tự phục hồi (Self-healing / Idempotent Repair).

---

## 1. Bảng Đối Chiếu Định Lượng Hiệu Năng

| Tiêu chí đánh giá | (1) Baseline (Sạch) | (2) Corrupted (Tiêm lỗi) | (3) Repaired (Phục hồi) | Nhận xét xu hướng |
| :--- | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | **100.0%** | **60.0%** | **100.0%** | Sụt giảm khi lỗi, phục hồi 100% |
| **Mean Token F1** | **1.000** | **0.497** | **1.000** | Chất lượng văn bản câu trả lời hồi sinh |
| **LLM Judge Accuracy** | **100.0%** | **50.0%** | **100.0%** | Độ chính xác câu trả lời thực tế |
| **Mean Judge Score** | **5.00 / 5.0** | **3.00 / 5.0** | **5.00 / 5.0** | Điểm số đánh giá trung bình |
| **Quality Gate (GX 1.x)** | `PASSED` | `FAILED` | `PASSED` | Báo động đỏ khi có lỗi, xanh khi sạch |
| **Freshness SLA** | `FRESH` | `STALE` | `FRESH` | Cảnh báo trôi dạt dữ liệu cũ |

---

## 2. Phân Tích Hiện Tượng Silent Failure & Cơ Chế Quan Sát Dữ Liệu

1. **Khi dữ liệu bị tiêm lỗi (Corrupted State):**
   - 6 kịch bản lỗi (mất bản ghi mới, rỗng summary, inject noise, cắt ngắn title, lùi ngày, duplicate) làm suy giảm trực tiếp không gian vector.
   - Retrieval Hit Rate giảm mạnh từ **100.0%** xuống **60.0%**, kéo theo Token F1 và Judge Accuracy sụp đổ.
   - Nếu không có Data Observability, ứng dụng AI vẫn trả lời bình thường (không văng lỗi crash) nhưng câu trả lời bị ảo giác / sai lệch (Silent Failure).
   - Bộ chốt kiểm dịch **Great Expectations 1.x** đã chặn đứng dữ liệu bẩn với trạng thái `FAILED`, đồng thời Freshness SLA cảnh báo `STALE`.

2. **Cơ chế Phục Hồi Dữ Liệu An Toàn (Idempotent Repair):**
   - Thay vì sửa chữa chắp vá trên dữ liệu bẩn, pipeline kích hoạt phục hồi dữ liệu từ bản lưu trữ thô bất biến (Immutable raw snapshot `crossref_records.json`).
   - Hàm `build_clean_dataframe` thực thi chuẩn hóa và tái lập chỉ mục ChromaDB (`papers-repaired`).
   - Kết quả: Retrieval Hit Rate và Token F1 phục hồi hoàn toàn về mức **100.0%** và **1.000**, Quality Gate quay lại trạng thái `PASSED`.
