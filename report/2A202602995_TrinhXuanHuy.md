# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trịnh Xuân Huy             |
| MSSV               | 2A202602995                |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | T052AI                     |
| Vai trò chính    | Trưởng nhóm / Pipeline Integrator |
| Repository         | https://github.com/younglonelyboiz/K4-L3B-Day10-T052AI-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Cấu hình hệ thống | `core/config.py`, `core/utils.py` | Environment variables, project paths | Settings dataclass, deterministic paths | Hoàn thành |
| Synthetic Corruption Suite | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | Clean DataFrame | `papers_clean_corrupted.*`, `corruption_log.json` | Hoàn thành |
| Baseline Orchestration | `src/pipelines/phase1.py` (`main`) | Toàn bộ các module pha 1 | `run_phase1.py`, `baseline_metrics.json`, `phase1_report.md` | Hoàn thành |
| Corruption & Repair Flow | `src/pipelines/corruption_flow.py` (`main`) | Toàn bộ luồng 3 trạng thái | `run_corruption_flow.py`, `corruption_report.md` | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Điều phối và liên kết pipeline | Cả 3 thành viên (Đức, Hoàng, Huy) | Đảm bảo data contract thông suốt từ Ingestion -> Observability -> RAG -> Repair |
| Quản lý Git & Release | Toàn nhóm | Đảm bảo 100% thành viên có commit trên GitHub nhánh `main` và phân chia nhánh minh bạch |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Chạy Phase 1 Pipeline | `script/run_phase1.py` | Hit rate 100.0%, Token F1 1.000, GX True | Lệnh CP3: hoàn tất sinh `phase1_report.md` |
| Tiêm 6 kịch bản lỗi dữ liệu | `src/ingestion/corruption.py` | 6 lỗi giả lập sự cố thực tế | Log `data/results/corruption_log.json` |
| Chạy luồng 3 trạng thái | `script/run_corruption_flow.py` | Bảng so sánh Baseline (100%) vs Corrupted (60%) vs Repaired (100%) | Lệnh CP5: in bảng so sánh ra console |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Hai kịch bản pipeline hoàn chỉnh `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`, có khả năng chạy tự động end-to-end, tạo ra đầy đủ các artifact metrics và báo cáo đối chứng khoa học.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Một hệ thống dữ liệu doanh nghiệp không chỉ cần chạy đúng khi dữ liệu sạch mà phải có khả năng tự phát hiện lỗi, quan sát trạng thái (Observability), chứng minh được sự suy giảm khi gặp sự cố và tự phục hồi an toàn (Self-healing) mà không làm mất mát dữ liệu gốc.

### Cách triển khai

- **Tiêm 6 kịch bản lỗi (CP4):**
  1. `drop_latest_records`: Xóa 20% bản ghi mới nhất.
  2. `blank_summary`: Làm rỗng cột summary của các bài báo hàng đầu.
  3. `inject_noise`: Chèn chuỗi ký tự rác vào `text_for_embedding`.
  4. `truncate_titles`: Cắt ngắn title xuống dưới 8 ký tự.
  5. `stale_dates`: Lùi ngày xuất bản về năm 2020 để vi phạm SLA Freshness (> 180 ngày).
  6. `duplicate_records`: Nhân bản các dòng dữ liệu để vi phạm ràng buộc Unique của GX.
