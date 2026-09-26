# Group Report — Day 10: Data Pipeline & Data Observability
## Dự án: Data Pipeline & Data Observability for Scholarly RAG Agent

---

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| :--- | :--- |
| **Khóa / Lớp** | K4 / L3B (Ca Sáng) |
| **Tên nhóm** | Team VN |
| **Repository** | `https://github.com/haikunn11/K4-L3B-Day10-TeamVN-DataPipelineDataObservability` |
| **Ngày hoàn thành** | 2026-09-26 |

### Thành viên và phân công công việc

| STT | Họ và tên | MSSV | Vai trò chính | Module / deliverable sở hữu |
| --: | :--- | :---: | :--- | :--- |
| 1 | **Phạm Đình Hải** | 2A202602482 | Data Foundation & Quality Engineer | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/observability/quality.py`, `report/2A202602482_PhamDinhHai.md` |
| 2 | **Nguyễn Minh Ngọc** | 2A202602530 | Evaluation & Failure Injection Engineer | `src/evaluation/testset.py`, `src/ingestion/corruption.py`, `tests/test_member2.py`, `report/individual_2A202602530_NguyenMinhNgoc.md` |
| 3 | **Vũ Huy Đỗ** *(Lead)* | 2A202602555 | Pipeline Orchestrator & Integration Lead | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/observability/reporting.py`, `docs/TEAM.md`, `report/group_report.md`, `report/2A202602555_VuHuyDo.md` |

---

## 2. Tóm tắt kết quả (Executive Summary)

Nhóm **Team VN** đã hoàn thành 100% các mục tiêu từ Checkpoint CP0 đến CP6 của bài Lab Day 10:
- **Baseline Pipeline (Phase 1):** Xây dựng thành công chu trình khép kín từ thu thập Crossref Metadata API (24 bài báo khoa học), làm sạch văn bản, chuẩn hóa cấu trúc 5 phần `text_for_embedding`, đến lưu trữ vector tại ChromaDB (`papers-baseline`). Trên bộ benchmark 10 câu hỏi chuẩn hóa, hệ thống đạt **Retrieval Hit Rate: 100.00%**, **Mean Token F1: 1.0000**, và **Judge Accuracy: 100.00%**.
- **Data Observability:** Thiết lập Quality Gate tự động theo chuẩn mới nhất **Great Expectations 1.x** (Ephemeral Context với 4 Expectations thiết yếu) và giám sát **Freshness SLA** (ngưỡng 180 ngày). Dữ liệu Baseline đạt trạng thái **PASS** và **FRESH** (tỷ lệ quá hạn chỉ 4.17%).
- **Data Corruption & Silent Failure (Phase 2):** Giả lập thành công 6 kịch bản suy giảm dữ liệu thực tế (mất 20% bài báo mới nhất, xóa rỗng summary, chèn chuỗi ký tự rác, cắt ngắn tiêu đề, lùi ngày xuất bản > 730 ngày, nhân bản dòng). Kết quả làm bộc lộ hiện tượng **Silent Failure**: RAG Agent không crash nhưng hiệu năng suy giảm nghiêm trọng (**Hit Rate giảm còn 80.00%**, **Token F1 giảm còn 0.6000**, **Judge Accuracy giảm còn 60.00%**). Data Observability bắt chính xác các lỗi này: GX báo **FAIL** và Freshness báo **STALE** (47.62% > 25%).
- **Idempotent Self-Healing / Repair:** Kích hoạt cơ chế tự phục hồi từ nguồn raw snapshot bất biến `data/raw/crossref_records.json`, tái tạo index `papers-repaired`. Toàn bộ chỉ số RAG và Quality Gate phục hồi **100% nguyên trạng** so với Baseline.

---

## 3. Kiến trúc và luồng dữ liệu

