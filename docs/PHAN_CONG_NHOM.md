# Phân công chi tiết nhóm 3 người theo module và checkpoint

## 1. Nguyên tắc phân công

Giữ **một người phụ trách chính mỗi file**, phối hợp và tích hợp ở cuối từng checkpoint. Người phụ trách module sửa lỗi của module đó; Thái điều phối ghép code và kiểm tra toàn luồng.

| Thành viên | Vai trò | Module sở hữu |
|---|---|---|
| **Nguyễn Đình Thái** | Trưởng nhóm, Pipeline & RAG | `core`, `pipelines`, `retrieval`, `script` |
| **Vũ Tiến Linh** | Data Foundation & Recovery | `ingestion` |
| **Dương Đình Long** | Observability & Evaluation | `observability`, `evaluation` |

Code hiện tại đã có triển khai cho phần lớn `core`, `retrieval` và `evaluation/metrics.py`; các phần này cần kiểm chứng, sửa khi cần. Những hàm còn `TODO` trong ingestion, pipelines, quality, reporting và testset cần hoàn thiện.

Mục tiêu là hoàn thành phần bắt buộc trong 240 phút; chưa làm bonus. Đây là kế hoạch phân công, không phải xác nhận các nhiệm vụ đã hoàn thành.

Tài liệu căn cứ: [CHECKPOINTS.md](CHECKPOINTS.md), [RUBRIC.md](RUBRIC.md), [SUBMISSION.md](SUBMISSION.md) và [hướng dẫn báo cáo](../report/README.md).

## 2. Nhiệm vụ chi tiết từng thành viên

### Nguyễn Đình Thái — Pipeline, RAG và tích hợp

| File phụ trách | Cần hoàn thành | Tiêu chí bàn giao |
|---|---|---|
| `pyproject.toml`, `.env.example` | Xác minh cài đặt môi trường Python 3.11–3.13; hướng dẫn cấu hình provider; chỉ dùng placeholder cho secret. | Cả nhóm cài và import được các package, chạy entrypoint từ thư mục repo. |
| `src/core/config.py`, `src/core/utils.py` | Kiểm chứng cấu hình, đường dẫn và hàm đọc/ghi; bổ sung alias `google` → `gemini` để khớp tên provider trong rubric. | Các module dùng chung `Settings` và đường dẫn cấu hình; không hardcode đường dẫn máy cá nhân. |
| `src/retrieval/embeddings.py` | Kiểm chứng MiniLM sinh embedding cho dữ liệu sạch và dữ liệu lỗi. | Sinh vector cho đủ tài liệu được đưa vào index. |
| `src/retrieval/index.py` | Kiểm chứng build/load/search; dùng đúng 3 collection; giữ `paper_id` nghiệp vụ tách khỏi ID bản ghi Chroma để xử lý dữ liệu duplicate. | Baseline có 24 tài liệu; build lại collection không tích lũy bản ghi cũ; các trạng thái không ghi đè nhau. |
| `src/retrieval/qa.py`, `src/retrieval/llm.py`, `src/retrieval/agent.py` | Kiểm chứng QA theo context, router provider và Agent dùng công cụ truy vấn; xử lý đường chạy mock phù hợp khi thiếu API key. | QA trả đúng cấu trúc mà evaluator đang dùng; demo Agent được xác minh riêng. Không coi QA trích xuất hiện có là bằng chứng Agent gọi LLM thành công. |
| `src/pipelines/phase1.py` | Hoàn thiện `main()`: load settings → lấy raw → cleaning → lưu clean → quality/freshness → index → benchmark → evaluate → báo cáo. | Sinh đầy đủ artifacts baseline, metrics và `phase1_report.md`. |
| `src/pipelines/corruption_flow.py` | Hoàn thiện `main()`: đọc baseline → corruption → kiểm định → index/evaluate → phục hồi từ raw → kiểm định/index/evaluate → báo cáo đối chiếu. | Sinh metrics và quality/freshness của corrupted, repaired cùng báo cáo 3 trạng thái. |
| `script/run_phase1.py`, `script/run_corruption_flow.py` | Kiểm chứng entrypoint và import sau khi cài project. | Hai lệnh chạy từ thư mục repo đều kết thúc với exit code 0 khi đủ điều kiện đầu vào. |
| `README.md`, `docs/TEAM.md` | Ghi cách cài/chạy, phân công, checkpoint và thông tin thành viên. | Người khác có thể chạy lại; không ghi công việc dự kiến thành công việc đã hoàn thành. |

