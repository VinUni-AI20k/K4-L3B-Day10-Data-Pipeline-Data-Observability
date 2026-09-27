# Báo cáo triển khai web demo

Ngày: 27/09/2026. Nhánh: `khoi`. Yêu cầu mới được thực hiện dưới dạng trang web tương tác; CLI và các gói nghiệm thu trước giữ vai trò bằng chứng lịch sử.

## Chức năng đã thực hiện

- Giao diện với sidebar, trạng thái dữ liệu, thẻ KPI và bố cục responsive.
- Sơ đồ Raw → Transform → Quality → Index → QA, có mô tả khi chọn từng bước và hiệu ứng trình diễn. Hiệu ứng này được ghi rõ là minh họa flow đã lưu.
- Biểu đồ SVG và bảng benchmark baseline/corrupted/repaired đọc từ artifact thật; phân biệt benchmark extractive/mock với bằng chứng Gemini online.
- Bảng kiểm tra sáu corruption, chọn DOI và so sánh số dòng/ngày/title/summary ở ba trạng thái. Có tìm kiếm corpus.
- Khung chat Gemini online, hỗ trợ câu tự do bằng tiếng Việt, exact lookup và semantic search. Có lựa chọn một corpus hoặc so sánh cùng câu trên cả ba corpus.
- Hiển thị câu trả lời, latency, token, nguồn DOI và tool calls. Lỗi API không được chuyển thành mock.
- Chế độ trích xuất local không cần API, được ghi nhãn rõ và dùng tốt với câu mẫu.
- Nút chạy pipeline thật: gọi hai entrypoint hiện có với output dưới `demo/runtime/`, xác minh kết quả rồi mới thay corpus đang phục vụ.

## File thay đổi

Mọi file mới của lượt này nằm trong `demo/`: backend `app.py`, static HTML/CSS/JS/SVG, unit test, HTTP test, README, báo cáo này và evidence. Mọi file sinh trong quá trình chạy web nằm ở `demo/runtime/`; thư mục này được ignore trong Git.

Các file đã tồn tại được sửa để hướng người dùng sang web:

- `README.md`: thêm lệnh mở web làm điểm vào chính của demo.
- `docs/CP6_LIVE_DEMO_GUIDE.md`: thêm liên kết web, giữ hướng dẫn CLI lịch sử.
- `docs/CP6_GEMINI_ACCEPTANCE_2026-09-27.md`: thêm liên kết báo cáo web; giữ nguyên số liệu nghiệm thu cũ.

Không thay mã pipeline/retrieval đã nghiệm thu trong lượt này. Backend web tái sử dụng chúng. Không sửa `.env`, raw, dữ liệu cũ, tài liệu đóng góp trên `main`; không commit/push.

## Cách triển khai

Backend dùng `ThreadingHTTPServer` và một worker xử lý job, frontend dùng HTML/CSS/JavaScript và SVG. Không cần cài framework hoặc Node. Server chỉ bind `127.0.0.1`.

Run mặc định là `cp6_pipeline_20260927_04`. Checker đối chiếu artifact trước khi dashboard nhận dữ liệu. Index phục vụ chat được sao chép vào `demo/runtime/`, đóng/mở riêng theo trạng thái và được nạp lại sau khi chuyển sang run mới. File raw trong repo chỉ được đọc.

Key Gemini chỉ được đọc ở backend. Dashboard không trả key; static server chỉ phục vụ bốn file giao diện, không phục vụ `.env`. POST khác origin bị từ chối. Câu hỏi giới hạn 2.000 ký tự; mỗi job chat tối đa 12 lượt gọi model, timeout 60 giây/call và không retry SDK tự động.

Hội thoại trên màn hình gồm các lượt độc lập, không dùng lịch sử làm context. Điều này phù hợp với mục tiêu thử cùng câu hỏi trên dữ liệu khác nhau; chưa phải chatbot có bộ nhớ dài hạn.

## Kết quả kiểm chứng

| Hạng mục | Kết quả |
| --- | --- |
| Unit test mới | 7/7 đạt |
| HTTP/integration checks | 15/15 đạt |
| Gemini hỏi ngày bị sửa trên ba corpus | `2026-05-02` → `2025-05-02` → `2026-05-02` |
| Gemini hỏi DOI không tồn tại | Từ chối, không có nguồn bài thay thế |
| Gemini hỏi tự do bằng tiếng Việt | Gọi `semantic_search_papers`, trả bài/DOI/tóm tắt tiếng Việt, có 3 nguồn tool trả về |
| Local hỏi bài bị xóa | Ngày đúng → từ chối → ngày đúng |
| Chạy pipeline qua HTTP | Hoàn tất, tạo run mới trong `demo/`, 99 kiểm tra artifact đạt |
| Chat sau khi đổi run | Dùng đúng run mới; ba giá trị ngày vẫn khớp |
| Dữ liệu có trước lượt web | 754 file giữ nguyên SHA-256 |
| JavaScript | Parse/compile thành công bằng V8 |
| HTML/JS | ID không trùng; các ID JavaScript tham chiếu đều tồn tại |
| Quét key trong `demo/` | Không tìm thấy key đang cấu hình trong artifact |
| `git diff --check` | Đạt |

Bằng chứng: [verification.json](evidence/verification.json), [http_checks.json](evidence/http_checks.json), [semantic_chat.json](evidence/semantic_chat.json). File HTTP checks chứa kết quả và câu trả lời thực tế của từng job, không chỉ số tổng hợp.

## Lỗi và giới hạn kiểm tra

- Công cụ browser không có Chrome hoặc trình duyệt tích hợp được kết nối. Do đó chưa kiểm tra trực quan bằng screenshot hay click end-to-end trên trình duyệt. Đã kiểm thử endpoint mà UI sử dụng, compile JavaScript và kiểm tra liên kết DOM; cần mở trang để duyệt bố cục thực tế.
- Lệnh `node --check` không chạy vì máy không có Node. Đã dùng V8 để kiểm tra cú pháp JavaScript; Node không phải dependency của web demo.
- Chế độ local trích xuất thông tin có quy tắc, không đại diện chất lượng LLM hoặc chat tự do tiếng Việt. Gemini online được dùng để kiểm chứng câu hỏi tự do.
- Chưa tự chấm độ đúng tổng quát cho câu hỏi mở. Nguồn được hiển thị là tài liệu tool trả về, không phải xác nhận rằng mọi mệnh đề trong câu trả lời đều đã được kiểm chứng.
- Quota/độ trễ Gemini vẫn phụ thuộc provider. Bằng chứng online lịch sử có nhãn riêng và không thay thế câu trả lời mới khi API lỗi.

## Mở và sử dụng

```powershell
.venv/Scripts/python.exe -B demo/app.py
```

Truy cập http://127.0.0.1:8765. Hướng dẫn từng bước và kịch bản trình diễn nằm tại [README.md](README.md).