### Sơ đồ Luồng End-to-End

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES & INGESTION                        │
│   Crossref REST API ────► Offline Raw Snapshot (crossref_records.json)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        CLEANING & DATA MODELING                        │
│   - Khử trùng lặp paper_id                                             │
│   - Xóa bỏ JATS XML tags & chuẩn hóa Unicode                           │
│   - Tính age_days (UTC)                                                │
│   - Cấu trúc text_for_embedding 5 phần                                 │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
┌─────────────────────────────────────┐  ┌───────────────────────────────┐
│         DATA OBSERVABILITY          │  │     VECTOR DB & RETRIEVAL     │
│ - Great Expectations 1.x (Ephemeral)│  │ - MiniLM all-MiniLM-L6-v2     │
│ - Freshness SLA Monitoring          │  │ - ChromaDB Collection         │
└───────────────────┬─────────────────┘  └───────────────┬───────────────┘
                    │                                    │
                    ▼                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     EVALUATION & FAILURE SIMULATION                    │
│   - Benchmark Test Set (10 questions, 4 business groups)               │
│   - 6 Synthetic Corruption Scenarios (Drop, Blank, Noise, Dup, ...)   │
│   - 3-State Measurement: BASELINE vs CORRUPTED vs REPAIRED             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      IDEMPOTENT REPAIR & REPORTING                     │
│   - Self-healing từ Raw Snapshot bất biến                              │
│   - Markdown Reports: phase1_report.md & corruption_report.md          │
└────────────────────────────────────────────────────────────────────────┘
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output / Artifact | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Crossref REST API / Snapshot local | Fetch API có retry/fallback, trích xuất metadata chuẩn | `crossref_response.json`<br>`crossref_records.json` | Phạm Đình Hải (TV1) |
| **Cleaning** | List `PaperRecord` | Strip JATS XML, dedup `paper_id`, tính `age_days`, tạo `text_for_embedding` | `papers_clean.csv`<br>`papers_clean.json` | Phạm Đình Hải (TV1) |
| **Vector DB** | Clean DataFrame | Embed văn bản MiniLM-L6-v2, quản lý ChromaDB collections | `data/chroma/`<br>`papers_embeddings.json` | Vũ Huy Đỗ (TV3) |
| **Evaluation** | Clean DataFrame | Sinh đề thi 10 câu qua 4 nhóm (`summary`, `authors`, `date`, `categories`) | `data/eval/test_set.json` | Nguyễn Minh Ngọc (TV2) |
| **Observability** | DataFrame (sạch/bẩn/phục hồi) | Chạy 4 Expectations GX 1.x Ephemeral & Freshness SLA 180 ngày | `*_quality_report.json`<br>`freshness_report.json` | Phạm Đình Hải (TV1) |
| **Corruption** | Clean DataFrame | Tiêm 6 dạng lỗi dữ liệu thực tế và xuất log kiểm toán | `papers_clean_corrupted.json`<br>`corruption_log.json` | Nguyễn Minh Ngọc (TV2) |
| **Orchestration** | Toàn bộ các module | Điều phối Phase 1, Corruption Flow, Idempotent Repair & sinh báo cáo so sánh | `phase1.py`, `corruption_flow.py`<br>`phase1_report.md`, `corruption_report.md` | Vũ Huy Đỗ (TV3) |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến / Cấu hình | Giá trị sử dụng |
| :--- | :--- |
| `LLM_PROVIDER` | `gemini` (hỗ trợ graceful heuristic judge fallback khi không có API key) |
| `LLM_MODEL` | `gemini-2.5-flash` |
| `Embedding Model` | `sentence-transformers/all-MiniLM-L6-v2` (384 chiều) |
| `Số lượng Crossref Records` | `24` bản ghi |
| `Retrieval top_k` | `4` documents |
| `Freshness Threshold` | `180` ngày |
| `Freshness Stale Ratio Max` | `25%` |

### Lệnh cài đặt

```bash
pip install -e .
```

### Lệnh chạy thực thi

- **Chạy Pha 1 (Baseline Pipeline):**
  ```bash
  python script/run_phase1.py
  ```
