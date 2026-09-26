# KẾ HOẠCH PHÂN CÔNG CÔNG VIỆC NHÓM 3 THÀNH VIÊN
## Dự án: K4-L3B-Day10 — Data Pipeline & Data Observability for RAG

> **Thời lượng thực chiến:** 240 phút (4 giờ)  
> **Bộ dữ liệu:** Crossref Metadata API (hoặc Local Snapshot `data/raw/crossref_response.json`)  
> **Mục tiêu cốt lõi:** Xây dựng Data Pipeline hoàn chỉnh cho RAG Agent, tích hợp Data Observability (Great Expectations 1.x + Freshness SLA), mô phỏng suy giảm dữ liệu (6 kịch bản Data Corruption), đo lường hiện tượng **Silent Failure** và chứng minh năng lực tự phục hồi (**Idempotent Repair**) qua bảng đối chiếu 3 trạng thái: **Baseline vs Corrupted vs Repaired**.

---

## I. BẢNG PHÂN CHIA VAI TRÒ TỔNG QUAN (KHÔNG TRÙNG LẶP FILE)

Để đảm bảo các thành viên làm việc song song hiệu quả, không bị dẫm chân lên nhau và **không bao giờ gặp Git merge conflict**, mỗi thành viên sở hữu độc quyền các file mã nguồn sau:

| Thành viên | Tên vai trò | Trọng tâm phụ trách | File mã nguồn sở hữu độc quyền | File báo cáo & tài liệu |
| :--- | :--- | :--- | :--- | :--- |
| **Thành viên 1**<br>*(Phạm Đình Hải - 2A202602482)* | **Data Foundation & Quality Engineer** | Ingestion, Cleaning, Great Expectations 1.x & Freshness SLA | - `src/ingestion/crossref.py`<br>- `src/ingestion/cleaning.py`<br>- `src/observability/quality.py` | `report/2A202602482_PhamDinhHai.md` |
| **Thành viên 2** | **Evaluation & Failure Injection Engineer** | Benchmark Test Set, 6 Kịch bản Data Corruption & Log kiểm định | - `src/evaluation/testset.py`<br>- `src/ingestion/corruption.py` | `report/<MSSV2>_<HoTen2>.md` |
| **Thành viên 3** *(Lead)* | **Pipeline Orchestrator & Integration Lead** | Lắp ráp Pipeline end-to-end, Phục hồi Idempotent, Báo cáo đối chiếu, Điều hành Demo | - `src/pipelines/phase1.py`<br>- `src/pipelines/corruption_flow.py`<br>- `src/observability/reporting.py` | - `report/<MSSV3>_<HoTen3>.md`<br>- `report/group_report.md`<br>- `docs/TEAM.md` |

---

## II. CẤU TRÚC THƯ MỤC DỰ ÁN & VỊ TRÍ TỪNG FILE