**Đầu vào cần nhận:** dữ liệu và hàm xử lý từ Linh; Quality Gate, benchmark và hàm báo cáo từ Long.

**Trách nhiệm tích hợp:** Thái gọi các hàm do hai người còn lại cung cấp; không tự sửa đồng thời file của họ.

### Vũ Tiến Linh — Ingestion, cleaning, corruption và dữ liệu phục hồi

| File phụ trách | Cần hoàn thành | Tiêu chí bàn giao |
|---|---|---|
| `src/ingestion/crossref.py` | Hoàn thiện `parse_crossref_payload()`: ánh xạ Crossref sang `PaperRecord`; xử lý trường thiếu, ngày tháng và định danh DOI. | Parse snapshot chuẩn thành các record có schema nhất quán, ID ổn định. |
| `src/ingestion/crossref.py` | Hoàn thiện `fetch_source_records()`: gọi API, retry có giới hạn với lỗi tạm thời, fallback snapshot khi mạng/API lỗi; lưu raw response và raw records. | Có đủ 2 raw JSON; chạy được với snapshot offline chuẩn gồm 24 bài. Không ghi đè snapshot tốt bằng response lỗi. |
| `src/ingestion/crossref.py` | Hoàn thiện `load_raw_records()`. | Đọc lại JSON thành `list[PaperRecord]`, dùng được cho baseline và repair. |
| `src/ingestion/cleaning.py` | Hoàn thiện `build_clean_dataframe()`: loại JATS/XML và khoảng trắng thừa; chuẩn hóa tác giả, phân loại, ngày; khử trùng lặp; tính các cột phụ. | Có đủ `age_days`, `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`; snapshot chuẩn cho 24 dòng sạch. |
| `src/ingestion/cleaning.py` | Tạo `text_for_embedding` theo 5 phần: title, authors, published, categories, summary; giữ ngày ở định dạng thống nhất cho QA. | Thái index được; Long tạo benchmark và kiểm định được mà không phải đổi tên cột. |
| `src/ingestion/corruption.py` | Hoàn thiện `corrupt_clean_dataframe()`: mất 20% bản ghi mới, blank summary, noise, title ngắn dưới 8 ký tự, stale date, duplicate rows. | Log ghi đủ 6 loại lỗi, ID bị ảnh hưởng và số lượng; không sửa dataframe baseline tại chỗ. |
| `src/ingestion/corruption.py` | Cập nhật lại các cột phụ và embedding text sau corruption; cập nhật `age_days` tương ứng khi lùi ngày. | Lỗi thật sự đi vào kiểm định và retrieval; không chỉ thay đổi cột gốc trong khi text embedding vẫn sạch. |

**Phần repair:** Linh đảm bảo chuỗi `load_raw_records()` → `build_clean_dataframe()` phục hồi được dữ liệu. Thái gọi chuỗi này trong `corruption_flow.py`; không cần tạo một pipeline repair riêng.

**Đầu ra bàn giao:** raw records, dataframe sạch, dataframe lỗi, corruption log và bằng chứng chạy cleaning/repair lặp lại cho kết quả ổn định.

### Dương Đình Long — Quality, freshness, evaluation và reporting