- **Chạy Pha 2 (Corruption Flow, Silent Failure & Idempotent Repair):**
  ```bash
  python script/run_corruption_flow.py
  ```
- **Chạy toàn bộ Unit Tests kiểm định:**
  ```bash
  pytest
  ```

### Kết quả tái hiện thực tế

| Lệnh | Trạng thái | Thời điểm chạy | Bằng chứng |
| :--- | :---: | :---: | :--- |
| `python script/run_phase1.py` | **Thành công (Exit 0)** | 2026-09-26 11:16 | Sinh đầy đủ `papers_clean.csv`, `papers-baseline`, `baseline_metrics.json`, `phase1_report.md` |
| `python script/run_corruption_flow.py` | **Thành công (Exit 0)** | 2026-09-26 11:17 | Sinh `corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` |
| `pytest` | **18/18 Tests PASSED** | 2026-09-26 11:20 | 15 tests thành viên 2 + 3 tests tích hợp thành viên 3 |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Nguồn API** | Crossref REST API (`https://api.crossref.org/works`) |
| **Query** | `agentic retrieval augmented generation large language model` |
| **Filter** | `from-pub-date:2026-03-30,has-abstract:true` |
| **Số records nhận được** | 24 bài báo khoa học |
| **Cơ chế Fallback & Lineage** | Khi mất kết nối hoặc gặp HTTP 429/503, tự động đọc từ snapshot `data/raw/crossref_records.json` |

### Schema dữ liệu sạch (Data Contract)

| Trường | Kiểu dữ liệu | Bắt buộc | Ý nghĩa nghiệp vụ | Xử lý khi thiếu / sai |
| :--- | :--- | :---: | :--- | :--- |
| `paper_id` | `str` | Có | DOI định danh duy nhất của bài báo | Bỏ qua bản ghi nếu thiếu; khử trùng lặp |
| `title` | `str` | Có | Tiêu đề bài báo khoa học | Strip XML tags; GX chặn nếu độ dài < 8 |
| `summary` | `str` | Có | Tóm tắt bài báo (Abstract) | Strip XML tags; GX chặn nếu độ dài < 20 |
| `authors_joined` | `str` | Có | Danh sách tác giả nối bằng dấu phẩy | Ghép từ mảng authors; gán rỗng nếu thiếu |
| `categories_joined` | `str` | Có | Chuyên mục nối bằng dấu phẩy | Ghép từ mảng categories |
| `published` | `str` | Có | Ngày xuất bản định dạng ISO `YYYY-MM-DD` | Chuẩn hóa date-parts; kiểm tra định dạng ISO |
| `age_days` | `int` | Có | Số ngày tuổi tính từ ngày chạy chuẩn UTC | `(run_date - published).days` |
| `text_for_embedding`| `str` | Có | Văn bản nhúng chuẩn hóa 5 phần | Ghép Title, Authors, Published, Categories, Summary |

