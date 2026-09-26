# Phase 1 Baseline Pipeline Report

## 1. Nguồn Dữ Liệu & Ingestion Summary
- **Source API:** Crossref REST API
- **Tổng số bản ghi thô (Raw Records):** 24
- **Số bản ghi sạch (Cleaned Records):** 24
- **ChromaDB Collection:** `papers-baseline`
- **Mô hình Embedding:** `sentence-transformers/all-MiniLM-L6-v2`

## 2. Kết Quả Kiểm Định Chất Lượng (Great Expectations 1.x & Freshness SLA)
- **Trạng thái tổng thể Quality Gate:** PASSED (True)
- **GX 1.x Expectations:** PASSED
- **Số lượng Expectation đạt chuẩn:** 8/8
- **Freshness SLA:** FRESH (True)
- **Số bài báo quá hạn (>180 ngày):** 1/24 (4.17%)

## 3. Chỉ Số Đánh Giá Baseline (RAG Evaluation Metrics)
| Chỉ số (Metric) | Giá trị | Mô tả |
|---|:---:|---|
| **Retrieval Hit Rate** | **100.0%** | Tỉ lệ truy vấn tìm đúng bài báo chứa thông tin |
| **Mean Token F1** | **1.0000** | Độ trùng khớp từ ngữ giữa câu trả lời và ground truth |
| **Judge Accuracy** | **100.0%** | Đánh giá tính chính xác về mặt ngữ nghĩa |
| **Mean Judge Score** | **5.00/5.0** | Điểm số trung bình từ giám khảo |
| **Số lượng câu hỏi kiểm thử** | **10** | Bộ câu hỏi Benchmark bao phủ 4 nhóm nghiệp vụ |

## 4. Kết Luận Phase 1
Pipeline Baseline đã chạy thành công qua toàn bộ các bước: Ingestion -> Cleaning -> Quality Gate -> Vector Store Indexing -> Benchmark Evaluation.
Dữ liệu sạch đáp ứng đầy đủ tiêu chuẩn kiểm dịch và sẵn sàng làm mốc đối chứng (Ground Truth Baseline) cho Phase 2.
