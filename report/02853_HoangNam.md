# Báo cáo cá nhân — 02853_HoangNam

- **Thành viên:** Hoàng Nam (02853)
- **Nhóm/lớp:** Trike — K4-L3B-DAY10
- **Phạm vi:** Quality gate và freshness monitoring Phase 1
- **Ngày ghi nhận:** 2026-09-26

## Công việc phụ trách

Hoàn thiện `src/observability/quality.py`, trọng tâm là `run_data_quality_checks(df, settings, stage)` với Great Expectations 1.x Ephemeral Context và `evaluate_freshness_sla()`.

## Cách thực hiện và quyết định kỹ thuật

- Tạo pandas data source, dataframe asset, whole-dataframe batch definition và batch trên Ephemeral Context để kiểm định trực tiếp DataFrame sạch.
- Thực thi sáu expectation từ bốn loại yêu cầu: số dòng trong [5, 5000]; `paper_id`, `title`, `text_for_embedding` không null; `paper_id` duy nhất; `summary` dài ít nhất 30 ký tự.
- Kiểm tra thêm cột bắt buộc bị thiếu, chuỗi chỉ chứa khoảng trắng và summary quá ngắn. Các trường hợp này làm `success=false` ngay cả khi phép kiểm null của GX không phát hiện chuỗi rỗng.
- Tính tỉ lệ bài cũ từ `age_days > 180`; `is_fresh=false` nếu tỉ lệ vượt 25%, thiếu tuổi dữ liệu hoặc DataFrame rỗng. Kết quả GX và freshness cùng quyết định trạng thái cuối.
- Ghi báo cáo chất lượng theo `stage` và báo cáo freshness để pipeline có dấu vết kiểm định.

## Đầu ra và bằng chứng

| Đầu ra | Kết quả ghi nhận |
| --- | --- |
| [Baseline quality report](../data/quality/baseline_quality_report.json) | `success=true`, `gx_success=true`, 6/6 expectations đạt, 24 dòng |
| [Freshness report](../data/quality/freshness_report.json) | 0/24 bài cũ trên 180 ngày; `is_fresh=true`; ngưỡng cho phép 25% |

Lệnh kiểm tra `run_data_quality_checks(df, s, 'test')` với dữ liệu sạch đã in trạng thái `True`. Quality gate cũng được gọi trong pipeline baseline trước khi tạo index; nếu không đạt, pipeline dừng và trỏ đến báo cáo lỗi.

## Giới hạn và bàn giao

Quality gate xác nhận các ràng buộc schema, độ dài, tính duy nhất và độ tươi. Nó không xác nhận tính đúng thực tế của abstract hay `subject` do Crossref cung cấp; hiện 0/24 bài có lĩnh vực.

## Liên kết với toàn tuyến và hướng cải thiện

Quality gate nhận DataFrame sau cleaning và chạy trước Chroma index. Kiểm tra GX phát hiện cấu trúc hoặc giá trị không hợp lệ; freshness đo riêng tuổi dữ liệu theo ngày chạy. Hai tín hiệu kết hợp trong `success` để pipeline quyết định tiếp tục hay dừng. Retrieval Hit Rate và Token F1 đánh giá tác động lên RAG sau khi dữ liệu vượt gate; chúng không thay thế kiểm tra dữ liệu đầu vào.

Quyết định kiểm tra thêm chuỗi trắng và tuổi bị thiếu giúp tránh trường hợp expectation `NotBeNull` hoặc tỉ lệ bài cũ thấp che mất dữ liệu vô nghĩa. Cải thiện tiếp theo là thêm kiểm tra tỷ lệ bài có `categories` nếu lĩnh vực trở thành trường bắt buộc; tiêu chí hiện tại chưa yêu cầu điều đó. Khi có dữ liệu corrupted/repaired, cần đối chiếu quality, freshness và metrics trên cùng test set để xác nhận việc sửa có tác dụng.

Các file mã nguồn và artifact ở trên là phần đóng góp được ghi nhận cho Hoàng Nam. Thành viên cần rà soát cách diễn đạt và xác nhận nội dung báo cáo cá nhân trước khi nộp.
