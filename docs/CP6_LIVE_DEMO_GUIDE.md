# Checkpoint 6 — Kịch bản live demo và Q&A

**Cập nhật: demo chính đã chuyển sang giao diện web** với data flow, benchmark, so sánh dữ liệu và chatbot. Chạy `.venv/Scripts/python.exe -B demo/app.py`, mở http://127.0.0.1:8765. Xem [hướng dẫn web demo](../demo/README.md). Phần dưới giữ kịch bản CLI/bằng chứng của lần nghiệm thu trước.

Phạm vi: phần trình diễn kỹ thuật trên nhánh `khoi`. Thông tin đóng góp nhóm trên `main` được bỏ qua theo yêu cầu. Không commit/push, không sửa raw. Việc trình bày trước giảng viên và được giảng viên công nhận vẫn là hoạt động của nhóm.

## 1. Chuẩn bị trước buổi trình bày

Mở terminal tại root repo và hai tài liệu: báo cáo corruption của run mới, báo cáo online của demo. Đảm bảo đã cài dependency, có cache `sentence-transformers/all-MiniLM-L6-v2`, và máy kết nối Gemini API.

`.env` cần có `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY` hợp lệ. Script chỉ đọc key vào bộ nhớ và dùng provider `gemini`. Không mở `.env` khi chiếu màn hình. Script không chỉnh sửa file này và không đưa key vào evidence.

Lệnh demo bên dưới chọn rõ model chat `gemini-3.5-flash-lite`. Model và key đã vượt kiểm tra kết nối/gọi tool. MiniLM local vẫn tạo vector; Gemini gọi tool và sinh câu trả lời. Script cũng hỗ trợ OpenRouter, nhưng các lượt thử trước có lỗi định dạng, HTTP 429 hoặc yêu cầu reasoning; không dùng chúng làm bằng chứng đạt.

Không dùng model embedding làm chat agent. Model/rate limit online có thể thay đổi; script báo lỗi nếu provider không phục vụ, không tự dùng mock thay thế.

## 2. Lệnh demo một bước

```powershell
.venv/Scripts/python.exe -B script/run_live_demo.py --demo-id cp6_live_next --run-id cp6_pipeline_20260927_04 --provider gemini --model gemini-3.5-flash-lite
```

Mỗi lần gọi online cần `--demo-id` mới để không ghi đè lịch sử. Nếu source/config/dependency thay đổi, dùng cả `--run-id` mới:

```powershell
.venv/Scripts/python.exe -B script/run_live_demo.py --demo-id cp6_live_new_source --run-id cp6_pipeline_new_source --provider gemini --model gemini-3.5-flash-lite
```

Lệnh này xác minh key, gọi hai entrypoint `run_phase1.py` và `run_corruption_flow.py`, kiểm tra toàn bộ artifact rồi gọi agent online. Run pipeline đã hoàn tất sẽ được dùng lại sau kiểm tra hash; mỗi demo mới vẫn gọi LLM online mới. Để biểu diễn lại đầy đủ quá trình tạo dữ liệu/index, chọn run ID mới.

Mỗi demo có bốn câu hỏi ở ba trạng thái, thường cần hai API call/câu: model gọi tool, rồi trả câu trả lời sau khi nhận kết quả tool. Script giới hạn tối đa 36 call, giới hạn nhịp gọi, timeout 60 giây mỗi call và tắt retry SDK. Gemini dùng model đã chỉ định; riêng nhánh OpenRouter giới hạn model miễn phí. Không chạy Ragas hoặc LLM judge trong demo này.

## 3. Lời dẫn 3–5 phút

| Thời gian gợi ý | Thao tác | Ý chính cần nói |
| --- | --- | --- |
| 0:00–0:40 | Chạy lệnh hoặc mở log pipeline đã chạy trước buổi demo | “Nguồn là snapshot Crossref 24 bài. Raw được giữ nguyên. Cleaning, GX và freshness diễn ra trước khi index sạch được publish.” |
| 0:40–1:20 | Mở `corruption_report.md` của run mới | “Cùng một benchmark 10 câu: baseline, corrupted, repaired. Corruption áp dụng sáu lỗi, quality alert kích hoạt repair từ raw.” |
| 1:20–2:40 | Xem terminal online và `online_report.md` | “Đây là model chat thật qua Gemini API. Mỗi câu phải có exact lookup trong trace, không chỉ in câu trả lời mẫu.” |
| 2:40–3:30 | Chỉ hàng `stale_date` | “Ngày trong index bị lùi một năm. Agent vẫn trả lời trôi chảy và đúng theo context, nhưng sai so với raw. Đây là silent data failure.” |
| 3:30–4:10 | Chỉ hàng `dropped_paper` và cột repaired | “Bài bị mất làm agent từ chối, tránh trả bài khác. Repair khôi phục bài và ngày đúng; control không đổi.” |
| 4:10–5:00 | Mở manifest/verification và trả lời Q&A | “Artifact cùng một run được liên kết bằng hash; index online là bản copy, run bàn giao không bị thay đổi. Không suy rộng 4 câu demo thành toàn bộ chất lượng LLM.” |

Độ trễ mạng không bảo đảm nằm trong 3–5 phút. Nên chạy rehearsal trước giờ trình bày, giữ bằng chứng có timestamp; nếu cần gọi API trực tiếp tại lớp, dùng demo ID mới. Không gọi replay là một lần inference mới.

## 4. Bốn case online và cách đọc kết quả