```text
K4-L3B-Day10-TeamVN-DataPipelineDataObservability/
├── .env.example                                ← [Có sẵn] Mẫu biến môi trường (API Key, model)
├── .gitignore                                   ← [Có sẵn] Bỏ qua .env, venv, cache
├── pyproject.toml / requirements.txt            ← [Có sẵn] Khai báo thư viện phụ thuộc
├── README.md                                    ← [Có sẵn] Hướng dẫn tổng quan bài lab
├── PHAN_CONG_NHOM.md                            ← [File này] Kế hoạch phân công chi tiết
│
├── docs/                                        ← Tài liệu hướng dẫn & quy chế
│   ├── CHECKPOINTS.md                           ← Phân bổ 7 mốc thời gian (CP0 -> CP6)
│   ├── RUBRIC.md                                ← Tiêu chuẩn chấm điểm (100 chuẩn + 10 bonus)
│   ├── SUBMISSION.md                            ← Quy định nộp bài & checklist nghiệm thu
│   └── TEAM.md                                  ← [TV3 điền] Thông tin nhóm, phân công & đóng góp
│
├── data/                                        ← Dữ liệu & Artifacts qua các pha
│   ├── raw/                                     ← Snapshot thô: crossref_response.json, crossref_records.json
│   ├── clean/                                   ← File sạch: papers_clean.csv, papers_clean.json
│   ├── chroma/                                  ← Vector DB chứa 3 collection: papers-baseline, papers-corrupted, papers-repaired
│   ├── eval/                                    ← Bộ benchmark: test_set.json (10 câu hỏi)
│   ├── quality/                                 ← Báo cáo GX: baseline/corrupted_quality_report.json, freshness_report.json
│   ├── results/                                 ← baseline_metrics.json, corrupted_metrics.json, repaired_metrics.json, corruption_log.json
│   └── reports/                                 ← phase1_report.md, corruption_report.md (Bảng đối chiếu 3 trạng thái)
│
├── report/                                      ← Báo cáo văn bản nộp chấm điểm
│   ├── group_report.md                          ← [TV3 viết] Báo cáo chung của nhóm (theo template)
│   └── <MSSV>_<HoTen>.md                        ← [Từng người viết] 3 file báo cáo cá nhân của 3 thành viên
│
├── script/                                      ← Entrypoints thực thi lệnh
│   ├── run_phase1.py                            ← Chạy toàn bộ chu trình Pha 1 (Baseline)
│   └── run_corruption_flow.py                   ← Chạy luồng Tiêm lỗi -> Đo suy giảm -> Phục hồi -> So sánh
│
└── src/                                         ← Source code dự án (Module hóa)
    ├── core/                                    ← [ĐÃ HOÀN THIỆN SẴN]
    │   ├── config.py                            ← Quản lý cấu hình, Settings, đường dẫn Paths
    │   └── utils.py                             ← Tiện ích I/O file, JSON, text normalization
    │
    ├── ingestion/                               ← Thu thập, làm sạch & làm bẩn dữ liệu
    │   ├── crossref.py                          ← [TODO: TV1] Ingestion API & Offline snapshot fallback
    │   ├── cleaning.py                          ← [TODO: TV1] Làm sạch văn bản, age_days, text_for_embedding
    │   └── corruption.py                        ← [TODO: TV2] 6 kịch bản tiêm lỗi dữ liệu & corruption_log
    │
    ├── observability/                           ← Giám sát chất lượng dữ liệu & xuất báo cáo
    │   ├── quality.py                           ← [TODO: TV1] Great Expectations 1.x & Freshness SLA
    │   └── reporting.py                         ← [TODO: TV3] Sinh file markdown phase1_report & corruption_report
    │
    ├── evaluation/                              ← Đánh giá chất lượng RAG
    │   ├── testset.py                           ← [TODO: TV2] Sinh bộ 10 câu hỏi benchmark 4 nhóm nghiệp vụ
    │   └── metrics.py                           ← [ĐÃ HOÀN THIỆN SẴN] Tính Hit Rate, Token F1, LLM Judge
    │
    ├── retrieval/                               ← Tầng RAG Agent & Vector DB [ĐÃ HOÀN THIỆN SẴN]
    │   ├── embeddings.py                        ← SentenceTransformer all-MiniLM-L6-v2
    │   ├── index.py                             ← Quản lý Persistent ChromaDB & LocalEmbeddingIndex
    │   ├── llm.py                               ← Router đa nhà cung cấp (Gemini, OpenAI, Mock,...)
    │   ├── qa.py                                ← Trích xuất câu trả lời trực tiếp từ SearchResult
    │   └── agent.py                             ← LangChain Agent có tool semantic_search & lookup
    │
    └── pipelines/                               ← Tích hợp điều phối quy trình end-to-end
        ├── phase1.py                            ← [TODO: TV3] Orchestration toàn bộ Phase 1
        └── corruption_flow.py                   ← [TODO: TV3] Orchestration toàn bộ Corruption & Repair Flow
```

---

## III. NHIỆM VỤ CHI TIẾT TỪNG THÀNH VIÊN

---

### 👤 THÀNH VIÊN 1: Phạm Đình Hải (MSSV: 2A202602482) - Data Foundation & Quality Engineer
> **Mục tiêu:** Đảm bảo nguồn dữ liệu đầu vào chuẩn xác, làm sạch tối ưu cho embedding và xây dựng hàng rào kiểm soát chất lượng tự động bằng Great Expectations 1.x kết hợp Freshness SLA.

#### 1. File mã nguồn sở hữu độc quyền:
* `src/ingestion/crossref.py`
* `src/ingestion/cleaning.py`
* `src/observability/quality.py`

