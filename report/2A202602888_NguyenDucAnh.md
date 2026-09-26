# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Đức Anh            |
| MSSV               | 2A202602888               |
| Khóa/Lớp         | K4 - Lớp B (Ca Sáng)      |
| Tên nhóm         | Team 03 - DataObservability |
| Vai trò chính    | Trưởng nhóm / Pipeline Integrator & Data Orchestration |
| Repository         | K4-L3B-DAY10-Team03-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| Cấu hình hệ thống & đường dẫn artifacts | `src/core/config.py`, `src/core/utils.py` | Biến môi trường `.env`, cấu hình mặc định | Đối tượng `Settings`, `Paths` và helper I/O | Hoàn thành |
| Baseline Orchestration Pipeline | `src/pipelines/phase1.py`, `script/run_phase1.py` | Modules ingestion, cleaning, retrieval, observability | Toàn bộ artifacts Pha 1 (`phase1_report.md`, `baseline_metrics.json`) | Hoàn thành |
| Corruption & Repair Orchestration | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Clean data, corruption suite, raw snapshot | Báo cáo so sánh 3 trạng thái `corruption_report.md` | Hoàn thành |
| Automated Self-Healing Pipeline (Bonus B2) | `src/observability/self_healing.py`, `script/run_self_healing.py` | Bất kỳ DataFrame hoặc file clean data nào | Pipeline tự phục hồi khi có cảnh báo dữ liệu bẩn | Hoàn thành |
| Pytest CI Suite (Bonus B3) | `tests/test_pipeline.py`, `.github/workflows/ci.yml` | Toàn bộ mã nguồn dự án | 100% tests passed, cấu hình GitHub Actions CI | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Debug mã hóa tiếng Việt trên Windows | Cả nhóm / toàn bộ script | Thêm `sys.stdout.reconfigure(encoding='utf-8')` sửa triệt để lỗi `charmap UnicodeEncodeError` |
| Rà soát Data Contract | Đặng Thái Anh (`cleaning.py`) | Thống nhất cấu trúc 5 phần của `text_for_embedding` và kiểu dữ liệu `age_days` |
| Tích hợp ChromaDB & LLM Judge | Đỗ Trung Tuyến (`retrieval/`, `observability/`) | Đảm bảo persistent path cho 3 collection độc lập và cơ chế timeout API |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Thiết kế kiến trúc tổng thể & Orchestration | `src/pipelines/phase1.py` | Chạy end-to-end 7 bước của Pha 1 | `python script/run_phase1.py` exit code 0 |
| Điều phối luồng 3 trạng thái | `src/pipelines/corruption_flow.py` | Tạo bảng đối chiếu Baseline - Corrupted - Repaired | `python script/run_corruption_flow.py` exit code 0 |
| Xây dựng cơ chế Auto Self-Healing | `src/observability/self_healing.py` | Tự động phát hiện lỗi và phục hồi dữ liệu từ raw | `python script/run_self_healing.py` exit code 0 |
| Thiết lập bộ kiểm thử tự động | `tests/test_pipeline.py` | Toàn bộ unit tests bao phủ mọi tầng pipeline | `pytest tests/ -v` pass 100% |

**Output cụ thể:**
File báo cáo đối chiếu `data/reports/corruption_report.md` và console bảng đối chiếu hiệu năng 3 trạng thái với Hit Rate phục hồi hoàn toàn từ 60.0% lên 100.0%.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Một Data Pipeline cho hệ thống RAG không thể xem là hoàn chỉnh nếu chỉ hoạt động trong điều kiện lý tưởng (Happy Path). Nếu không có cơ chế điều phối chặt chẽ, các lỗi schema hoặc suy thoái dữ liệu (Data Corruption) sẽ âm thầm lọt vào Vector Database, gây ra hiện tượng **Silent Failure** mà không hề sinh ngoại lệ (Exception). Nhiệm vụ của tôi là tích hợp các module thành một chu trình khép kín, tự động hóa việc đo lường, đối chiếu và kích hoạt cơ chế tự phục hồi (Self-Healing).

