# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lê Việt Hoàng              |
| MSSV               | 2A202602596                |
| Khóa/Lớp         | K4-L3B-Day10               |
| Tên nhóm         | T052AI                     |
| Vai trò chính    | RAG & Vector Index         |
| Repository         | https://github.com/younglonelyboiz/K4-L3B-Day10-T052AI-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Vector Store Indexing | `src/retrieval/index.py` (`LocalEmbeddingIndex`) | Cleaned/Corrupted/Repaired DataFrame | 3 ChromaDB collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`) | Hoàn thành |
| Embedding Generator | `src/retrieval/embeddings.py` (`MiniLMEmbeddings`) | `all-MiniLM-L6-v2` | Dense vector embeddings (384 chiều) | Hoàn thành |
| Multi-Provider QA Agent | `src/retrieval/agent.py`, `qa.py`, `llm.py` | Query, ChromaDB search, LLM config | Trích xuất câu trả lời chuẩn xác theo ngữ cảnh | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Hỗ trợ STT 1 đo lường hiệu năng | Trịnh Xuân Huy (`src/pipelines/phase1.py`, `corruption_flow.py`) | Cung cấp interface `index.search` và `index.lookup` giúp đạt Hit Rate 100% ở baseline |
| Hỗ trợ STT 4 kiểm tra testset | Mai Tiến Huy (`src/evaluation/testset.py`) | Đảm bảo metadata của documents khớp với các trường trích xuất QA |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Index 24 tài liệu sạch vào ChromaDB | `src/retrieval/index.py` | Collection `papers-baseline` | File `data/embeddings/papers_embeddings.json` sinh ra đầy đủ 24 docs |
| Tách biệt 3 không gian vector | `src/retrieval/index.py` | 3 collection độc lập trong `data/chroma/` | Thư mục `data/chroma/` lưu trữ bền vững SQLite và segment |
| Đo lường suy giảm retrieval | `src/evaluation/metrics.py` | Hit rate giảm từ 100% -> 60% khi corrupted | File `data/results/corrupted_metrics.json` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Hệ thống vector index ChromaDB lưu trữ liên tục (persistent SQLite) tại `data/chroma/` chứa 3 collections độc lập cùng file manifest `data/embeddings/papers_embeddings.json` định dạng 24 vector nhúng 384 chiều.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Để so sánh một cách khách quan giữa dữ liệu sạch (Baseline), dữ liệu bị lỗi (Corrupted) và dữ liệu đã sửa chữa (Repaired), hệ thống RAG không thể dùng chung một collection vector vì sẽ gây lẫn lộn ngữ cảnh. Cần kiến trúc cô lập từng không gian vector riêng biệt với cùng embedding model `sentence-transformers/all-MiniLM-L6-v2`.

### Cách triển khai

- **Cơ chế Embedding Dense Vector:** Sử dụng mô hình `all-MiniLM-L6-v2` chuyển đổi toàn bộ chuỗi 5 phần của trường `text_for_embedding` thành vector nhúng 384 chiều chuẩn hóa L2.
- **Quản lý ChromaDB Collections độc lập:** Xây dựng lớp `LocalEmbeddingIndex` hỗ trợ nạp tài liệu vào các collection riêng biệt:
  - `papers-baseline`: Nạp từ `papers_clean.json`.
  - `papers-corrupted`: Nạp từ `papers_clean_corrupted.json`.
  - `papers-repaired`: Nạp từ `papers_clean_repaired.json`.
- **Cơ chế Hybrid Search:** Tích hợp cả tìm kiếm tương đồng vector cosine (`space: cosine`) và cơ chế tra cứu chính xác theo khóa băm `paper_id` / `title` để phục vụ đánh giá ground truth.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | DataFrame chứa cột `text_for_embedding`, `paper_id`, `title`, `summary` |
| Output                         | ChromaDB Persistent Collections trong `data/chroma/`, manifest embeddings `data/embeddings/` |
| Module phụ thuộc             | `chromadb`, `sentence-transformers`, `core.config.Settings` |
| Module sử dụng output        | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/evaluation/evaluate.py` |
| Điều kiện lỗi cần xử lý | Xử lý tài liệu có `summary` rỗng hoặc bị cắt ngắn dưới ngưỡng độ dài embedding |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from retrieval.index import build_paper_index; from ingestion.cleaning import load_clean_dataset; s=load_settings(); idx=build_paper_index(load_clean_dataset(s.paths.clean_dataset_json), s); print(f'Tín hiệu hoàn thành: Index thành công collection {idx.collection_name}')"
```

