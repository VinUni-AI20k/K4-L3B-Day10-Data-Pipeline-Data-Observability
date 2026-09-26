# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Team 03 - DataObservability`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-Team03-DataPipelineDataObservability`
- **Ngày Hoàn Thành:** `2026-09-26`

---

## 1. Bảng Phân Công Vai Trò Thành Viên (Nhóm 4 Thành Viên)

| STT | Họ và tên | MSSV | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|
| 1 | Đặng Thái Anh | 2A202602740 | **Trưởng nhóm / Data Foundation, Ingestion & Idempotent Recovery**<br>- Xây dựng module thu thập Crossref API với cơ chế local fallback snapshot tại `src/ingestion/crossref.py`.<br>- Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` (cấu trúc 5 phần) trong `src/ingestion/cleaning.py`.<br>- Thiết kế 6 kịch bản tiêm lỗi dữ liệu tổng hợp (Synthetic Data Corruption Suite) trong `src/ingestion/corruption.py`.<br>- Triển khai logic Idempotent Repair khôi phục 100% dữ liệu gốc bất biến từ raw records. | `report/2A202602740_DangThaiAnh.md` |
| 2 | Nguyễn Đức Anh | 2A202602888 | **Pipeline Integrator & Data Orchestration**<br>- Thiết lập kiến trúc tổng thể, môi trường ảo & cấu hình `core/config.py`, `core/utils.py`.<br>- Tích hợp và điều phối luồng thực thi trong `src/pipelines/phase1.py` & `src/pipelines/corruption_flow.py`.<br>- Xây dựng entrypoints thực thi `script/run_phase1.py`, `script/run_corruption_flow.py`.<br>- Triển khai cơ chế tự động hóa phục hồi Self-Healing & Pytest CI. | `report/2A202602888_NguyenDucAnh.md` |
| 3 | Đỗ Trung Tuyến | 2A202602427 | **RAG Agent & Vector Index Architecture**<br>- Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2` và chuẩn hóa vector cosine similarity.<br>- Thiết lập và cô lập 3 collection độc lập trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`).<br>- Xây dựng cơ chế Multi-Provider LLM Router (`gemini`, `openai`, `mock`) trong `src/retrieval/llm.py`.<br>- Xây dựng Retrieval Agent và hàm trích xuất câu trả lời chuẩn xác ngữ cảnh trong `src/retrieval/qa.py` và `src/retrieval/agent.py`. | `report/2A202602427_DoTrungTuyen.md` |
| 4 | Nguyễn Khánh Duy | 2A202602403 | **Data Observability, Freshness SLA & Benchmark Evaluation**<br>- Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** (ephemeral context) với 7 expectations bắt buộc.<br>- Giám sát Freshness SLA (ngưỡng 180 ngày, cảnh báo khi tỷ lệ quá hạn > 25%) trong `src/observability/quality.py`.<br>- Xây dựng bộ test benchmark 10 câu hỏi chuẩn hóa qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`) trong `src/evaluation/testset.py`.<br>- Đo lường metrics Hit Rate, Token F1, LLM Judge Score và thiết kế Interactive HTML Observability Dashboard. | `report/2A202602403_NguyenKhanhDuy.md` |

---

## 2. Phần Tự Khai Báo Đóng Góp Chi Tiết Từng Cá Nhân

### 2.1. Đặng Thái Anh - 2A202602740
- **Vai trò:** Trưởng nhóm & Data Foundation, Ingestion & Idempotent Recovery.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref REST API với cơ chế local fallback snapshot tại `src/ingestion/crossref.py`, đảm bảo pipeline vẫn chạy mượt mà ngay cả khi mất mạng hoặc dính `429 Too Many Requests`.
  - Triển khai thuật toán trích xuất dữ liệu, làm sạch thẻ XML/JATS, chuẩn hóa khoảng trắng và tính toán chỉ số `age_days` chuẩn hóa timezone tại `src/ingestion/cleaning.py`.
  - Thiết kế cấu trúc `text_for_embedding` gồm 5 phần chuẩn mực (Title, Authors, Categories, Published, Summary) phục vụ embedding vector tối ưu.
  - Xây dựng bộ công cụ tiêm lỗi tổng hợp (Synthetic Corruption Suite) gồm 6 kịch bản thực tế: mất dữ liệu mới, rỗng tóm tắt, nhiễu văn bản, cắt ngắn tiêu đề, ngày xuất bản lỗi thời, và nhân bản bản ghi trùng lặp.
  - Kiểm chứng và hoàn thiện thuật toán Idempotent Repair: nạp lại từ snapshot bất biến `data/raw/crossref_records.json`, tái tạo trạng thái sạch hoàn hảo 24 bản ghi mà không để lại tác dụng phụ.