#### 2. Công việc cần thực hiện:
* **Task 1.1 — Ingestion & Snapshot Fallback (`src/ingestion/crossref.py`):**
  - Hoàn thiện `parse_crossref_payload(payload: dict) -> list[PaperRecord]`: Trích xuất DOI (`paper_id`), chuẩn hóa tiêu đề, abstract, tác giả (`authors`), chuyên mục (`categories`), ngày xuất bản (`published`) định dạng `YYYY-MM-DD`. Bỏ qua các bản ghi lỗi hoặc thiếu trường bắt buộc.
  - Hoàn thiện `fetch_source_records(settings: Settings) -> list[PaperRecord]`: Gửi HTTP request đến Crossref API. **Bắt buộc có cơ chế Fallback:** nếu gặp lỗi kết nối hoặc mã lỗi 429/503 thì tự động đọc từ snapshot cục bộ `data/raw/crossref_response.json`. Lưu 2 file raw artifacts: `crossref_response.json` và `crossref_records.json`.
  - Hoàn thiện `load_raw_records(path: Path) -> list[PaperRecord]`: Đọc file JSON snapshot chuyển thành danh sách `PaperRecord`.
* **Task 1.2 — Data Cleaning & Text Modeling (`src/ingestion/cleaning.py`):**
  - Hoàn thiện `build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame`:
    - Khử trùng lặp theo `paper_id`.
    - Loại bỏ thẻ XML/HTML (như `<jats:p>`, `<jats:title>`) và chuẩn hóa khoảng trắng thừa trong `title` và `summary`.
    - Tính toán cột độ tuổi bài báo: `age_days = (run_date - published).days`.
    - Tạo các cột bổ trợ: `authors_joined` (nối các tác giả bằng dấu phẩy), `categories_joined`, `summary_chars`.
    - Xây dựng trường `text_for_embedding` gồm 5 phần chuẩn:
      ```text
      Title: {title}
      Authors: {authors_joined}
      Published: {published}
      Categories: {categories_joined}
      Summary: {summary}
      ```
* **Task 1.3 — Data Observability với Great Expectations 1.x (`src/observability/quality.py`):**
  - Cấu hình ephemeral context chuẩn **GX 1.x**:
    ```python
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    ```
  - Thiết lập đủ 4 Expectations thiết yếu:
    1. `ExpectTableRowCountToBeBetween` (min_value=15, max_value=50).
    2. `ExpectColumnValuesToNotBeNull` cho `paper_id`, `title`, `text_for_embedding`.
    3. `ExpectColumnValuesToBeUnique` cho `paper_id`.
    4. `ExpectColumnValueLengthsToBeBetween` cho `title` (>=8 ký tự) và `summary` (>=20 ký tự).
* **Task 1.4 — Freshness SLA Check (`src/observability/quality.py`):**
  - Hoàn thiện `build_freshness_report`: Tìm ngày mới nhất, ngày cũ nhất, đếm số bài báo quá hạn (`age_days > 180`).
  - Gắn nhãn `is_fresh = False` nếu tỷ lệ bài báo quá hạn vượt quá 25%. Xuất kết quả ra `data/quality/freshness_report.json`.

#### 3. Lệnh tự kiểm chứng độc lập (Self-Verification):
```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Tín hiệu hoàn thành: Quality check status = {res[\"success\"]}')"
```

#### 4. File báo cáo cá nhân:
* File báo cáo chính thức đã tạo tại: [`report/2A202602482_PhamDinhHai.md`](report/2A202602482_PhamDinhHai.md).

---

### 👤 THÀNH VIÊN 2: Evaluation & Failure Injection Engineer
> **Mục tiêu:** Xây dựng bộ đề thi đánh giá RAG (Benchmark Test Set) và thiết lập kịch bản làm bẩn dữ liệu thực tế (Data Corruption Suite) để đo lường định lượng mức độ suy giảm chất lượng câu trả lời.

#### 1. File mã nguồn sở hữu độc quyền:
* `src/evaluation/testset.py`
* `src/ingestion/corruption.py`