- **Kết quả mong đợi:** In ra `Tín hiệu hoàn thành: Index thành công collection papers-baseline`.
- **Kết quả thực tế:** Trùng khớp 100% với kết quả mong đợi.
- **Artifact/log:** `data/chroma/chroma.sqlite3`, `data/embeddings/papers_embeddings.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp lưu trữ vector giữa in-memory ChromaDB và Persistent ChromaDB client.
- **Các phương án đã cân nhắc:**
  1. *Phương án 1 (Ephemeral In-Memory):* Tạo index tạm thời trong RAM mỗi khi chạy câu hỏi.
  2. *Phương án 2 (Persistent On-Disk):* Sử dụng `chromadb.PersistentClient(path=str(settings.paths.chroma_dir))` để lưu trữ bền vững.
- **Phương án đã chọn:** Phương án 2 (Persistent On-Disk).
- **Lý do:** Giúp tái sử dụng các vector đã tính toán, giảm thời gian khởi chạy giữa các lần evaluate và cho phép cô lập hoàn toàn 3 collection độc lập phục vụ cho quy trình đối chứng khoa học.
- **Bằng chứng quyết định phù hợp:** Thời gian truy vấn tìm kiếm RAG giảm xuống dưới 15ms cho mỗi câu hỏi, dữ liệu index được lưu trữ bền vững tại `data/chroma/`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ValueError: Expected embedding length 384, but got None` khi một số văn bản bị rỗng do kịch bản corruption `blank_summary`.
- **Lệnh hoặc bước tái hiện:** Chạy embedding trên tập dữ liệu bị xóa rỗng nội dung summary.
- **Nguyên nhân gốc:** Khi summary bị rỗng, chuỗi `text_for_embedding` bị suy thoái chỉ còn nhãn rỗng, một số tokenizer xử lý chuỗi rỗng không đồng nhất.
- **Cách xử lý:** Bổ sung cơ chế fallback kiểm tra chuỗi rỗng: nếu văn bản không đủ độ dài tối thiểu, gán giá trị mặc định có cấu trúc để embedding model luôn trả về vector 384 chiều hợp lệ mà không làm crash ứng dụng.
- **Cách xác minh sau khi sửa:** Chạy toàn bộ pipeline corruption mà không gặp lỗi runtime, hệ thống ghi nhận chính xác sự sụt giảm độ tương đồng cosine thay vì văng exception.
- **Điều học được:** Module Vector Ingestion phải luôn có tầng phòng thủ (defensive handling) trước các vector suy biến do dữ liệu bẩn gây ra.

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

Kịch bản xóa mất bản ghi mới nhất (`drop_latest_records`) và làm rỗng summary khiến các câu hỏi truy xuất vào top documents hoàn toàn không tìm thấy vector tương ứng trong ChromaDB, làm tụt trực tiếp 40% Retrieval Hit Rate.

Kết quả nào khác với kỳ vọng ban đầu?

Ban đầu tôi dự đoán rằng cơ chế Semantic Search sẽ tự động tìm được các bài báo có nội dung gần đúng dù bị nhiễu nhẹ; tuy nhiên thực tế khi bị inject noise và cắt ngắn title, khoảng cách cosine tăng vọt khiến model truy xuất nhầm văn bản hoàn toàn, làm Token F1 giảm sâu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Về data pipeline: Vector database chỉ là tấm gương phản chiếu dữ liệu nguồn; dữ liệu đầu vào bị thiếu thì vector store hoàn toàn mất khả năng truy xuất.
2. Về data quality/observability: Việc đo lường Retrieval Hit Rate cần gắn liền với ground truth doc IDs để có thước đo định lượng chính xác thay vì đánh giá cảm tính.
3. Về ảnh hưởng của data đến RAG agent: Cơ chế cô lập collection theo từng phiên bản dữ liệu (baseline/corrupted/repaired) là kỹ thuật quan trọng để thực hiện kiểm thử A/B và phân tích sự cố.

### Nếu có thêm thời gian

Tôi sẽ tích hợp kỹ thuật Re-ranking (Cross-encoder) sau bước Retrieval để tối ưu hóa thứ tự các bài báo được đưa vào context của LLM.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lê Việt Hoàng  
**Ngày xác nhận:** 2026-09-26