- **Điều học được / Đóng góp chính:**
  - Hiểu rõ tầm quan trọng của Data Lineage và nguyên tắc bảo toàn dữ liệu gốc (Raw Immutability).
  - Nhận thức rõ ràng về hiện tượng Silent Failure: dữ liệu suy thoái không làm sập ứng dụng mà âm thầm phá hủy độ chính xác của AI.

### 2.2. Nguyễn Đức Anh - 2A202602888
- **Vai trò:** Pipeline Integrator & Data Orchestration.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết kế kiến trúc tổng thể của hệ thống pipeline theo chuẩn Idempotent Pipeline Design.
  - Quản lý cấu hình tập trung trong `src/core/config.py` và các hàm tiện ích I/O trong `src/core/utils.py`.
  - Kết nối luồng thực thi end-to-end cho Pha 1 (`src/pipelines/phase1.py`) và luồng kiểm chứng suy thoái (`src/pipelines/corruption_flow.py`).
  - Xử lý tương thích mã hóa UTF-8 trên Windows PowerShell/CMD để ngăn chặn lỗi mã hóa `charmap` (`UnicodeEncodeError`).
  - Xây dựng module tự động phát hiện lỗi và kích hoạt cơ chế tự phục hồi (Automated Self-Healing Controller) trong `src/observability/self_healing.py`.
  - Thiết lập bộ kiểm thử toàn diện `tests/test_pipeline.py` và cấu hình GitHub Actions CI `.github/workflows/ci.yml`.
- **Điều học được / Đóng góp chính:**
  - Nắm vững nguyên tắc thiết kế Data Pipeline có khả năng phục hồi (Resilient Data Engineering).
  - Hiểu sâu sắc cách phối hợp giữa tầng lưu trữ dữ liệu thô (Raw Layer), tầng xử lý (Clean Layer), và tầng truy xuất ngữ nghĩa (Serving/Vector Layer).

### 2.3. Đỗ Trung Tuyến - 2A202602427
- **Vai trò:** RAG Agent & Vector Index Architecture.
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý mô hình sentence-transformers `all-MiniLM-L6-v2`, tối ưu hóa embedding văn bản 384 chiều với cosine distance.
  - Thiết lập và quản lý vòng đời của 3 ChromaDB collections độc lập (`papers-baseline`, `papers-corrupted`, `papers-repaired`), giải quyết triệt để vấn đề xung đột vector và rò rỉ bộ đệm HNSW.
  - Xây dựng cơ chế Multi-Provider LLM trong `src/retrieval/llm.py`, hỗ trợ chuyển đổi linh hoạt giữa Gemini, OpenAI, Anthropic và Fake LLM Mock cho môi trường CI.
  - Cấu hình Agentic QA Router kết hợp semantic search và exact lookup theo title trong `src/retrieval/qa.py` và `src/retrieval/agent.py`.
- **Điều học được / Đóng góp chính:**
  - Nắm vững kỹ thuật Vector Space Isolation để so sánh khách quan giữa dữ liệu sạch và dữ liệu bị suy thoái.
  - Hiểu cách tối ưu hóa cấu trúc văn bản nhúng giúp cải thiện vượt bậc Retrieval Hit Rate.

### 2.4. Nguyễn Khánh Duy - 2A202602403
- **Vai trò:** Data Observability, Freshness SLA & Benchmark Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Triển khai Data Quality Gate trên nền tảng **Great Expectations 1.x** với Ephemeral Context trong `src/observability/quality.py`, định nghĩa 7 expectations bắt buộc (Row count, Not Null, Unique paper_id, Value length).
  - Tích hợp chốt kiểm soát Freshness SLA (ngưỡng 180 ngày, kích hoạt cảnh báo đỏ khi tỷ lệ quá hạn vượt quá 25%).
  - Thiết kế bộ test benchmark 10 câu hỏi cân bằng trên 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`) tại `src/evaluation/testset.py`.
  - Đo lường và phân tích các chỉ số định lượng: Retrieval Hit Rate, Mean Token F1, LLM Judge Score tại `src/evaluation/metrics.py`.
  - Thiết kế báo cáo tổng hợp Markdown và Interactive HTML Observability Dashboard (`report/observability_dashboard.html`).
- **Điều học được / Đóng góp chính:**
  - Nắm vững công nghệ Data Observability hiện đại (Great Expectations 1.x) và quy trình kiểm thử đánh giá hệ thống RAG chuẩn mực.
  - Hiểu sâu sắc cách thiết lập chốt kiểm dịch để chặn đứng hiện tượng Silent Failure trước khi dữ liệu đi vào tầng phục vụ người dùng.