#### 2. Công việc cần thực hiện:
* **Task 2.1 — Benchmark Test Set Builder (`src/evaluation/testset.py`):**
  - Hoàn thiện hàm `build_test_set(df: pd.DataFrame, output_path) -> list[dict]`:
  - Chọn các bài báo tiêu biểu từ `df` sạch để tạo ra đúng **10 câu hỏi benchmark**, bao phủ đủ **4 nhóm nghiệp vụ**:
    1. `summary`: Hỏi đóng góp/ý chính của bài báo `'{title}'`. Ground truth là câu đầu tiên (`first_sentence`) của summary.
    2. `authors`: Hỏi ai là tác giả bài báo `'{title}'`. Ground truth là `authors_joined`.
    3. `date`: Hỏi bài báo `'{title}'` xuất bản ngày nào. Ground truth là `published`.
    4. `categories`: Hỏi bài báo `'{title}'` thuộc chuyên mục nào. Ground truth là `categories_joined`.
  - Mỗi câu hỏi bao gồm đầy đủ cấu trúc: `id` (`q_01` -> `q_10`), `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` (danh sách `paper_id` chứa câu trả lời).
  - Lưu file ra `data/eval/test_set.json`.
* **Task 2.2 — Data Corruption Suite 6 Kịch Bản (`src/ingestion/corruption.py`):**
  - Hoàn thiện `corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame`:
  - Thực hiện trên bản sao của DataFrame sạch đủ **6 dạng lỗi thực tế**:
    1. **Drop latest records:** Xóa bỏ 20% bài báo mới nhất (mô phỏng mất dữ liệu gần nhất).
    2. **Blank summary:** Làm rỗng tóm tắt (`summary = ""`) ở 2-3 bài báo (mô phỏng lỗi parsing).
    3. **Inject noise:** Chèn chuỗi ký tự rác vào summary của 2 bài báo (mô phỏng nhiễu văn bản).
    4. **Truncate title:** Cắt ngắn tiêu đề xuống dưới 8 ký tự (vi phạm kiểm định GX).
    5. **Stale date:** Lùi ngày xuất bản về quá khứ xa (> 1000 ngày) để vi phạm Freshness SLA.
    6. **Duplicate rows:** Nhân bản 2 dòng bất kỳ để vi phạm tính duy nhất (`paper_id` uniqueness).
  - Tái tạo lại `text_for_embedding` trên các dòng bị ảnh hưởng.
  - Ghi toàn bộ thông tin chi tiết vào `data/results/corruption_log.json` (dạng lỗi, index dòng bị sửa, giá trị cũ/mới).
* **Task 2.3 — Kiểm thử đánh giá tính nhất quán của Test Set:**
  - Kiểm tra bộ câu hỏi khớp hoàn hảo với logic đánh giá trong `src/evaluation/metrics.py`.
  - Đảm bảo **bộ test set này được giữ nguyên cố định** khi chạy đánh giá qua cả 3 trạng thái (Baseline, Corrupted, Repaired).

#### 3. Lệnh tự kiểm chứng độc lập (Self-Verification):
```bash
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); cdf=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Tín hiệu hoàn thành: Corrupt xong {len(cdf)} dòng')"
```

#### 4. File báo cáo cá nhân:
* Hoàn thiện file `report/<MSSV2>_<HoTen2>.md` (dựa trên mẫu `report/individual_report.md`).

---

### 👤 THÀNH VIÊN 3 (Trưởng nhóm): Pipeline Orchestrator & Integration Lead
> **Mục tiêu:** Điều phối và lắp ráp chuỗi pipeline end-to-end, hiện thực hóa cơ chế tự phục hồi (Idempotent Repair), sinh báo cáo đối chiếu Markdown 3 trạng thái và chủ trì phần Live Demo trước lớp.

#### 1. File mã nguồn & tài liệu sở hữu độc quyền:
* `src/pipelines/phase1.py`
* `src/pipelines/corruption_flow.py`
* `src/observability/reporting.py`
* `report/group_report.md` & `docs/TEAM.md`

#### 2. Công việc cần thực hiện:
* **Task 3.1 — Tích hợp Pipeline Pha 1 Baseline (`src/pipelines/phase1.py`):**
  - Viết hàm `main()` điều phối luồng Baseline chạy qua entrypoint `python script/run_phase1.py`:
    1. Load cấu hình qua `load_settings()`.
    2. Gọi TV1 lấy raw records (`fetch_source_records` hoặc fallback `load_raw_records`).
    3. Gọi TV1 làm sạch dữ liệu (`build_clean_dataframe`) -> lưu `papers_clean.csv` và `papers_clean.json`.
    4. Xây dựng ChromaDB vector store collection `papers-baseline` qua `LocalEmbeddingIndex.build(...)`.
    5. Gọi TV2 sinh test set (`build_test_set`) -> lưu `data/eval/test_set.json`.
    6. Chạy `evaluate_pipeline(...)` -> xuất `baseline_metrics.json` và `baseline_answers.json`.
    7. Gọi TV1 chạy `run_data_quality_checks` và `build_freshness_report`.
    8. Gọi hàm tạo báo cáo `generate_phase1_report(...)` xuất ra `data/reports/phase1_report.md`.
