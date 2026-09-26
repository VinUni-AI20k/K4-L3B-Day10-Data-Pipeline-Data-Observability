# Báo cáo cá nhân — 02623_TuanDat

- **Thành viên:** Tuấn Đạt (02623)
- **Nhóm/lớp:** Trike — K4-L3B-DAY10
- **Phạm vi:** Thu thập raw data và tạo benchmark Phase 1
- **Ngày ghi nhận:** 2026-09-26

## Công việc phụ trách

1. Hoàn thiện `src/ingestion/crossref.py`: `parse_crossref_payload(payload)` và `fetch_source_records(settings)`.
2. Hoàn thiện `src/evaluation/testset.py`: `build_test_set(df, output_path)`.

## Cách thực hiện và quyết định kỹ thuật

- Parser đọc `message.items` của Crossref, lấy DOI, tiêu đề, abstract, tác giả, `subject`, ngày xuất bản và các đường dẫn. Nội dung HTML/XML trong abstract được giải mã và bỏ thẻ; bản ghi thiếu DOI, tiêu đề, tóm tắt hoặc ngày hợp lệ bị loại.
- Khi API trả về thành công, lưu **bytes phản hồi gốc** vào `data/raw/crossref_response.json`; danh sách `PaperRecord` sau bóc tách được lưu riêng trong `data/raw/crossref_records.json`. Sự tách biệt này cho phép tái xử lý mà không phải gọi lại Crossref.
- Hàm fetch thử lại có giới hạn với 429/503, rồi đọc snapshot có sẵn nếu không nhận được phản hồi hợp lệ. Khi dùng snapshot, file phản hồi gốc được giữ nguyên.
- Hàm tạo benchmark chọn bài theo DOI, sinh 10 câu hỏi có `id`, loại câu hỏi, ground truth và `ground_truth_doc_ids`. Phân bố là 3 summary, 3 authors, 2 date, 2 categories.

## Đầu ra và bằng chứng

| Đầu ra | Kết quả ghi nhận |
| --- | --- |
| [JSON Crossref gốc](../data/raw/crossref_response.json) | Snapshot để phục hồi và truy nguyên dữ liệu |
| [Raw records](../data/raw/crossref_records.json) | 24 đối tượng `PaperRecord` |
| [Test set](../data/eval/test_set.json) | 10 câu hỏi; 3/3/2/2 theo summary/authors/date/categories |

Lệnh `build_test_set` với dữ liệu sạch đã sinh 10 câu hỏi. Các artifact raw hiện có 24 records; kết quả này chứng minh dữ liệu sẵn cho pipeline, còn cách lấy trực tuyến hay fallback của lần tạo snapshot hiện tại không được suy ra chỉ từ nội dung file.

## Giới hạn và bàn giao

Snapshot hiện tại không có `subject` cho cả 24 bài. Hai câu hỏi `categories` dùng ground truth nêu rõ metadata Crossref không liệt kê lĩnh vực; điểm Token F1 của loại này bằng 0 trong báo cáo baseline. Nên lấy nguồn có `subject` nếu muốn đánh giá khả năng trả lời câu hỏi lĩnh vực thực sự.

## Liên kết với toàn tuyến và hướng cải thiện

Raw response là điểm bắt đầu để chạy lại parser khi quy tắc bóc tách đổi. Raw records là input trực tiếp cho cleaning; DOI từ đó trở thành document ID trong Chroma và `ground_truth_doc_ids` của benchmark. Các câu hỏi dùng cùng bộ `test_set.json` thì mới so sánh baseline, corrupted và repaired có ý nghĩa; hiện mới có metrics baseline.

Quyết định giữ response nguyên bytes riêng với records đã chuẩn hóa giúp truy nguyên sai lệch do parser mà không tiêu hao thêm lượt gọi API. Bước cải thiện là chọn dữ liệu Crossref có `subject` và cập nhật benchmark từ nguồn đó, sau đó kiểm tra riêng Token F1 của câu hỏi `categories`. Không thể kết luận từ snapshot hiện tại rằng parser đã làm mất lĩnh vực, vì trường này không xuất hiện trong metadata đầu vào.

Các file mã nguồn và artifact ở trên là phần đóng góp được ghi nhận cho Tuấn Đạt. Thành viên cần rà soát cách diễn đạt và xác nhận nội dung báo cáo cá nhân trước khi nộp.
