# Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired
**Dự án:** K4-L3B-Day10 — Data Pipeline & Data Observability for RAG  
**Nhóm:** Team VN | **Thời gian phân tích:** 2026-09-26 04:23:50 UTC  
**Mục tiêu:** Định lượng hiện tượng **Silent Failure**, chứng minh hiệu lực của Data Observability và kiểm chứng năng lực **Idempotent Self-Healing**.

---

## 1. Bảng Đối Chiếu Định Lượng 3 Trạng Thái

| Metric / Tín hiệu kiểm định | Baseline | Corrupted | Repaired | Thay đổi do Corruption | Mức phục hồi sau Repair | Đánh giá & Phân tích nhân quả |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | **100.00%** | **80.00%** | **100.00%** | `-20.00%` | **100% phục hồi** | Sụt giảm do bị drop 20% bài báo mới nhất và chèn noise làm lệch không gian vector cosine |
| **Mean Token F1** | **1.0000** | **0.6000** | **1.0000** | `-0.4000` | **100% phục hồi** | Sụt giảm nghiêm trọng do summary bị xóa trắng hoặc bị chèn chuỗi ký tự rác |
| **Judge Accuracy** | **100.00%** | **60.00%** | **100.00%** | `-40.00%` | **100% phục hồi** | LLM Judge phát hiện câu trả lời hallucinate / thiếu căn cứ khi context bị hỏng |
| **Mean Judge Score** | **5.00 / 5.0** | **3.40 / 5.0** | **5.00 / 5.0** | `-1.60` | **5.00 / 5.0** | Phản ánh trực quan chất lượng câu trả lời suy giảm rõ rệt và hồi phục nguyên trạng |
| **GX Quality Gate** | **PASS** | **FAIL** | **PASS** | `PASS -> FAIL` | **PASS (100%)** | GX bắt chính xác lỗi vi phạm null title/summary, title ngắn < 8 ký tự, duplicate paper_id |
| **Freshness SLA** | **FRESH** | **STALE** | **FRESH** | `FRESH -> STALE` | **FRESH (100%)** | Bắt chính xác lỗi lùi ngày xuất bản > 730 ngày, khiến tỷ lệ stale vượt trần 25% |

---

## 2. Chi tiết 6 Kịch bản Data Corruption Đã Tiêm

Hệ thống đã thực hiện tiêm 6 lỗi dữ liệu theo đúng chuẩn thực tế:
1. **Drop latest records (20%):** Loại bỏ 5 bài báo khoa học mới nhất khỏi corpus -> Trực tiếp làm mất ground-truth context, gây trượt Retrieval Hit Rate đối với các câu hỏi về bài báo mới.
2. **Blank summary (20%):** Xóa rỗng trường tóm tắt (`summary = ""`) -> Khiến câu trả lời cho câu hỏi dạng `summary` bị rỗng hoặc hallucinate, giảm Token F1.
3. **Inject noise (20%):** Chèn tiền tố rác `[CORRUPTED] zxqv987 ### @@@ invalid_payload !!!.` vào đầu tóm tắt -> Làm loãng mật độ từ khóa ngữ nghĩa và phá vỡ embedding vector.
4. **Truncate title (20%):** Cắt ngắn tiêu đề xuống dưới 8 ký tự -> Kích hoạt cảnh báo vi phạm của Great Expectations (`ExpectColumnValueLengthsToBeBetween`).
5. **Stale date (40%):** Lùi ngày xuất bản thêm 730 ngày -> Đẩy số ngày tuổi `age_days` vượt xa 180 ngày, kích hoạt cảnh báo vi phạm Freshness SLA.
6. **Duplicate rows (10%):** Nhân bản các bản ghi có cùng `paper_id` -> Kích hoạt cảnh báo trùng lặp khóa chính của Great Expectations (`ExpectColumnValuesToBeUnique`).

Toàn bộ chi tiết từng bản ghi bị tác động được kiểm toán tại `data/results/corruption_log.json`.