* **Task 3.2 — Tích hợp Corruption Flow & Idempotent Repair (`src/pipelines/corruption_flow.py`):**
  - Viết hàm `main()` điều phối luồng chạy qua entrypoint `python script/run_corruption_flow.py`:
    1. Nạp baseline metrics và DataFrame sạch từ Pha 1.
    2. Gọi TV2 tạo corrupted data (`corrupt_clean_dataframe`) -> lưu `papers_clean_corrupted.csv/json`.
    3. Tạo ChromaDB collection `papers-corrupted` từ dữ liệu bẩn.
    4. Chạy `evaluate_pipeline` trên collection bẩn -> xuất `corrupted_metrics.json`.
    5. Chạy GX Quality Checks & Freshness trên dữ liệu bẩn -> chứng minh **Quality Gate cảnh báo FAIL**.
    6. **Kích hoạt Idempotent Repair:** Phục hồi dữ liệu từ bản snapshot thô ban đầu `data/raw/crossref_records.json`, chạy lại hàm làm sạch của TV1 `build_clean_dataframe` -> lưu `papers_clean_repaired.csv/json`.
    7. Tạo ChromaDB collection `papers-repaired` từ dữ liệu đã phục hồi.
    8. Chạy `evaluate_pipeline` trên collection đã phục hồi -> xuất `repaired_metrics.json`.
    9. Chạy GX Quality Checks trên dữ liệu phục hồi -> chứng minh **Quality Gate phục hồi PASS**.
    10. Gọi `generate_corruption_report` xuất báo cáo đối chiếu.
* **Task 3.3 — Xuất Báo Cáo Đối Chiếu Định Lượng (`src/observability/reporting.py`):**
  - Hoàn thiện `generate_phase1_report(...)` và `generate_corruption_report(...)`.
  - Báo cáo `data/reports/corruption_report.md` bắt buộc có bảng đối chiếu 3 cột:
    | Metric / Tín hiệu | Baseline | Corrupted | Repaired | Đánh giá & Phân tích nhân quả |
    | :--- | :---: | :---: | :---: | :--- |
    | `retrieval_hit_rate` | Cao (~1.0) | Sụt giảm | Phục hồi | Phản ánh việc mất tài liệu & nhiễu vector |
    | `mean_token_f1` | Chuẩn | Sụt giảm | Phục hồi | Phản ánh việc summary bị rỗng hoặc méo mó |
    | `judge_accuracy` | Cao | Thấp | Phục hồi | LLM phát hiện câu trả lời hallucinate |
    | GX Quality Gate | **PASS** | **FAIL** | **PASS** | Bắt đúng lỗi duplicate, null, length |
    | Freshness SLA | **FRESH** | **STALE** | **FRESH** | Bắt đúng lỗi bài báo quá hạn |
* **Task 3.4 — Hoàn thiện Báo Cáo Nhóm & Quản trị Git:**
  - Điền đầy đủ thông tin nhóm vào `docs/TEAM.md`.
  - Hoàn thiện báo cáo chung `report/group_report.md`.
  - Viết file báo cáo cá nhân `report/<MSSV3>_<HoTen3>.md`.
  - Kiểm tra tab **Insights → Contributors** trên GitHub đảm bảo 100% (cả 3 người) đều có commit trên nhánh `main`.
* **Task 3.5 — Chủ trì Live Demo (CP6):**
  - Chuẩn bị terminal trình diễn chạy trực tiếp `run_phase1.py` và `run_corruption_flow.py` trên bảng trước Giảng viên và lớp.

#### 3. Lệnh tự kiểm chứng độc lập (Self-Verification):
```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```
Cả hai script phải chạy thành công với `exit code 0`, sinh ra đầy đủ các file báo cáo markdown và JSON metrics.

---

## IV. QUY TRÌNH PHỐI HỢP & CHIẾN LƯỢC GIT (TIMELINE 240 PHÚT)

