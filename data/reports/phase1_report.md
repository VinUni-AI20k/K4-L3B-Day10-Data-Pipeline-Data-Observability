# Báo Cáo Đo Lường Dữ Liệu Pha 1 (Baseline Pipeline Report)

- **Thời điểm sinh báo cáo:** Dữ liệu chuẩn hóa Pha 1
- **Nguồn dữ liệu:** Crossref REST API
- **Tổng số tài liệu nạp:** 24

---

## 1. Kết Quả Data Observability & Quality Gates (Great Expectations 1.x)

| Chỉ số kiểm định | Giá trị thực tế | Trạng thái |
| :--- | :--- | :--- |
| **Tổng số Expectation đánh giá** | 4 | Hoàn tất |
| **Số Expectation đạt chuẩn** | 4 | 100% |
| **Trạng thái Quality Gate (GX 1.x)** | `PASSED` | ✅ Đạt chuẩn |
| **Số bài báo cũ (> 180 ngày)** | 1 / 24 | Tỷ lệ: 4.2% |
| **Trạng thái Freshness SLA** | `FRESH` | ✅ Thỏa SLA |

---

## 2. Kết Quả Benchmark Retrieval & QA Agent

Đánh giá trên bộ câu hỏi chuẩn hóa (10 câu hỏi qua 4 nhóm nghiệp vụ):

| Chỉ số hiệu năng (Metric) | Kết quả Baseline | Diễn giải |
| :--- | :---: | :--- |
| **Retrieval Hit Rate** | **100.0%** | Tỷ lệ tìm đúng tài liệu chứa câu trả lời |
| **Mean Token F1** | **1.000** | Độ trùng khớp ngữ nghĩa từ vựng |
| **LLM Judge Accuracy** | **100.0%** | Độ chính xác câu trả lời theo LLM Judge |
| **Mean Judge Score** | **5.00 / 5.0** | Điểm trung bình chất lượng câu trả lời |

---

## 3. Kết Luận Pha 1
Dữ liệu sạch đáp ứng 100% các tiêu chuẩn kiểm định chất lượng bảng, không có trường null hay trùng lặp. Hệ thống RAG đạt hiệu năng ổn định làm mốc đối chiếu (Baseline) cho các kịch bản thử nghiệm tiếp theo.
