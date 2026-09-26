# Data Observability & Corruption Flow: 3-State Comparison Report

> **Mục tiêu:** Kiểm chứng hiện tượng Silent Failure khi dữ liệu bị suy thoái (Data Corruption), năng lực cảnh báo của Data Quality Gate (Great Expectations 1.x & Freshness SLA), và khả năng tự phục hồi bất biến (Idempotent Repair) từ nguồn Raw.

---

## 1. Bảng Đối Chiếu Hiệu Năng 3 Trạng Thái (Performance Benchmarks)

| Chỉ số Đánh Giá | Baseline (Sạch) | Corrupted (Tiêm lỗi) | Repaired (Phục hồi) | Delta (Corrupted vs Baseline) | Đánh Giá Phục Hồi |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Retrieval Hit Rate (@4)** | **100.0%** | **60.0%** | **100.0%** | **-40.0%** | Hoàn toàn khôi phục (100%) |
| **Mean Token F1 Score** | **100.0%** | **85.1%** | **100.0%** | **-14.9%** | Khôi phục tối ưu |
| **Judge Evaluation Accuracy** | **100.0%** | **90.0%** | **100.0%** | **-10.0%** | Khôi phục chuẩn xác |
| **Mean Judge Score (1-5)** | **5.00** | **4.20** | **5.00** | **-0.80** | Đạt mức tối đa |

---

## 2. Đối Chiếu Chốt Kiểm Dịch Chất Lượng (Quality Gate & Freshness SLA)

| Tiêu Chí Observability | Baseline | Corrupted (Lỗi) | Repaired (Sau sửa) | Phân Tích Kỹ Thuật |
| :--- | :---: | :---: | :---: | :--- |
| **GX 1.x Quality Gate** | **PASSED (True)** | **FAILED (False)** | **PASSED (True)** | Quality Gate kích hoạt cảnh báo vi phạm schema, null & duplicate ngay lập tức. |
| **Freshness SLA Status** | **HEALTHY (True)** | **VIOLATION (False)** | **HEALTHY (True)** | Tỷ lệ bài báo quá hạn (> 180 ngày) vượt ngưỡng cho phép 25%. |
| **Số Bản Ghi Bị Stale** | 0 | 9 | 0 | Phục hồi ngày xuất bản chuẩn từ Raw Ingestion. |
| **Tỷ Lệ Stale** | 0.0% | 40.9% | 0.0% | Tỷ lệ stale trở về 0% sau repair. |

---

## 3. Phân Tích 6 Dạng Lỗi Tiêm Vào (Corruption Scenarios)
1. **Drop latest records (20% bản ghi mới bị mất):**
   - *Tác động:* Gây mất thông tin các nghiên cứu mới nhất, dẫn đến Miss khi người dùng truy vấn tài liệu mới (`retrieval_hit` giảm sâu).
2. **Blank summary (Xóa rỗng tóm tắt):**
   - *Tác động:* Khiến câu trả lời tóm tắt bị rỗng hoặc Agent hallucinate do vector embedding mất ngữ nghĩa chính.
3. **Inject noise into summary (Chèn ký tự rác):**
   - *Tác động:* Phá vỡ khoảng cách vector embedding, giảm độ tương đồng cosine khi truy vấn ngữ nghĩa.
4. **Truncate title (< 8 ký tự):**
   - *Tác động:* Phá hỏng cơ chế exact match title và vi phạm expectation `ExpectColumnValueLengthsToBeBetween`.
5. **Stale date (Lùi ngày xuất bản về quá khứ xa):**
   - *Tác động:* Vi phạm Freshness SLA (> 25% bài báo cũ), làm suy giảm độ tin cậy thời gian thực của RAG.
6. **Duplicate rows (Nhân bản dữ liệu):**
   - *Tác động:* Làm sai lệch trọng số vector, gây trùng lặp kết quả truy vấn, vi phạm `ExpectColumnValuesToBeUnique`.

---

## 4. Hiện Tượng Silent Failure & Cơ Chế Tự Phục Hồi (Idempotent Repair)
- **Silent Failure là gì?** Hệ thống RAG thông thường không hề quăng exception hay dừng chương trình khi dữ liệu bị lỗi. Thay vào đó, API vẫn trả HTTP 200, nhưng độ chính xác (Hit Rate và F1) âm thầm tụt giảm nghiêm trọng từ **100.0% xuống 60.0%**.
- **Vai trò của Data Observability:** Chốt kiểm dịch Great Expectations 1.x và Freshness Check chặn đứng luồng dữ liệu bẩn trước khi phục vụ người dùng.
- **Tính Bất Biến (Idempotency) của Repair:** Pipeline khôi phục dữ liệu từ bản sao lưu thô bất biến `data/raw/crossref_records.json`, tái tạo hoàn toàn DataFrame sạch, xóa và nạp lại ChromaDB collection. Dù chạy bao nhiêu lần, kết quả đầu ra luôn nhất quán 100% với trạng thái Baseline chuẩn.
