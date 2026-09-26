# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Dương Hữu Đạt             |
| MSSV               | 2A202602544                     |
| Khóa/Lớp         | K4-L3B              |
| Tên nhóm         | sunset     |
| Vai trò chính    | Observability & Evaluation                 |
| Repository         | K4-L3-DAY10-sunset-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Đánh giá chất lượng dữ liệu | `src/observability/quality.py` | Dataframe | Báo cáo Quality / Freshness | Hoàn thành |
| Markdown Reporter | `src/observability/reporting.py` | Metrics | File `phase1_report.md`, `corruption_report.md` | Hoàn thành |
| Auto Testset | `src/evaluation/testset.py` | Dataframe sạch | File `test_set.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Cấu hình ragas | Hỗ trợ Thái (Module RAG) | Tắt chạy RAGAS mặc định để cải thiện tốc độ pipeline |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sinh Markdown Report | `src/observability/reporting.py` | File `data/reports/corruption_report.md` | Xem file markdown |
| Tính độ trễ (Freshness) | `src/observability/quality.py` | File `freshness_report.json` | Mở file json thấy `age_days` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Dữ liệu thô tải về không phải lúc nào cũng đẹp. Việc thiếu sót một số trường quan trọng (như summary, title) sẽ phá vỡ Vector Search. Yêu cầu một hệ thống kiểm tra tự động trước khi nạp vào AI.

### Cách triển khai
Khởi tạo Great Expectations Context dưới dạng Ephemeral (chỉ sống trong RAM). Cấu hình 6 bộ Expectations (Luật). Trả về JSON tổng kết success_percent. Viết hàm format chuỗi JSON đưa vào file markdown tự động để tạo báo cáo trực quan.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Dictionary của các metrics AI và Data Quality           |
| Output                         | Markdown string ghi đè vào file .md |
| Module phụ thuộc             | `core/config.py`                    |
| Điều kiện lỗi cần xử lý | Xử lý lỗi lấy metrics RAGAS nếu RAGAS đang tắt (trả về N/A) |

### Cách xác minh

```bash
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Báo cáo Markdown hiển thị bảng so sánh 3 cột đầy đủ giá trị.
- **Kết quả thực tế:** Hiển thị 0.5 cho hit_rate ở cột Corrupted và 1.0 ở cột Repaired.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lỗi khi lấy chỉ số từ RAGAS hiển thị N/A ở bảng báo cáo do chưa xử lý key lồng nhau.
- **Phương án đã chọn:** Khai báo biến `rb = baseline_metrics.get("ragas", {})` sau đó `.get()` an toàn trên biến tạm này thay vì gọi cứng vào key dict.
- **Lý do:** Chống văng lỗi `KeyError` hoặc `TypeError` khiến toàn bộ chuỗi Pipeline bị gãy chỉ vì không chấm được điểm.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Markdown table báo cáo hiện toàn N/A cho cả các chỉ số căn bản của LLM Judge.
- **Nguyên nhân gốc:** Không gọi đúng tên biến ngoài level root của dict.
- **Cách xử lý:** Đổi key gọi dict và thêm `.get(..., 'N/A')` để đảm bảo fallback.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu tải từ HTTP API -> Clean bằng Pandas -> Lưu CSV -> Băm Vector bằng SentenceTransformers -> Lưu xuống ChromaDB.
2. Ground-truth doc IDs dùng để match ID tài liệu mà bot AI trả về. Nếu tìm thấy thì được 1 điểm (Hit), không thấy thì 0 điểm.
3. Quality Check check cấu trúc (null, regex, length). Freshness check check Logic về mặt thời gian hiện hành.
4. Dùng cùng Test Set để đảm bảo tính công bằng (cố định hằng số) nhằm đánh giá đúng sự tụt hậu của AI do tác động của dữ liệu đầu vào.
5. Repair thành công khi Quality status đạt tỷ lệ cao nhất và Agent Metric (hit_rate) quay lại 1.0.

## 8. Phân tích kết quả

(Giống với trưởng nhóm, đã chứng minh việc chạy lệnh cho ra kết quả giảm số expectation thành công khi dữ liệu bị phá)

## 9. Điều học được và hướng cải thiện

1. Great Expectations là một công cụ mạnh mẽ dành cho Data Engineer.
2. File Markdown có thể tự gen tự động 100% bằng code Python mà không cần viết tay.
3. AI Evaluation rất nhạy cảm với chất lượng của dữ liệu vector.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Dương Hữu Đạt
**Ngày xác nhận:** 2026-09-26