---

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| :--- | :--- |
| **Số câu hỏi benchmark** | 10 câu hỏi (`q_01` -> `q_10`) |
| **Các nhóm nghiệp vụ** | 4 nhóm: `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu) |
| **Ground-truth Mapping** | Mỗi câu hỏi gắn liền với `ground_truth_doc_ids` (chứa `paper_id` gốc) |
| **Embedding Model** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector Store** | ChromaDB Persistent Client với cosine space |
| **Retrieval Top-K** | `top_k = 4` |
| **Tính bất biến của Test Set** | **Bộ test set được sinh 1 lần duy nhất từ Baseline và giữ nguyên cố định** khi đánh giá xuyên suốt 3 trạng thái. Điều này đảm bảo tính khách quan và so sánh công bằng. |

---

## 7. Kết quả Baseline (Pha 1)

### Baseline Artifact Checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| :--- | :--- | :---: | :--- |
| Raw snapshot | `data/raw/crossref_records.json` | **Có** | 24 bản ghi gốc |
| Cleaned dataset | `data/clean/papers_clean.csv`, `.json` | **Có** | 24 dòng sạch hoàn toàn |
| Vector collection | `data/chroma/` (collection `papers-baseline`) | **Có** | ChromaDB persistent |
| Benchmark test set | `data/eval/test_set.json` | **Có** | 10 câu hỏi 4 nhóm |
| Baseline metrics | `data/results/baseline_metrics.json` | **Có** | Điểm số chuẩn mực |
| Quality & Freshness | `data/quality/baseline_quality_report.json` | **Có** | GX 1.x PASS, Freshness FRESH |
| Baseline report | `data/reports/phase1_report.md` | **Có** | Báo cáo Markdown chi tiết |

### Baseline Metrics

| Metric | Giá trị Baseline | Diễn giải |
| :--- | :---: | :--- |
| `retrieval_hit_rate` | **100.00%** | Toàn bộ 10/10 câu hỏi đều truy xuất trúng tài liệu mục tiêu trong top-4 |
| `mean_token_f1` | **1.0000** | Độ trùng khớp n-gram hoàn hảo giữa câu trả lời và ground truth |
| `judge_accuracy` | **100.00%** | Toàn bộ câu trả lời được đánh giá chính xác |
| `mean_judge_score` | **5.00 / 5.0** | Điểm số đánh giá tối đa |

---

## 8. Data Observability: Great Expectations 1.x & Freshness SLA

### Great Expectations 1.x (4 Expectations thiết yếu)

| Check | Quality Dimension | Ngưỡng / Kỳ vọng | Kết quả Baseline | Bằng chứng |
| :--- | :--- | :--- | :---: | :--- |
| `ExpectTableRowCountToBeBetween` | Completeness | min=15, max=50 | **PASS** (24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` | Completeness | `paper_id`, `title`, `text_for_embedding` | **PASS** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` | Uniqueness | `paper_id` | **PASS** (0 trùng lặp) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween`| Validity | `title` >= 8, `summary` >= 20 | **PASS** (100% hợp lệ)| `baseline_quality_report.json` |

### Freshness SLA

| Thuộc tính | Giá trị Baseline |
| :--- | :--- |
| **Phạm vi đo** | Đo trực tiếp trên cột `age_days` của Cleaned DataFrame |
| **Ngưỡng quy định** | `180` ngày (bài báo có `age_days > 180` bị coi là stale) |
| **Tỷ lệ bài báo quá hạn** | **4.17%** (1/24 bài báo) |
| **Ngưỡng cho phép tối đa** | `<= 25%` |
| **Trạng thái Freshness** | **FRESH** |

---

## 9. Data Corruption Scenarios & Idempotent Repair

### 6 Kịch bản Tiêm lỗi Dữ liệu

| Kịch bản Corruption | Cách tạo | Số record bị ảnh hưởng | Tín hiệu phát hiện của Observability | Tác động thực tế tới RAG |
| :--- | :--- | :---: | :--- | :--- |
| **1. Drop latest records** | Xóa 20% bài báo mới nhất | 5 bản ghi | `ExpectTableRowCountToBeBetween` (giảm dòng) | Trực tiếp gây trượt `retrieval_hit_rate` với câu hỏi về bài báo bị xóa |
| **2. Blank summary** | Gán `summary = ""` | 4 bản ghi | `ExpectColumnValueLengthsToBeBetween` (summary < 20) | Làm rỗng câu trả lời dạng summary, giảm mạnh Token F1 |
| **3. Inject noise** | Chèn chuỗi rác vào đầu summary | 4 bản ghi | Phá vỡ phân phối từ vựng văn bản | Làm nhiễu không gian vector cosine, giảm độ tương đồng truy xuất |
| **4. Truncate title** | Cắt ngắn tiêu đề < 8 ký tự | 4 bản ghi | `ExpectColumnValueLengthsToBeBetween` (title < 8) | Gây trượt lookup tiêu đề chính xác |
| **5. Stale date** | Lùi ngày xuất bản thêm 730 ngày | 8 bản ghi | Freshness SLA: stale ratio nhảy lên 47.62% (> 25%) | Gắn cờ cảnh báo **STALE** toàn bộ dữ liệu |
| **6. Duplicate rows** | Nhân bản 10% số dòng còn lại | 2 bản ghi | `ExpectColumnValuesToBeUnique` (trùng paper_id) | Gây ô nhiễm vector store và lãng phí index |

