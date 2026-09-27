# Data Observatory — Web demo

**Máy mới hoặc chuẩn bị push lên GitHub:** bắt đầu với [docs/README_khoi.md](../docs/README_khoi.md). Danh sách file bàn giao nằm trong [publish_files.txt](publish_files.txt); chạy `python -B demo/check_publish.py` từ root để kiểm tra trước khi stage.

Trang web trực quan cho lab Data Pipeline & Data Observability, gồm data flow, benchmark ba trạng thái, kiểm tra dữ liệu và chatbot Gemini. Mọi file mới, log, bản sao Chroma và output pipeline của web nằm trong `demo/`.

## Mở trang web

Mở PowerShell tại root repo:

```powershell
.venv/Scripts/python.exe -B demo/app.py
```

Giữ terminal này mở và truy cập **http://127.0.0.1:8765** bằng Chrome hoặc Edge. Dùng `Ctrl+C` trong terminal để dừng server. Không mở trực tiếp `demo/static/index.html`, vì trang cần backend Python.

Nếu cổng 8765 đang được dùng:

```powershell
.venv/Scripts/python.exe -B demo/app.py --port 8766
```

Sau đó mở http://127.0.0.1:8766. Không cần Node, npm, Streamlit, FastAPI hay thêm dependency ngoài môi trường hiện có của repo.

## Cấu hình chatbot

Backend đọc `.env` ở root. Gemini dùng `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY`; model lấy từ `LLM_MODEL` khi `LLM_PROVIDER=gemini` hoặc `google`. Nếu `.env` đang chọn OpenRouter, web vẫn dùng Gemini key với model mặc định `gemini-3.5-flash-lite`.

Key chỉ nằm ở backend, không được đưa vào HTML/JavaScript/API dashboard. Trang không có ô nhập key. Sau khi cập nhật key trong `.env`, gửi câu hỏi mới; không cần sửa mã nguồn. Không chiếu `.env` trong buổi demo.

Chat online gửi câu hỏi và phần corpus mà tool trả về tới Gemini API. Nút **Chạy pipeline mới** và chế độ **Trích xuất local** không gọi LLM online. Nếu API lỗi, trang hiển thị lỗi và giữ các câu trả lời đã hoàn tất; không tự chuyển sang mock.

## Trình diễn 3–5 phút

1. **Tổng quan:** chọn các tab Dữ liệu sạch / Corrupted / Repaired. Chỉ ra 24 → 20 → 24 tài liệu, GX 7/7 → 3/7 → 7/7 và Hit Rate 100% → 80% → 100%.
2. **Data flow:** chọn từng bước Raw → Transform → Quality → Index → QA. “Trình diễn flow” chỉ tô sáng sơ đồ từ dữ liệu đã lưu. Nói rõ corrupted được index trong collection thử nghiệm riêng để đo tác động.
3. **Benchmark:** xem biểu đồ và bảng metrics. Benchmark 10 câu là extractive QA/mock judge. Khối Gemini là bằng chứng online đã lưu của bốn case, có nhãn run gốc; không phải điểm của hội thoại vừa hỏi.
4. **Kiểm tra dữ liệu:** chọn “Ngày bị làm cũ”. So sánh cùng DOI ở ba cột: `2026-05-02` → `2025-05-02` → `2026-05-02`. Chọn “Mất bài mới nhất” để thấy bài biến mất rồi trở lại.
5. **Phòng chat:** chọn Gemini online, bật **So sánh cả 3**, bấm câu mẫu **Ngày bị sửa**, rồi **Gửi câu hỏi**. Ba câu trả lời được hiển thị cạnh nhau; mở phần nguồn/tool để xem bằng chứng tra cứu.
6. Thử **Bài bị mất**, **DOI không tồn tại**. Với câu hỏi tự do bằng tiếng Việt, dùng Gemini; câu mẫu **Tìm kiếm ngữ nghĩa** kiểm tra tool tìm vector.

Thông điệp trình bày: “Model có thể trả lời đúng theo context nhưng sai so với raw khi dữ liệu đã bị sửa. Observability phát hiện vấn đề; repair khôi phục dữ liệu và câu trả lời.”

## Chạy pipeline thật từ giao diện