- **Chứng minh Silent Failure:** RAG Retrieval Hit Rate giảm mạnh từ 100% xuống 60%, Token F1 giảm từ 1.000 xuống 0.497. Quality Gate Great Expectations 1.x chuyển sang `FAILED` và Freshness SLA chuyển sang `STALE`.
- **Cơ chế Idempotent Repair:** Tái tạo lại dữ liệu từ snapshot thô ban đầu `data/raw/crossref_records.json`, chứng minh hệ thống phục hồi 100% phong độ (Hit Rate 100%, F1 1.000, Quality Gate `PASSED`).

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Settings hệ thống, raw snapshot và clean dataframe |
| Output                         | Bộ metrics 3 trạng thái (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`), 2 báo cáo Markdown hoàn chỉnh |
| Module phụ thuộc             | Mọi module trong `ingestion`, `retrieval`, `observability`, `evaluation` |
| Module sử dụng output        | Người dùng, giảng viên đánh giá, CI/CD automated pipeline |
| Điều kiện lỗi cần xử lý | Xử lý race conditions, đảm bảo thứ tự thực thi đúng: Ingest -> Clean -> Quality -> Eval -> Corrupt -> Repair |

### Cách xác minh

```bash
PYTHONPATH=src python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** In ra bảng đối sánh 3 trạng thái với Hit Rate: Baseline 100.0% -> Corrupted 60.0% -> Repaired 100.0%.
- **Kết quả thực tế:** Trùng khớp 100% với kết quả mong đợi.
- **Artifact/log:** `data/reports/corruption_report.md`, `data/results/corruption_log.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Thiết kế cơ chế Repair giữa "Sửa trực tiếp trên bảng Corrupted (Patching/In-place Mutation)" và "Tái tạo từ Snapshot gốc (Idempotent Rebuild from Raw Snapshot)".
- **Các phương án đã cân nhắc:**
  1. *Phương án 1 (In-place Patching):* Viết hàm tìm dòng bị lỗi để bổ sung hoặc sửa đổi.
  2. *Phương án 2 (Idempotent Rebuild from Raw):* Coi dữ liệu clean là sản phẩm phái sinh (derived asset), khi có lỗi thì xóa bỏ và tái tạo lại 100% từ immutable raw snapshot.
- **Phương án đã chọn:** Phương án 2 (Idempotent Rebuild from Raw Snapshot).
- **Lý do:** Phương án 1 tiềm ẩn nguy cơ "lỗi chồng lỗi" (dirty state accumulation) và khó kiểm chứng. Phương án 2 đảm bảo tính toán bất biến (Immutability), tính Idempotent tuyệt đối và khả năng khôi phục chắc chắn 100%.
- **Bằng chứng quyết định phù hợp:** Pipeline repair khôi phục hoàn hảo 24/24 bản ghi chuẩn, đưa toàn bộ metrics chất lượng và RAG về trạng thái lý tưởng như ban đầu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Xung đột module import `ModuleNotFoundError: No module named 'core'` khi chạy các script từ thư mục gốc.
- **Lệnh hoặc bước tái hiện:** `python script/run_corruption_flow.py`
- **Nguyên nhân gốc:** Thư mục `src/` không nằm trong biến môi trường `sys.path` mặc định khi chạy từ bên ngoài.
- **Cách xử lý:** Cấu hình chuẩn hóa `PYTHONPATH=src` trong các lệnh chạy script và hướng dẫn `README.md`.
- **Cách xác minh sau khi sửa:** Chạy trơn tru tất cả các lệnh qua cả hai cách `PYTHONPATH=src python ...` và `uv run python ...`.
- **Điều học được:** Cấu trúc dự án Python dạng `src-layout` đòi hỏi quản lý đường dẫn import chặt chẽ và nhất quán trong toàn đội ngũ.

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** N/A (Đã xử lý hoàn tất 100%)
- **Những gì đã loại trừ:** N/A
- **Bước tiếp theo:** N/A

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index:** Dữ liệu thô từ Crossref REST API (hoặc snapshot offline dự phòng) được tải về và lưu vào `data/raw/crossref_response.json` cùng `crossref_records.json` (bảo toàn data lineage). Sau đó hàm `build_clean_dataframe` trong `cleaning.py` làm sạch các thẻ XML, tính trường `age_days` và tạo chuỗi `text_for_embedding` 5 phần có nhãn. Chuỗi văn bản này được đưa vào mô hình `all-MiniLM-L6-v2` để sinh vector 384 chiều và nạp vào ChromaDB collection `papers-baseline`.
2. **Evaluation set và ground-truth document IDs:** Module `testset.py` trích xuất 10 cặp câu hỏi - câu trả lời cùng `ground_truth_doc_ids` từ clean DataFrame. Khi RAG truy vấn, nếu doc_id do vector search tìm được nằm trong danh sách ground_truth_doc_ids thì tính là `retrieval_hit = True`. Mean Token F1 đo lường sự trùng khớp từ vựng giữa câu trả lời sinh ra và câu trả lời chuẩn ground truth.
3. **Quality checks khác freshness monitoring:** Quality checks (Great Expectations 1.x) kiểm định tính toàn vẹn cấu trúc tĩnh của bảng (số dòng [20, 30], khóa chính không trùng, trường bắt buộc không null, độ dài summary >= 10). Trong khi đó Freshness monitoring đo lường chiều thời gian (Data Drift/Staleness), phát hiện tỷ lệ bài báo quá hạn (> 180 ngày) vượt ngưỡng SLA 25%.
4. **Vì sao phải dùng cùng test set cho 3 trạng thái:** Để đảm bảo tính khách quan và khoa học (Controlled Experiment). Việc giữ cố định bộ câu hỏi giúp mọi sự thay đổi về Hit Rate và Token F1 phản ánh chính xác tác động của việc dữ liệu bị lỗi và phục hồi, loại bỏ thiên vị do câu hỏi khác nhau.
5. **Repair được xem là thành công dựa trên:** Hệ thống khôi phục hoàn toàn chỉ số Retrieval Hit Rate về 100.0%, Mean Token F1 về 1.000, Quality Gate chuyển từ `FAILED` sang `PASSED`, và Freshness SLA chuyển từ `STALE` sang `FRESH`, thể hiện qua các artifact `data/results/repaired_metrics.json` và `data/reports/corruption_report.md`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   100.0% |     60.0% |   100.0% | Sụt giảm nghiêm trọng (-40%) khi bị tiêm lỗi, hồi sinh 100% sau repair |
| `mean_token_f1`      |    1.000 |     0.497 |    1.000 | Chất lượng văn bản câu trả lời giảm hơn 50% ở trạng thái lỗi |
| `judge_accuracy`     |   100.0% |     50.0% |   100.0% | Tỷ lệ câu trả lời đạt chuẩn ngữ nghĩa khôi phục toàn diện |
| `mean_judge_score`   | 5.00/5.0 | 3.00/5.0 | 5.00/5.0 | Điểm đánh giá chất lượng câu trả lời phục hồi tối đa |
| Quality checks         | `PASSED` |  `FAILED` | `PASSED` | GX 1.x bắt trọn vi phạm trùng lặp DOI và rỗng summary |
| Freshness status       |  `FRESH` |   `STALE` |  `FRESH` | Cảnh báo vi phạm ngưỡng SLA 180 ngày chính xác |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. [Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]:  
   Khi 6 kịch bản lỗi được tiêm vào (xóa 20% bản ghi mới nhất, làm rỗng summary, chèn ký tự rác, lùi ngày về 2020) → Quality check chuyển sang `FAILED` và Freshness chuyển sang `STALE` → Dẫn đến Retrieval Hit Rate sụt giảm từ 100.0% xuống 60.0% và Mean Token F1 giảm từ 1.000 xuống 0.497.
2. [Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi hoặc chưa phục hồi]:  
   Khi kích hoạt cơ chế Idempotent Repair tái tạo từ immutable raw snapshot `crossref_records.json` → Quality check phục hồi về `PASSED`, Freshness phục hồi về `FRESH` → Retrieval Hit Rate và Token F1 phục hồi 100% về mức 100.0% và 1.000.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Kịch bản xóa mất bản ghi mới nhất kết hợp cắt ngắn title khiến RAG Agent mất context hoàn toàn và nhận diện sai tài liệu đích, thể hiện qua việc giảm 40% hit rate và 50% F1.

Kết quả nào khác với kỳ vọng ban đầu?

Ban đầu tôi dự đoán việc duplicate rows chỉ làm chậm tốc độ xử lý, nhưng trong thực tế nó làm vi phạm ràng buộc Unique constraint của Great Expectations ngay lập tức, ngăn chặn dữ liệu bẩn trước khi tiến vào bước embedding.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Về data pipeline: Pipeline vững chắc phải thiết kế theo tư duy "Fail gracefully and Recover deterministically" (thất bại an toàn và phục hồi tất định).
2. Về data quality/observability: Observability là cầu nối sống còn giữa Data Engineering và AI Engineering để giải quyết bài toán Silent Failure.
3. Về ảnh hưởng của data đến RAG agent: Việc phân chia ranh giới contract rõ ràng giữa các deliverable giúp cả nhóm làm việc song song mà không bị giẫm chân lên nhau.

### Nếu có thêm thời gian

Tôi sẽ thiết lập workflow GitHub Actions CI/CD để tự động chạy kiểm thử Data Quality Check và RAG Regression Evaluation mỗi khi có Pull Request được tạo vào nhánh `main`.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trịnh Xuân Huy  
**Ngày xác nhận:** 2026-09-26
