# Checkpoint 6 — Nghiệm thu kỹ thuật live demo Gemini

Bản bổ sung giao diện web nằm trong `demo/`: [hướng dẫn mở trang và sử dụng](../demo/README.md), [báo cáo triển khai web](../demo/IMPLEMENTATION.md). Số liệu trong tài liệu này tiếp tục là bằng chứng của lượt CLI đã nêu bên dưới.

Ngày: 27/09/2026. Nhánh: `khoi`. Phạm vi: chuẩn bị và diễn tập live demo online; bỏ qua tài liệu đóng góp nhóm trên `main` theo xác nhận của người dùng. Không commit/push, không sửa raw hoặc `.env`.

## 1. Kết luận và bộ bằng chứng được chọn

Đã hoàn tất phần chuẩn bị và diễn tập kỹ thuật: chạy pipeline ba trạng thái, gọi Gemini thật qua tool agent, lưu câu trả lời/tool trace và chuẩn bị kịch bản trình bày 3–5 phút cùng Q&A.

- **Run dữ liệu chuẩn:** [`cp6_pipeline_20260927_04`](../data/runs/cp6_pipeline_20260927_04/run_manifest.json).
- **Bộ bằng chứng online hoàn tất:** [`cp6_gemini_20260927_02`](../data/live_demos/cp6_gemini_20260927_02/demo_manifest.json).
- **Provider/model:** Gemini API, `gemini-3.5-flash-lite`; tên model này xuất hiện trong toàn bộ 24 phản hồi AI đã lưu.
- **Kiểm chứng:** 34 test đạt; 132 kiểm tra pipeline đạt; 12/12 case online đạt yêu cầu trình diễn.
- **Bảo toàn:** 158 file dữ liệu có trước phần live demo giữ nguyên SHA-256, gồm raw và bộ bàn giao trước.

**Lượt online có một lần chạy tiếp:** Gemini trả đúng 11 câu đầu, sau đó SDK lỗi ở câu cuối. Đã giữ nguyên lượt lỗi, chạy lại riêng câu cuối thành công trên cùng run/index/case/model, rồi đóng dấu bộ bằng chứng hoàn tất. Không gọi đây là một lần chạy liên tục không lỗi. `prior_attempt_results.json` và `continuation_result.json` giữ nguồn gốc từng phần.

Việc nhóm trực tiếp trình bày trước giảng viên, phản biện tại lớp và được công nhận vẫn cần diễn ra thực tế; báo cáo này xác nhận phần kỹ thuật đã sẵn sàng, không thay cho xác nhận của giảng viên.

## 2. Kết quả online thực tế

Xem [bảng online](../data/live_demos/cp6_gemini_20260927_02/online_report.md) và [câu trả lời cùng trace](../data/live_demos/cp6_gemini_20260927_02/online_results.json).

| Case | DOI | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- | --- |
| Bài bị mất | `10.1145/3637528.3671812` | `2026-07-22` | Từ chối vì không có trong index | `2026-07-22` |
| Ngày bị làm cũ | `10.1145/3637528.3671806` | `2026-05-02` | **`2025-05-02`** | `2026-05-02` |
| Bài không bị tác động | `10.1145/3637528.3671824` | `2026-06-12` | `2026-06-12` | `2026-06-12` |
| DOI không tồn tại | `10.9999/cp6-not-in-corpus` | Từ chối | Từ chối | Từ chối |

Câu từ chối được model trả là `I don't know from the indexed corpus.`. Mỗi case đều có lời gọi `lookup_paper` đúng DOI và kết quả tool trước câu trả lời cuối.

| Phép kiểm tra trên bốn case | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Tuân theo dữ liệu trong index và dùng đúng tool | 4/4 | 4/4 | 4/4 |
| Câu trả lời đúng so với raw gốc | 4/4 | 2/4 | 4/4 |

Ngày `2025-05-02` minh họa silent failure: model trả lời đúng theo context đã bị sửa, nhưng sai với raw. Khi repair, ngày đúng quay lại. Trường hợp bài bị xóa minh họa mất khả năng trả lời và abstention an toàn. Hai control giữ nguyên hành vi.

Không diễn giải “12/12 đạt” là 12 câu đều đúng với raw: hai câu corrupted cố ý biểu diễn tác động dữ liệu lỗi. Bộ chấm yêu cầu chúng có hành vi dự kiến và trace thật. Reference/case được đóng băng trước khi gọi model, không sửa để ép pass.