| File phụ trách | Cần hoàn thành | Tiêu chí bàn giao |
|---|---|---|
| `src/observability/quality.py` | Hoàn thiện `run_data_quality_checks()` bằng GX 1.x; kiểm tra số dòng, not-null, uniqueness và độ dài chuỗi. Áp dụng cho `paper_id`, title, summary phù hợp yêu cầu. | Trả dict có `success` và chi tiết kiểm định; ghi báo cáo theo từng trạng thái; phát hiện các lỗi dữ liệu tương ứng. |
| `src/observability/quality.py` | Hoàn thiện `build_freshness_report()`: ngày mới/cũ nhất, số dòng stale, tổng dòng, tỷ lệ stale và `is_fresh`. | `age_days > 180` là stale; tỷ lệ **vượt 25%** mới vi phạm SLA. Dữ liệu rỗng không được báo đạt. |
| `src/evaluation/testset.py` | Hoàn thiện `build_test_set()`: 10 câu thuộc 4 nhóm `summary`, `authors`, `date`, `categories`. | Mỗi câu có `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`; ground truth lấy từ baseline sạch. |
| `src/evaluation/metrics.py` | Kiểm chứng `evaluate_pipeline()` và cách tính metrics hiện có; kiểm tra tương thích với benchmark và QA; sửa lỗi nếu phát hiện. | Xuất metrics và answers, có `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`; phân biệt LLM judge với fallback heuristic. |
| `src/observability/reporting.py` | Hoàn thiện `generate_phase1_report()`. | Báo cáo có nguồn dữ liệu, metrics, chất lượng và freshness từ kết quả thực tế. |
| `src/observability/reporting.py` | Hoàn thiện `generate_corruption_report()`. | Có bảng metrics Baseline–Corrupted–Repaired, quality/freshness được truyền vào và phân tích suy giảm/phục hồi; không tự điền số liệu thiếu. |
| `report/group_report.md` | Tổng hợp kết quả, phân công thực tế, cách chạy, bằng chứng và hạn chế. | Nội dung khớp artifacts do lần chạy tích hợp sinh ra. |

**Đầu vào cần nhận:** schema/raw mẫu ở CP0, dữ liệu sạch ở CP1, kết quả chạy baseline ở CP3 và corruption/repair ở CP4–CP5.

**Đầu ra bàn giao:** benchmark cố định, hàm kiểm định/báo cáo, cấu trúc kết quả rõ ràng để Thái tích hợp.

## 3. Giao diện dùng chung và cách tránh conflict

### Chốt trong 10 phút đầu CP0

- Giữ chữ ký hàm có sẵn. `PaperRecord` là schema raw chung; dataframe clean giữ các trường mà index và evaluator đang dùng.
- Giữ định danh `paper_id` xuyên suốt raw → clean → benchmark → retrieval.
- Thái và Linh dùng cùng mốc `run_date` khi cleaning baseline và repair trong một lần so sánh.
- Benchmark tạo từ baseline và được dùng nguyên vẹn cho cả 3 trạng thái; không tạo lại từ corrupted hoặc repaired.
- Long chốt kết quả quality gồm `success`, chi tiết GX và freshness; Thái đọc kết quả này, không tự tính lại chỉ số.
- Dùng đường dẫn trong `Settings.paths`; báo cáo quality/freshness có tên riêng theo trạng thái để tránh ghi đè.

**Quality Gate:** baseline và repaired phải được kiểm định trước khi index. Với corrupted, ghi nhận kết quả thất bại nhưng cho phép tiếp tục chạy nhánh thí nghiệm để đo tác động. Đây là hành vi chủ đích của bài lab và phải được ghi rõ trong báo cáo.

**Freshness:** nếu snapshot thực sự quá hạn tại ngày chạy, giữ nguyên kết quả cảnh báo; không sửa ngày hoặc ngưỡng để ép pass.

### Quy tắc Git và artifacts

- Ba nhánh làm việc: `feat/thai-pipeline-rag`, `feat/linh-data`, `feat/long-observability`.
- Mỗi người commit phần code mình sở hữu; cần đổi giao diện thì báo cho người gọi trước khi merge.
- Thái điều phối merge cuối mỗi checkpoint, giữ tác giả commit của từng người.
- Linh bàn giao snapshot chuẩn ở CP0; sau đó cố định nguồn raw cho chuỗi so sánh.
- Thái chịu trách nhiệm sinh và đưa bộ artifacts tích hợp vào bài nộp. Hai người còn lại không đồng thời commit lại cùng metrics, báo cáo tự sinh hoặc ChromaDB.
- Lỗi thuộc module nào do owner module đó sửa. Nếu hỗ trợ sửa file của nhau, phải thống nhất người đang chỉnh sửa trước.

## 4. Thời điểm phối hợp và bàn giao

Các mốc dưới đây tính từ lúc bắt đầu; dành khoảng 5 phút cuối mỗi checkpoint để bàn giao và kiểm tra.