Bấm **Chạy pipeline mới**. Server gọi hai entrypoint baseline/corruption hiện có với output riêng dưới `demo/runtime/<session>/pipeline_runs/`. Khi cả hai hoàn tất và checker đạt, dashboard cùng corpus chat chuyển sang run mới. Nếu pipeline lỗi, run đang xem vẫn được giữ nguyên.

Raw trong `data/raw/` chỉ được đọc. Chat mở bản copy index trong `demo/runtime/<session>/indices/`, không mở ghi vào index bàn giao. Mỗi lần chỉ chạy một job để tránh pipeline và chat cùng thay corpus.

## Khung chat hoạt động thế nào?

- Chọn một trạng thái để hỏi riêng, hoặc bật **So sánh cả 3** để gửi cùng câu hỏi tới ba corpus.
- **Gemini online:** model thật gọi tool rồi trả lời; hiện model, latency, token, DOI và tool call.
- **Trích xuất local:** không gọi API; phù hợp với câu mẫu tiếng Anh về ngày/tác giả/tóm tắt. Không quảng bá chế độ này là chatbot LLM đầy đủ.
- Mỗi câu hỏi là một lượt độc lập, không dùng lịch sử hội thoại làm context; điều này giúp so sánh các trạng thái công bằng.
- Giới hạn câu hỏi 2.000 ký tự, tối đa 12 lượt gọi model cho một job, timeout 60 giây mỗi call, không retry SDK tự động. Độ trễ/quota API có thể thay đổi.
- “Xóa hội thoại trên màn hình” chỉ xóa phần hiển thị. Log kiểm chứng vẫn nằm trong `demo/runtime/<session>/jobs/`.

## File và bằng chứng

```text
demo/
  app.py                 Backend HTTP local + pipeline/chat jobs
  static/index.html      Giao diện
  static/styles.css      Bố cục responsive
  static/app.js          Biểu đồ SVG, bảng, chat và polling
  static/favicon.svg
  test_app.py            Unit tests
  check_web.py           Kiểm thử HTTP và các luồng thực tế
  README.md
  IMPLEMENTATION.md      Báo cáo triển khai/kiểm chứng
  evidence/              Kết quả kiểm thử và đối chiếu dữ liệu
  runtime/               Output mới; được ignore trong Git
```

Run mặc định là `data/runs/cp6_pipeline_20260927_04`. Có thể chọn run khác bằng `--run <đường-dẫn-run>`, miễn run có đủ baseline/comparison và vượt checker. Bằng chứng Gemini lịch sử lấy từ `data/live_demos/cp6_gemini_20260927_02` và được ghi nhãn riêng ngay cả khi dashboard chuyển sang run mới.

## Kiểm tra và xử lý lỗi

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s demo -p test_app.py -v
```

Khi web server đang chạy, kiểm tra cả chat online và pipeline thật:

```powershell
.venv/Scripts/python.exe -B demo/check_web.py --online --pipeline
```

Lệnh này có gọi Gemini và tạo một run mới bên trong `demo/`. Kết quả lưu tại `demo/evidence/http_checks.json`.

| Triệu chứng | Xử lý |
| --- | --- |
| `WinError 10048` | Cổng đã dùng; mở server hiện có hoặc chọn `--port 8766`. |
| Chưa có Gemini key | Điền key hợp lệ vào `.env` ở root; không nhập vào khung chat. |
| API 429/timeout | Đợi quota/provider phục hồi; dùng local khi cần minh họa ngay và nói rõ chế độ. |
| Lần hỏi đầu chậm | Server đang nạp MiniLM và sao chép index. Các lần sau dùng model đã nạp. |
| Run không vượt checker | Chọn run còn nguyên artifact; không sửa manifest để bỏ qua kiểm tra. |
| Pipeline mới thất bại | Đọc log ở `demo/runtime/<session>/logs/`; dashboard vẫn giữ run cũ. |

Đây là ứng dụng demo local, chỉ bind `127.0.0.1`; không phải dịch vụ triển khai công khai. Các gói bàn giao/CLI trước đó được giữ như bằng chứng lịch sử. Phần đóng góp nhóm trên `main` không được chỉnh sửa.