### Cơ chế Idempotent Self-Healing / Repair

- **Khái niệm Idempotent Repair:** Phục hồi dữ liệu theo nguyên tắc toán học: $f(f(x)) = f(x)$. Cho dù pipeline phục hồi được gọi bao nhiêu lần, trên bất kỳ trạng thái dữ liệu hư hại nào, kết quả đầu ra luôn là một tập dữ liệu sạch duy nhất, đồng nhất và chuẩn hóa 100%.
- **Quy trình thực thi:**
  1. Không sửa chắp vá (patching) trên DataFrame lỗi vì dễ gây ô nhiễm chéo và mất Data Lineage.
  2. Nạp lại dữ liệu thô nguyên bản từ `data/raw/crossref_records.json`.
  3. Tái áp dụng toàn bộ pipeline làm sạch chuẩn `build_clean_dataframe`.
  4. Tái tạo collection ChromaDB `papers-repaired`.
  5. Đánh giá kiểm thử và giám sát lại: đảm bảo phục hồi nguyên vẹn các chỉ số.

---

## 10. Bảng đối chiếu 3 trạng thái: Baseline vs Corrupted vs Repaired

| Metric / Tín hiệu kiểm định | Baseline | Corrupted | Repaired | Thay đổi do Corruption | Mức độ Phục hồi | Đánh giá & Phân tích nhân quả |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | **100.00%** | **80.00%** | **100.00%** | `-20.00%` | **100% phục hồi** | Sụt giảm do 20% bài báo mới nhất bị xóa khỏi corpus; phục hồi hoàn toàn sau repair |
| **Mean Token F1** | **1.0000** | **0.6000** | **1.0000** | `-0.4000` | **100% phục hồi** | Sụt giảm do summary bị xóa rỗng hoặc chèn chuỗi rác; phục hồi nguyên vẹn sau clean lại |
| **Judge Accuracy** | **100.00%** | **60.00%** | **100.00%** | `-40.00%` | **100% phục hồi** | LLM Judge phát hiện câu trả lời hallucinate / thiếu căn cứ khi context bị hỏng |
| **Mean Judge Score** | **5.00 / 5.0** | **3.40 / 5.0** | **5.00 / 5.0** | `-1.60` | **5.00 / 5.0** | Phản ánh trực quan chất lượng câu trả lời bị tụt dốc và lấy lại phong độ |
| **GX Quality Gate** | **PASS** | **FAIL** | **PASS** | `PASS -> FAIL` | **PASS (100%)** | GX bắt trúng 100% các vi phạm độ dài chuỗi, tính duy nhất và schema |
| **Freshness SLA** | **FRESH** | **STALE** | **FRESH** | `FRESH -> STALE` | **FRESH (100%)** | Bắt trúng lỗi bài báo quá hạn khi stale ratio vọt lên 47.62% |

### Hai Kết luận Nhân quả Vững chắc

1. **Quan hệ Nhân quả 1 (Dữ liệu bẩn dẫn tới Silent Failure):**
   Khi tiêm lỗi xóa 20% bài báo và làm rỗng summary, Vector Database và RAG Agent **hoàn toàn không crash hay văng lỗi runtime**. Tuy nhiên, chất lượng thực tế suy giảm nghiêm trọng: Retrieval Hit Rate rơi từ 100% xuống 80%, Token F1 giảm 40% (xuống 0.6000). Đây là minh chứng thực tế rõ ràng nhất cho hiểm họa **Silent Failure** trong kiến trúc RAG nếu không có Data Observability giám sát.