### 1. Phân nhánh Git:
* Mỗi thành viên tạo nhánh riêng của mình từ `main`:
  - Thành viên 1: `feat/tv1-data-foundation`
  - Thành viên 2: `feat/tv2-eval-corruption`
  - Thành viên 3: `feat/tv3-pipeline-orchestration`

### 2. 4 Mốc Phối Hợp Theo Thời Gian:

* ⏱️ **Mốc 1 (0 – 65 phút): Phát triển độc lập từng module**
  - **TV1:** Hoàn thiện `crossref.py`, `cleaning.py`, `quality.py`. Chạy lệnh self-test in ra `Đã tải 24 bài báo`, `Clean thành công 24 dòng`.
  - **TV2:** Đọc `data/clean/papers_clean.json` (tạm thời lấy từ snapshot test) để viết `testset.py` (10 câu hỏi) và viết `corruption.py` (6 lỗi).
  - **TV3:** Cấu hình `.env`, kiểm tra môi trường, đọc hiểu `retrieval/index.py` và `retrieval/agent.py`, chuẩn bị khung sườn cho `phase1.py` và `reporting.py`.

* ⏱️ **Mốc 2 (65 – 120 phút): Tích hợp Baseline (Pha 1)**
  - TV1 và TV2 tạo Pull Request vào `main`. (Cả 2 thành viên đã có commit trên `main`!).
  - TV3 pull code mới nhất về nhánh của mình, ghép các module vào `src/pipelines/phase1.py` và viết `generate_phase1_report`.
  - Chạy thử nghiệm: `python script/run_phase1.py`.
  - Kiểm tra các artifact sinh ra: `papers_clean.csv`, `papers_clean.json`, `test_set.json`, `baseline_metrics.json`, `phase1_report.md`.

* ⏱️ **Mốc 3 (120 – 180 phút): Tích hợp Corruption Flow & Idempotent Repair**
  - TV3 hoàn thiện `src/pipelines/corruption_flow.py` và `generate_corruption_report`.
  - Chạy thực thi: `python script/run_corruption_flow.py`.
  - Cả nhóm kiểm tra kết quả bảng so sánh 3 trạng thái: đảm bảo các chỉ số giảm rõ rệt ở Corrupted và phục hồi lại ở Repaired.
  - TV3 tạo Pull Request merge vào `main`.

* ⏱️ **Mốc 4 (180 – 240 phút): Viết Báo Cáo, Live Demo & Nộp LMS**
  - Cả 3 thành viên: mỗi người tự hoàn thành file `report/<MSSV>_<HoTen>.md` của mình và commit lên nhánh `main`.
  - TV3 hoàn thiện `report/group_report.md` và `docs/TEAM.md`.
  - Cả nhóm chuẩn bị nội dung Live Demo (3-5 phút).
  - **⏰ TRƯỚC 23:59:59:** Từng cá nhân (cả 3 người) dùng tài khoản cá nhân nộp đường link GitHub repo lên VLearn LMS!

---

## V. CHECKLIST TRÁNH BỊ TRỪ ĐIỂM THEO RUBRIC

| Hạng mục | Mức phạt nếu vi phạm | Cách phòng tránh | Thành viên phụ trách |
| :--- | :---: | :--- | :--- |
| **Lộ API Key / Token** | **-20đ (hoặc 0đ)** | Tuyệt đối không commit file `.env`, chỉ dùng `.env.example` | Cả nhóm |
| **Hardcode đường dẫn** | **-5đ** | Không dùng đường dẫn tuyệt đối kiểu `C:\...` hay `D:\...`, dùng `Path` từ `core/config.py` | Cả nhóm |
| **Sai chuẩn GX 1.x** | **-10đ** | Dùng đúng cú pháp `gx.get_context(mode="ephemeral")` (không dùng cú pháp cũ) | Thành viên 1 |
| **Thiếu commit trên main** | **0đ cá nhân** | Kiểm tra tab **Insights → Contributors** trên GitHub: cả 3 người đều phải có commit trên `main` | Cả nhóm / TV3 |
| **Thiếu báo cáo cá nhân** | **-5đ / người** | Mỗi thành viên nộp đúng file `report/<MSSV>_<HoTen>.md` | Từng cá nhân |
| **Nộp bài lên LMS** | **0đ cá nhân** | Mỗi người **tự nộp link repo** từ tài khoản VLearn cá nhân trước **23:59:59** | Từng cá nhân |