| Case | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| `dropped_paper` | Ngày đúng | Từ chối vì không còn DOI | Ngày đúng trở lại |
| `stale_date` | Ngày đúng | Ngày sai bị lùi một năm | Ngày đúng trở lại |
| `stable_control` | Ngày đúng | Cùng ngày đúng | Cùng ngày đúng |
| `absent_control` | Từ chối | Từ chối | Từ chối |

Case được chọn tự động từ log corruption và đóng băng trước khi gọi model. Reference chuẩn lấy từ baseline đã kiểm tra với raw. `matches_indexed_context` đánh giá model có tuân theo dữ liệu đang được index hay không; `correct_against_raw` đánh giá câu trả lời có đúng với nguồn gốc hay không. Case stale ở corrupted được kỳ vọng đạt tiêu chí trình diễn nhưng sai với raw — phải nói rõ hai nghĩa này.

Bộ bốn case tập trung vào lookup/date/abstention. Bộ 10 câu/4 loại vẫn là benchmark offline riêng, dùng extractive metadata QA và mock judge. Không báo cáo 30 câu benchmark đó là 30 câu do LLM online sinh.

## 5. Replay, kiểm chứng và xử lý lỗi

Hiển thị lại bằng chứng đã lưu, không gọi API:

```powershell
.venv/Scripts/python.exe -B script/run_live_demo.py --replay data/live_demos/cp6_gemini_20260927_02
.venv/Scripts/python.exe -B script/verify_run.py data/runs/cp6_pipeline_20260927_04 --project-dir .
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
```

Replay kiểm tra hash evidence và hiện rõ “REPLAY OF SAVED EVIDENCE - NO NEW ONLINE REQUESTS”. `--offline-rehearsal` chỉ dựng/kiểm chứng dữ liệu, có trạng thái `offline_rehearsal_only`, không được tính là nghiệm thu online.

Bộ được chọn hoàn tất theo cách 11 câu đạt ở lượt đầu và retry riêng câu cuối thành công trên cùng run. Nguồn từng phần được lưu trong artifact; xem [báo cáo nghiệm thu Gemini](CP6_GEMINI_ACCEPTANCE_2026-09-27.md). Không giới thiệu đây là một lần chạy liên tục không lỗi.

| Lỗi | Cách xử lý |
| --- | --- |
| HTTP 401 | Cập nhật key hợp lệ trong `.env`, không đưa key vào chat/report. Chạy lại bằng demo ID mới. |
| HTTP 429 | Chờ quota/rate limit của tài khoản phục hồi. Không liên tục retry hoặc đổi model để che lỗi. |
| Timeout/5xx | Kiểm tra mạng/provider rồi chạy demo ID mới; giữ run pipeline đã kiểm chứng để tiết kiệm thời gian. |
| Model không hỗ trợ tools | Chọn model chat hỗ trợ function calling của provider qua `--model`. Không dùng model embedding. |
| `Run inputs ... changed` | Source/config/dependency khác lúc đóng dấu; dùng run ID mới, không sửa manifest để bỏ qua. |
| `acceptance_failed` | Đọc answer, trace và checks; không đổi reference để ép pass. Sửa nguyên nhân rồi chạy demo mới. |

## 6. Câu hỏi phản biện thường gặp

**GX kiểm tra gì?** Schema/cột và các điều kiện như DOI không null/unique, chiều dài title/summary, tuổi dữ liệu; report lưu kết quả từng expectation. Quality gate sạch phải đạt trước index.

**Tại sao corrupted vẫn được index khi quality không đạt?** Đây là nhánh thí nghiệm có collection riêng để đo tác động. Nó không thay index sạch đang dùng.

**Freshness SLA là gì?** Bài quá 180 ngày được tính stale; vượt tỷ lệ cho phép mới vi phạm SLA. Dữ liệu hỏng vẫn có thể đạt freshness tổng thể, nên freshness không thay thế quality hoặc kiểm tra tính đúng của dữ liệu.

**Tại sao model trả sai dù có retrieval?** Retrieval cung cấp dữ liệu trong index. Khi ngày trong dữ liệu bị sửa, model có thể làm đúng yêu cầu và vẫn trả thông tin sai với thế giới/nguồn gốc. Vì thế cần data observability và repair.

**Idempotent được chứng minh thế nào?** Repair cùng raw/ngày cố định tạo cùng clean data. Run hoàn tất được kiểm tra hash và tái sử dụng. Retry thất bại dùng attempt mới. Đây không phải cam kết LLM online sẽ sinh cùng từng byte ở mọi lần gọi.

**Vector và model chat khác nhau thế nào?** MiniLM biến nội dung thành vector để tìm tài liệu, Chroma lưu vector/metadata. Gemini chat model quyết định gọi tool và viết câu trả lời. Câu hỏi có DOI chủ yếu kiểm tra exact lookup, không chứng minh toàn bộ semantic retrieval.

**Vì sao không chỉ copy SQLite?** Chroma còn tham chiếu segment chứa vector. Phải mang theo SQLite và đủ segment; checker kiểm tra inventory và các tham chiếu đó.

**Chạy online có sửa raw/index bàn giao không?** Raw được đọc/copy, pipeline tạo output riêng. Online mở bản copy Chroma; run đã đóng dấu được kiểm tra lại sau demo.

**Đã hoàn thành CP6 chưa?** Đã chuẩn bị và diễn tập phần kỹ thuật với bằng chứng online sau khi run đạt. Việc nhóm trình bày trước giảng viên, Q&A trực tiếp và được công nhận không thể thay bằng báo cáo tự động. Phần đóng góp nhóm nằm ngoài phạm vi lượt này theo yêu cầu.