2. **Quan hệ Nhân quả 2 (Idempotent Repair phục hồi chất lượng):**
   Khi kích hoạt cơ chế Idempotent Repair tái tạo từ raw snapshot bất biến `crossref_records.json`, Quality Gate GX chuyển ngay lập tức từ **FAIL** về **PASS**, Freshness chuyển từ **STALE** về **FRESH**, và hiệu năng RAG Agent phục hồi 100% về mức Baseline ban đầu (Hit Rate 100%, F1 1.0000). Điều này khẳng định tính đúng đắn của việc phục hồi theo Data Lineage thay vì chắp vá dữ liệu cục bộ.

---

## 11. Vấn đề tích hợp quan trọng (Integration Challenge)

- **Triệu chứng:** Khi chạy tích hợp end-to-end trên môi trường Python hệ thống, các module phụ thuộc tùy chọn (`langchain-anthropic`, `langchain-ollama`) có thể gây ra `ModuleNotFoundError` ở tầng import nếu người dùng cấu hình provider khác.
- **Nguyên nhân:** Khối `src/retrieval/llm.py` import tĩnh toàn bộ các router nhà cung cấp ở đầu file, khiến tiến trình bị gián đoạn ngay cả khi người dùng chỉ sử dụng Gemini hoặc Mock.
- **Cách xử lý:** Đã hoàn thiện cài đặt đầy đủ các gói thư viện chuẩn trong môi trường dự án và tối ưu hóa luồng gọi `load_settings()`, đảm bảo tính tương thích đa nền tảng và cách ly lỗi an toàn.
- **Cách xác minh:** Cả hai script `python script/run_phase1.py` và `python script/run_corruption_flow.py` đều thực thi trơn tru với `exit code 0`, sinh ra đầy đủ các artifact và báo cáo markdown.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng thực tế | Hướng cải thiện có thể kiểm chứng |
| :--- | :--- | :--- |
| **Corpus quy mô nhỏ (24 bài báo)** | Chưa đo lường được chi phí indexing và độ trễ truy xuất ở quy mô hàng triệu bản ghi | Mở rộng ingestion phân trang (pagination) lên 10,000+ bài báo và áp dụng HNSW indexing nâng cao |
| **Đánh giá Ragas cần GPU/API Key** | Quá trình tính Faithfulness/Relevancy qua Ragas bị bỏ qua khi không có API Key trực tiếp | Tích hợp local Ollama LLM (ví dụ: `qwen2.5` hoặc `llama3.1`) để tự động chạy Ragas pass 100% offline |
| **Cơ chế Repair phụ thuộc Snapshot** | Nếu snapshot ban đầu cũng bị lỗi từ nguồn thì cần fetch lại từ API | Bổ sung cơ chế Multi-tier Ingestion Fallback kết hợp kiểm định mã băm SHA-256 nguồn |

---

## 13. Checklist trước khi nộp bài

- [x] Thông tin nhóm và repository chính xác (`Team VN` - `haikunn11/K4-L3B-Day10-TeamVN-DataPipelineDataObservability`).
- [x] Phân công khớp chính xác với module, artifact và kết quả thực tế trong `PHAN_CONG_NHOM.md` và `docs/TEAM.md`.
- [x] Lệnh tái hiện đã được chạy lại thành công trên máy: `run_phase1.py` và `run_corruption_flow.py` đều exit code 0.
- [x] Baseline, Corrupted và Repaired dùng chung một bộ Benchmark 10 câu hỏi cố định trong `data/eval/test_set.json`.
- [x] Bảng metrics khớp chính xác với các file trong `data/results/` (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`).
- [x] Kết luận Quality và Freshness khớp chính xác với các file trong `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact đều truy cập được và hiển thị đẹp mắt.
- [x] Cả 3 thành viên đã hoàn thành báo cáo cá nhân riêng biệt (`PhamDinhHai.md`, `NguyenMinhNgoc.md`, `VuHuyDo.md`).
- [x] Tuyệt đối không chứa API Key, Token hay mật khẩu bí mật trong mã nguồn, báo cáo hay file log.