### Cách triển khai
1. **Thiết kế Idempotent Pipeline:** Đảm bảo mỗi lần chạy pipeline với cùng dữ liệu đầu vào đều cho ra kết quả đồng nhất mà không làm phát sinh dữ liệu rác hay lỗi trùng lặp collection ChromaDB. Trước khi tạo collection mới, pipeline luôn kiểm tra và dọn dẹp collection cũ.
2. **Quản lý trạng thái đa tầng (Multi-State Orchestration):** Trong `corruption_flow.py`, tôi điều phối tuần tự: nạp Baseline $\rightarrow$ tiêm 6 lỗi dữ liệu $\rightarrow$ đánh giá sụt giảm $\rightarrow$ kích hoạt nạp lại từ Raw snapshot $\rightarrow$ đánh giá phục hồi $\rightarrow$ xuất bảng đối chiếu.
3. **Cơ chế Self-Healing tự động (Bonus B2):** Khi Quality Gate hoặc Freshness SLA trả về vi phạm, bộ điều phối tự động kích hoạt logic rollback và tái tạo sạch từ nguồn Raw bất biến mà không cần con người can thiệp.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | `Settings` cấu hình từ `.env`, dữ liệu thô tại `data/raw/crossref_records.json` |
| Output | Các file metrics JSON (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`), Markdown reports |
| Module phụ thuộc | `ingestion`, `cleaning`, `retrieval`, `observability`, `evaluation` |
| Module sử dụng output | Giám khảo nghiệm thu, Interactive Observability Dashboard, CI runner |
| Điều kiện lỗi cần xử lý | Xung đột encoding trên Windows, collection ChromaDB đã tồn tại, mất kết nối API |

### Cách xác minh

```bash
# Chạy luồng kiểm chứng suy thoái và phục hồi
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Console in ra bảng so sánh 3 trạng thái, Hit Rate khôi phục từ 60.0% lên 100.0%, GX Quality Gate chuyển từ FAILED sang PASSED.
- **Kết quả thực tế:** Chương trình hoàn thành trong ~40 giây, exit code 0, bảng đối chiếu hiển thị chính xác.
- **Artifact:** `data/reports/corruption_report.md`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp xử lý khi dữ liệu bị lỗi (Data Corruption) được phát hiện bởi Great Expectations 1.x.
- **Các phương án đã cân nhắc:**
  - *Phương án 1:* Sửa trực tiếp tại chỗ (In-place Repair) bằng cách xóa các dòng bị lỗi hoặc điền giá trị mặc định vào các trường bị rỗng trong DataFrame bị hỏng.
  - *Phương án 2:* Tái tạo bất biến (Idempotent Repair) bằng cách đọc lại 100% từ bản sao lưu thô bất biến `data/raw/crossref_records.json` và chạy lại quy trình chuẩn hóa.
- **Phương án đã chọn:** Phương án 2 (Idempotent Repair từ Raw snapshot).
- **Lý do:** Phương án 1 (sửa tại chỗ) có nguy cơ gây mất mát dữ liệu vĩnh viễn (ví dụ 4 bài báo bị xóa không thể lấy lại nếu không nạp từ raw) và tạo ra sự phân mảnh trạng thái (State Drift). Phương án 2 đảm bảo tính toán bất biến (Immutability), Data Lineage rõ ràng và có thể kiểm chứng độc lập ở mọi môi trường.
- **Bằng chứng quyết định phù hợp:** Hit Rate khôi phục chính xác 100.0% và số dòng của DataFrame sau repair luôn đạt chuẩn 24 dòng, trùng khớp hoàn toàn với Baseline.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  Traceback (most recent call last):
    File "<string>", line 1, in <module>
    File "...\encodings\cp1252.py", line 19, in encode
      return codecs.charmap_encode(input,self.errors,encoding_table)[0]
  UnicodeEncodeError: 'charmap' codec can't encode characters in position 6-7: character maps to <undefined>
  ```
- **Lệnh tái hiện:** Chạy bất kỳ script nào in thông báo tiếng Việt trên Windows PowerShell mà không thiết lập encoding UTF-8.
- **Nguyên nhân gốc:** Windows console mặc định sử dụng codepage 1252 (cp1252), khi in ký tự tiếng Việt có dấu sẽ ném ngoại lệ `UnicodeEncodeError`.
- **Cách xử lý:** 
  1. Thêm cấu hình tự động vào đầu các file entrypoint:
     ```python
     import sys
     if hasattr(sys.stdout, "reconfigure"):
         sys.stdout.reconfigure(encoding="utf-8", errors="replace")
     ```
  2. Bổ sung cờ `-X utf8` và thiết lập biến môi trường `$env:PYTHONIOENCODING="utf-8"` trong mọi lệnh thực thi.
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_phase1.py` và `python script/run_corruption_flow.py`, in toàn bộ văn bản có dấu mượt mà không còn lỗi.
- **Điều học được:** Khi phát triển phần mềm đa nền tảng (cross-platform), luôn phải kiểm soát chặt chẽ cơ chế mã hóa I/O stream để tránh các lỗi môi trường cục bộ.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu được thu thập qua Crossref REST API (hoặc fallback snapshot offline) $\rightarrow$ parse thành các đối tượng `PaperRecord` $\rightarrow$ tiền xử lý khử XML và ghép chuỗi `text_for_embedding` (5 phần) $\rightarrow$ chuyển đổi thành vector embedding 384 chiều qua mô hình `all-MiniLM-L6-v2` $\rightarrow$ lưu trữ kèm metadata vào ChromaDB persistent storage.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Mỗi câu hỏi trong test set gắn liền với `ground_truth_doc_ids` (DOI của bài báo mục tiêu). Khi truy vấn, nếu ít nhất một trong top_k tài liệu trả về khớp với ID mục tiêu thì tính là Hit (`retrieval_hit = True`). Câu trả lời được so sánh với ground-truth bằng Token F1 và mô hình LLM Judge đánh giá độ chính xác ngữ nghĩa (1-5 điểm).
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks (Great Expectations 1.x) tập trung vào tính toàn vẹn tĩnh của dữ liệu (schema, non-null, uniqueness, độ dài chuỗi). Trong khi đó, Freshness monitoring tập trung vào tính thời điểm (timeliness / drift theo thời gian), đo lường số ngày từ ngày xuất bản đến hiện tại (`age_days`) để phát hiện dữ liệu lỗi thời.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Đây là nguyên tắc biến số kiểm soát trong nghiên cứu thực nghiệm. Việc cố định test set loại bỏ yếu tố ngẫu nhiên từ câu hỏi, đảm bảo sự thay đổi chỉ số hoàn toàn phản ánh chất lượng của tầng dữ liệu (Data Quality impact).
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Dựa trên: (1) `repaired_quality_report.json` đạt `success=True`; (2) `repaired_freshness_report.json` đạt `is_fresh=True`; (3) `repaired_metrics.json` có `retrieval_hit_rate` và `mean_token_f1` khôi phục về 100.0%; (4) `corruption_report.md` thể hiện sự tương đồng tuyệt đối giữa Baseline và Repaired.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate`   |   100.0% |     60.0% |   100.0% | Giảm mạnh 40% do 4 bài báo mới bị drop và nhiễu |
| `mean_token_f1`        |   100.0% |     85.1% |   100.0% | Mất mát tóm tắt làm suy giảm độ chính xác từ khóa |
| `judge_accuracy`       |   100.0% |     90.0% |   100.0% | LLM Judge phát hiện câu trả lời hallucinate |
| `mean_judge_score`     |     5.00 |      4.20 |     5.00 | Điểm trung bình sụt giảm rõ rệt |
| Quality checks         |   PASSED |    FAILED |   PASSED | GX 1.x cảnh báo chính xác mọi vi phạm dữ liệu |
| Freshness status       |  HEALTHY |  VIOLATED |  HEALTHY | Tỷ lệ stale 40.9% vượt xa ngưỡng 25% |

### Kết luận từ số liệu
1. **Tiêm lỗi $\rightarrow$ Quality Gate báo động $\rightarrow$ Agent suy giảm:** Việc cắt ngắn title và nhân bản hàng khiến GX báo FAILED; việc lùi ngày khiến Freshness vi phạm; kéo theo Retrieval Hit Rate sụt giảm nghiêm trọng từ 100.0% xuống 60.0%.
2. **Idempotent Repair $\rightarrow$ Quality Gate phục hồi $\rightarrow$ Agent lấy lại phong độ:** Khi nạp lại từ raw snapshot, 24 bản ghi sạch giúp GX đạt 100% Passed, Freshness trở lại Healthy, đưa Retrieval Hit Rate và F1 trở lại 100.0%.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Nguyên tắc Idempotency:** Trong Data Engineering, mọi thao tác xử lý dữ liệu phải có tính bất biến để bảo đảm khả năng phục hồi khi có sự cố.
2. **Hiện tượng Silent Failure:** Lỗi dữ liệu nguy hiểm hơn lỗi cú pháp code vì ứng dụng vẫn chạy bình thường nhưng ngầm đưa ra quyết định sai lầm.
3. **Vai trò của Data Observability:** Great Expectations 1.x và Freshness SLA là những chốt kiểm dịch không thể thiếu trước khi đưa dữ liệu vào Vector Store.

### Nếu có thêm thời gian
Tôi sẽ tích hợp cơ chế Streaming Pipeline với Apache Kafka / Redpanda để giám sát Data Drift theo thời gian thực thay vì xử lý theo từng mẻ (batch) như hiện tại.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đức Anh  
**Ngày xác nhận:** 2026-09-26