| Mốc | Làm song song | Phối hợp và điều kiện chuyển bước |
|---|---|---|
| **CP0 · 0–30 phút** | Thái cài môi trường, kiểm tra cấu hình; Linh hoàn thiện raw ingestion; Long chuẩn bị quality và schema benchmark. | **Phút 0–10:** cả nhóm chốt giao diện. **Phút 25–30:** Linh bàn giao raw mẫu và 2 JSON; Thái, Long kiểm tra đọc được. |
| **CP1 · 30–65 phút** | Linh cleaning; Long GX/freshness; Thái chuẩn bị index và orchestration. | **Khoảng phút 45:** Linh đưa dataframe mẫu để hai người thử sớm. **Phút 60–65:** kiểm tra schema, 24 dòng chuẩn, quality và nguyên nhân nếu freshness cảnh báo. |
| **CP2 · 65–95 phút** | Thái index/QA; Long benchmark; Linh kiểm chứng clean và chuẩn bị corruption. | **Phút 90–95:** ghép clean → index → benchmark → QA. Cố định benchmark, raw snapshot và cấu hình cho 3 trạng thái. |
| **CP3 · 95–120 phút** | Thái chạy baseline; Long hoàn thiện báo cáo; Linh xử lý lỗi dữ liệu nếu có. | **Phút 115–120:** cả nhóm xem metrics, answers và báo cáo baseline. Chỉ chạy đo corruption sau khi baseline hoàn chỉnh. |
| **CP4 · 120–165 phút** | Linh hoàn thiện corruption; Long kiểm định dữ liệu lỗi; Thái tích hợp index/evaluation corrupted. | **Khoảng phút 140:** bàn giao dataframe lỗi và log để chạy thử. **Phút 160–165:** xác nhận đủ 6 lỗi, quality phát hiện và metrics phản ánh kết quả thực tế. |
| **CP5 · 165–210 phút** | Thái tích hợp repair; Linh đối chiếu raw/clean/repaired; Long sinh báo cáo 3 trạng thái. | **Khoảng phút 185:** chạy repair lần đầu. **Phút 200–210:** chạy lại kiểm tra idempotent, đối chiếu metrics và báo cáo, chốt artifacts. |
| **CP6 · 210–240 phút** | Thái chuẩn bị demo; Linh và Long hoàn thiện bằng chứng, báo cáo cá nhân. | Chạy thử demo chung: Thái trình bày luồng/RAG, Linh giải thích corruption/repair, Long giải thích quality/metrics. Kiểm tra hồ sơ và commit của cả nhóm. |

Khi chưa có đầu vào đầy đủ, người nhận làm với mẫu dữ liệu chung đã chốt ở CP0; mẫu thử phải tách khỏi artifacts nộp bài.

## 5. Nghiệm thu và hồ sơ cuối cùng

### Linh kiểm tra

- Parse/fallback offline và đọc lại raw thành công.
- Cleaning loại trùng, chuẩn hóa văn bản và tính đúng tuổi dữ liệu.
- Corruption đủ 6 loại, không làm thay đổi baseline/raw.
- Repair lặp lại giữ nguyên dữ liệu sạch khi dùng cùng raw và `run_date`.

### Long kiểm tra

- GX phát hiện dữ liệu thiếu, trùng và chuỗi không đạt yêu cầu.
- Freshness đúng ở các biên 180 ngày và tỷ lệ 25%.
- Benchmark đủ 10 câu, 4 nhóm, cùng document IDs cho mọi trạng thái.
- Các số liệu trong báo cáo khớp JSON thực tế; không yêu cầu mọi metric đều phải giảm nếu thí nghiệm không chứng minh điều đó.

### Thái kiểm tra

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- Cả hai lệnh chạy thành công; đủ raw, clean, embeddings, benchmark, quality, results và reports.
- Ba collection độc lập; chạy lại không tích lũy dữ liệu.
- Một thành viên khác chạy lại được theo README.
- Kiểm tra Agent riêng; ghi rõ provider đã thực sự thử và hạn chế do thiếu credentials nếu có.

### Hồ sơ và nộp bài

- Cập nhật `docs/TEAM.md` theo phân công này; MSSV/email chưa biết để chỗ bổ sung.
- Mỗi người tự viết `report/<MSSV>_HoTen.md` từ đóng góp thực tế; Long tổng hợp báo cáo nhóm.
- Mỗi người phải có commit trên `main` và tự nộp link LMS trước **23:59:59 ngày 26/09/2026, GMT+7**.