Bộ đếm ghi nhận **26 lượt khởi tạo gọi model** qua lượt đầu và lần chạy tiếp, gồm lượt lỗi. Bộ kết quả được chọn chứa **24 phản hồi AI thành công**, tổng **8.513 token theo usage của các phản hồi đã lưu**. Số token này không bao gồm preflight hoặc phản hồi không lưu được ở lượt lỗi; không dùng nó làm tổng hóa đơn API.

## 3. Pipeline ba trạng thái dùng trong demo

Hai entrypoint `script/run_phase1.py` và `script/run_corruption_flow.py` đã chạy thành công cho run `cp6_pipeline_20260927_04`. [Báo cáo corruption](../data/runs/cp6_pipeline_20260927_04/comparison/attempt-001/reports/corruption_report.md) vẫn dùng bộ benchmark 10 câu/4 loại đã đóng băng.

| Chỉ số pipeline | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Số dòng | 24 | 20 | 24 |
| Retrieval Hit Rate | 1.0 | 0.8 | 1.0 |
| Mean Token F1 | 1.0 | 0.8 | 1.0 |
| Grounded Token F1 | 1.0 | 0.8 | 1.0 |
| GX expectations đạt | 7/7 | 3/7 | 7/7 |
| Quality Gate | Đạt | Không đạt | Đạt |

Benchmark 10 câu này vẫn là extractive metadata QA/mock judge để so sánh dữ liệu một cách xác định. **Phần LLM online là bộ bốn case ở mục 2**, được ghi riêng. Không đổi nhãn benchmark offline thành online, không tuyên bố đã chạy Ragas hoặc online LLM judge.

Raw → clean → embedding manifest → Chroma IDs/segment → answers → metrics → report đã được checker độc lập đối chiếu. Cả hai raw của run được sao chép nguyên byte từ raw gốc; baseline/comparison dùng cùng test set. Gemini đọc bản copy Chroma trong lượt demo để không ghi vào run đã đóng dấu. Run gốc được xác minh lại sau phần online.

## 4. Thay đổi mã nguồn và tài liệu

| File | Thay đổi |
| --- | --- |
| `script/run_live_demo.py` | Entrypoint mới: đọc provider/model/key, kiểm tra kết nối, gọi hai pipeline, xác minh artifact, copy index, chạy case online, lưu trace/usage/report/manifest. Hỗ trợ Gemini và OpenRouter; lỗi API không fallback mock. |
| `src/retrieval/agent.py` | Cho phép truyền `llm` vào `build_agent` để demo dùng đúng SDK/provider/model với timeout và retry được kiểm soát; giữ đường khởi tạo cũ cho caller khác. |
| `tests/test_live_demo.py` | 10 test mới: stale date đúng theo context nhưng sai raw; bài mất/absent; bắt buộc tool đúng; không bỏ qua chuỗi rác; ẩn header/key/thought; lỗi SDK serialize được; replay phát hiện tamper; offline không được coi là online; chặn ID vượt thư mục. |
| `README.md` | Thêm cách chạy Gemini demo và phân biệt run CP6 mới với gói bàn giao lịch sử. |
| `docs/CP6_LIVE_DEMO_GUIDE.md` | Lời dẫn 3–5 phút, thao tác terminal, replay, xử lý lỗi và Q&A. |
| `docs/CP6_GEMINI_ACCEPTANCE_2026-09-27.md` | Báo cáo kết quả, thay đổi, lỗi thực tế và giới hạn nghiệm thu. |

Script chuẩn hóa `GEMINI_API_KEY`/`GOOGLE_API_KEY` trong bộ nhớ cho phần demo. Không in hoặc ghi key vào output. Giới hạn tối đa 36 call/lượt demo, timeout 60 giây/call, tắt retry SDK, có khoảng cách giữa các call và dừng ngay khi một case không đạt. Các tên model/provider có thể chọn qua CLI.

`--replay` xác minh hash rồi hiển thị bằng chứng đã lưu, không gọi API. `--offline-rehearsal` có trạng thái riêng và không được tính là nghiệm thu online. Các cơ chế này không giả lập một lần inference mới.

## 5. Lỗi đã gặp và cách xử lý