---

## 3. Phân tích Hiện tượng Silent Failure trong RAG

- **Silent Failure là gì?** Khi dữ liệu bị lỗi (tóm tắt rỗng, tiêu đề cắt ngắn, dữ liệu nhiễu), hệ thống Vector Database và RAG Agent **vẫn hoạt động bình thường, không văng ra Exception hay Crash tiến trình**. Tuy nhiên, câu trả lời sinh ra cho người dùng bị sai lệch hoàn toàn, bịa đặt (hallucination) hoặc trả lời không đúng trọng tâm.
- **Vai trò của Data Observability:** Nếu không có **Great Expectations 1.x** và **Freshness SLA** làm trạm kiểm soát chất lượng (Quality Gate), hệ thống sẽ âm thầm phục vụ dữ liệu độc hại cho người dùng cuối mà đội ngũ vận hành không hề hay biết.

---

## 4. Cơ chế Tự Phục Hồi Idempotent (Self-Healing / Repair)

- **Nguyên tắc Idempotent:** Quy trình phục hồi `Idempotent Repair` cam kết rằng khi chạy lại quy trình từ nguồn lưu trữ thô bất biến (`data/raw/crossref_records.json`), hệ thống luôn trả về đúng một trạng thái dữ liệu sạch duy nhất, không phụ thuộc vào số lần thực thi hay trạng thái hư hại trước đó.
- **Không dùng phương pháp chắp vá (Patching):** Tuyệt đối không phục hồi bằng cách "sửa đè" các dòng lỗi trên DataFrame bẩn, vì phương pháp này vi phạm Data Lineage và dễ bỏ sót các lỗi tiềm ẩn.
- **Quy trình chuẩn:**
  1. Đọc lại raw snapshot nguyên bản từ nguồn tin cậy (`crossref_records.json`).
  2. Tái thực thi toàn bộ logic làm sạch tiêu chuẩn qua `build_clean_dataframe()`.
  3. Tái xây dựng Vector Index ChromaDB sạch (`papers-repaired`).
  4. Xác thực lại bằng Great Expectations 1.x và Freshness SLA: Đảm bảo Quality Gate chuyển từ **FAIL** trở lại **PASS**.
  5. Đánh giá lại trên cùng một bộ Benchmark cố định: Đảm bảo các chỉ số phục hồi 100% về mức Baseline ban đầu.

---

## 5. Phân tích Quan hệ Nhân quả (Causality Analysis)

Dựa trên các artifact đo lường thực tế, nhóm khẳng định 2 kết luận nhân quả vững chắc:

1. **Chuỗi Nhân quả Suy giảm (Corruption -> Failure):**
   ```text
   Tiêm lỗi (Drop 20% + Blank summary + Inject noise)
       │
       ▼
   Báo động Data Observability (GX FAIL + Freshness STALE)
       │
       ▼
   Silent Failure trong RAG (Hit Rate giảm xuống 80.0%, Token F1 giảm xuống 0.6000)
   ```
2. **Chuỗi Nhân quả Tự phục hồi (Idempotent Repair -> Recovery):**
   ```text
   Tái nạp raw snapshot tin cậy + Re-clean chuẩn hóa
       │
       ▼
   Phục hồi Observability (GX 1.x PASS 100% + Freshness FRESH)
       │
       ▼
   Phục hồi RAG Metrics (Hit Rate trở lại 100.0%, Token F1 trở lại 1.0000)
   ```

---

## 6. Kết luận & Đánh giá Nghiệm thu

Pipeline tích hợp của nhóm đã hoàn thành xuất sắc toàn bộ các mục tiêu đặt ra:
- Chứng minh được tính phòng vệ nhiều tầng của Data Observability.
- Định lượng chính xác tác động của dữ liệu bẩn tới hành vi của AI Agent.
- Hiện thực hóa thành công kiến trúc tự phục hồi Idempotent an toàn và đáng tin cậy.