| Lượt/vị trí | Lỗi quan sát được | Cách xử lý và tình trạng |
| --- | --- | --- |
| Cấu hình OpenRouter ban đầu | Key cũ trả HTTP 401; tên biến có tiền tố `1`; model được chọn là embedding | Người dùng cập nhật key; demo hỗ trợ alias trong bộ nhớ và chọn chat model. Không sửa `.env`. |
| `cp6_online_20260927_01` — Nemotron | Câu control có chuỗi ký tự rác trước ngày đúng | Chấm fail, giữ ba câu đã lưu; dừng tiến trình. Thêm test không được âm thầm cắt rác rồi tính pass. |
| `cp6_online_20260927_02` — Qwen | HTTP 429; chẩn đoán xác nhận `upstream_provider_shared_pool` ở ModelRun | Không coi là key sai. Giữ evidence lỗi, không dùng làm kết quả đạt. |
| `cp6_online_20260927_03` — Gemma | HTTP 429 ở câu đầu | Không có câu hoàn tất; nguyên nhân chi tiết của lần này không được lưu. Không suy diễn là cùng nguyên nhân với Qwen. |
| `cp6_online_20260927_04` — OpenRouter free router | HTTP 400: endpoint được chọn bắt buộc reasoning, không cho tắt | Bỏ tham số ép tắt reasoning ở nhánh OpenRouter trong script. Nhánh sửa này chưa được chạy nghiệm thu lại vì người dùng chuyển sang Gemini. |
| `cp6_gemini_20260927_01` — Gemini | SDK `ChatGoogleGenerativeAIError` ở câu thứ 12, sau 11 câu đạt | HTTP/root cause cụ thể không được lưu ở lượt này. Chạy lại riêng case cuối thành công; giữ lỗi gốc và nối tiếp trên cùng run dữ liệu. Không khẳng định đã xác định nguyên nhân provider. |
| Test mới ban đầu | Test mong `ValueError`, CLI thực tế trả `argparse.ArgumentTypeError` | Sửa assertion trong `tests/test_live_demo.py`; suite cuối cùng 34/34 đạt. |

Các lượt OpenRouter và lượt Gemini chưa hoàn tất vẫn nằm trong `data/live_demos/` để đối chiếu. Chúng không được chọn làm bằng chứng đạt. Bộ Gemini hoàn tất ghi nguồn từng answer ở `source_attempt`, giữ lỗi ban đầu và kết quả retry. Không ghi đè artifact lịch sử để làm mất lỗi.

## 6. Cách chạy và trình bày

Chạy online mới, dùng lại pipeline đã xác minh khi source chưa đổi:

```powershell
.venv/Scripts/python.exe -B script/run_live_demo.py --demo-id cp6_live_next --run-id cp6_pipeline_20260927_04 --provider gemini --model gemini-3.5-flash-lite
```

Nếu muốn tính lại toàn bộ pipeline, dùng run ID mới. Mỗi lần gọi API dùng demo ID mới. Độ trễ/quota provider không được bảo đảm; nên chạy rehearsal trước giờ lên trình bày.

Hiển thị bộ bằng chứng được chọn mà không gọi API:

```powershell
.venv/Scripts/python.exe -B script/run_live_demo.py --replay data/live_demos/cp6_gemini_20260927_02
.venv/Scripts/python.exe -B script/verify_run.py data/runs/cp6_pipeline_20260927_04 --project-dir .
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
```

Kịch bản chi tiết: [CP6_LIVE_DEMO_GUIDE.md](CP6_LIVE_DEMO_GUIDE.md). Bằng chứng kiểm thử và bảo toàn: [handover/cp6_evidence](../handover/cp6_evidence/).

## 7. Bàn giao và giới hạn

[Gói CP6 Gemini](../handover/cp6_gemini_20260927.zip) chứa source hiện tại, hướng dẫn, dependency metadata, raw/test set gốc, toàn bộ run `cp6_pipeline_20260927_04`, bộ Gemini hoàn tất và bằng chứng kiểm tra. Run gồm cả SQLite và toàn bộ segment Chroma được DB tham chiếu. Gói không chứa `.env`, `.git`, virtualenv, model cache hay working copy Chroma dùng khi gọi online.

`handover/cp6_package_verification.json` ghi SHA-256 archive và kết quả xác minh sau giải nén. Gói bàn giao `khoi_handover_20260927_01.zip` trước đó được giữ nguyên như bằng chứng lịch sử; source trong gói đó khác source CP6.

Giới hạn: bốn case online kiểm tra exact lookup/date/abstention và ảnh hưởng dữ liệu, chưa là đánh giá toàn diện semantic retrieval, câu hỏi mở hoặc chất lượng LLM trên toàn benchmark 10 câu. Một case cần retry nên không thể cam kết chạy liên tục luôn thành công. Chưa kiểm chứng cài mới dependency/model cache trên máy khác; kiểm tra giải nén và di chuyển artifact không thay thế việc cài mới.

Nhóm có thể dùng bộ này để trình bày phần kỹ thuật CP6. Phần đóng góp nhóm đã có trên `main` được bỏ qua theo yêu cầu; không tự truy cập/chỉnh sửa `main`, không commit/push, không nộp LMS thay người dùng.
