# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đỗ Trung Tuyến            |
| MSSV               | 2A202602427               |
| Khóa/Lớp         | K4 - Lớp B (Ca Sáng)      |
| Tên nhóm         | Team 03 - DataObservability |
| Vai trò chính    | RAG Agent & Vector Index Architecture |
| Repository         | K4-L3B-DAY10-Team03-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26.              |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| ChromaDB Vector Store & Embedding Manager | `src/retrieval/index.py`, `src/retrieval/embeddings.py` | Cleaned DataFrame, `all-MiniLM-L6-v2` | 3 collections độc lập trong `data/chroma/`, manifest JSON | Hoàn thành |
| Multi-Provider LLM Router | `src/retrieval/llm.py` (`build_llm`) | Cấu hình `Settings`, API credentials | LangChain LLM Client (`gemini`, `openai`, `mock`) | Hoàn thành |
| Semantic Search & QA Extraction | `src/retrieval/qa.py` (`answer_question`, `_extract_answer`) | Câu hỏi tự nhiên, vector index | Câu trả lời trích xuất, danh sách retrieved IDs | Hoàn thành |
| Agentic Tool-Use Integration | `src/retrieval/agent.py` (`build_agent`, `run_agent_question`) | LLM model, tools semantic search & lookup | LangChain Agent có khả năng suy luận trên kho dữ liệu | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Tích hợp Vector Retrieval vào Pipeline | Nguyễn Đức Anh (`phase1.py`, `corruption_flow.py`) | Đảm bảo quá trình tạo và nạp ChromaDB collection chạy ổn định trong pipeline |
| Phối hợp định dạng Embedding Text | Đặng Thái Anh (`cleaning.py`) | Kiểm chứng cấu trúc 5 phần của `text_for_embedding` tương thích tối đa với MiniLM |
| Cung cấp kết quả truy vấn cho Benchmark | Nguyễn Khánh Duy (`metrics.py`, `testset.py`) | Cung cấp đầu ra `retrieved_doc_ids` để tính toán chính xác Retrieval Hit Rate |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Quản lý mô hình MiniLM Embedding | `src/retrieval/embeddings.py` | Sinh vector 384 chiều chuẩn hóa cosine | Vector độ dài 384, normalize L2 thành công |
| Khởi tạo 3 ChromaDB collections | `src/retrieval/index.py` | `papers-baseline`, `papers-corrupted`, `papers-repaired` | Lưu trữ persistent tại `data/chroma/` |
| Xây dựng Multi-Provider LLM | `src/retrieval/llm.py` | Hỗ trợ Gemini 2.5 Flash và Mock model | Chạy mượt mà cả online và offline |
| Triển khai QA Engine | `src/retrieval/qa.py` | Kết hợp exact match title và semantic cosine | Hit Rate đạt 100% trên dữ liệu sạch |

**Output cụ thể:**
Hệ thống vector index ChromaDB với 3 collection độc lập lưu trữ tại `data/chroma/` và file manifest `data/embeddings/papers_embeddings.json`.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Trong hệ thống RAG, vector store là cầu nối quan trọng nhất giữa dữ liệu thô và mô hình ngôn ngữ lớn (LLM). Nếu việc đánh chỉ mục vector bị lỗi hoặc không gian vector giữa các trạng thái (sạch vs lỗi) bị trộn lẫn, các đánh giá khoa học sẽ mất đi tính khách quan.
2. Cần xây dựng cơ chế truy vấn thông minh có khả năng kết hợp giữa tìm kiếm tương đồng ngữ nghĩa (Semantic Vector Search) và tra cứu chính xác theo tiêu đề (Exact Title Lookup) để tối đa hóa Retrieval Hit Rate.
3. Cần hỗ trợ đa dạng nhà cung cấp LLM (Gemini, OpenAI, Mock) để phục vụ chấm điểm và chạy kiểm thử tự động trong CI/CD.

### Cách triển khai
1. **Quản lý Vector Embeddings với `sentence-transformers/all-MiniLM-L6-v2`:**
   Sử dụng mô hình MiniLM 384 chiều, chuẩn hóa `normalize_embeddings=True` để áp dụng khoảng cách Cosine Distance tối ưu trong không gian đa chiều.
2. **Cô lập không gian Vector (Vector Space Isolation):**
   Thay vì ghi đè một collection duy nhất, tôi khởi tạo 3 collection riêng biệt:
   - `papers-baseline`: Chứa 24 tài liệu sạch ban đầu.
   - `papers-corrupted`: Chứa dữ liệu đã bị tiêm 6 lỗi (thiếu bài, summary rác, title ngắn).
   - `papers-repaired`: Chứa 24 tài liệu sạch đã được phục hồi bất biến từ raw snapshot.
3. **Cơ chế Truy vấn Phối hợp (Hybrid Retrieval Strategy):**
   Trong `answer_question`, tôi trích xuất tiêu đề trong dấu nháy đơn `'...'` nếu có để lookup chính xác. Sau đó kết hợp với kết quả tìm kiếm ngữ nghĩa vector `search()` để đảm bảo câu trả lời luôn nhận được văn cảnh tối ưu nhất trong top_k.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | `text_for_embedding` từ DataFrame, câu hỏi tự nhiên từ user hoặc test set |
| Output | Vector embeddings (list float 384d), `SearchResult` (paper_id, score, content, metadata) |
| Module phụ thuộc | `sentence_transformers`, `chromadb`, `core/config.py` |
| Module sử dụng output | `evaluation/metrics.py`, `retrieval/agent.py`, pipeline runner |
| Điều kiện lỗi cần xử lý | Collection đã tồn tại trong ChromaDB (xóa an toàn trước khi tạo mới) |

### Cách xác minh

```bash
# Kiểm tra Vector Index và Semantic Search
python -c "from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); idx=LocalEmbeddingIndex.load(s); res=idx.search('large language model', top_k=2); print(f'Tim thay {len(res)} ket qua, top doc: {res[0].paper_id}')"
```

- **Kết quả mong đợi:** Tìm thấy 2 kết quả, in ra DOI hợp lệ của bài báo.
- **Kết quả thực tế:** Chính xác 100%.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp quản lý collection ChromaDB khi chạy luồng kiểm chứng suy thoái và phục hồi.
- **Các phương án đã cân nhắc:**
  - *Phương án 1:* Dùng chung một collection duy nhất (`papers`), mỗi lần chuyển pha thì xóa dữ liệu bên trong và ghi đè.
  - *Phương án 2:* Khởi tạo 3 collections riêng biệt (`papers-baseline`, `papers-corrupted`, `papers-repaired`) trong cùng một thư mục lưu trữ persistent.
- **Phương án đã chọn:** Phương án 2 (3 collections độc lập).
- **Lý do:** Dùng chung 1 collection có nguy cơ "rò rỉ vector" (Vector Leakage) do bộ đệm HNSW index chưa kịp flush xuống đĩa, dẫn đến việc dữ liệu sạch và dữ liệu bẩn bị lẫn lộn. Sử dụng 3 collection riêng biệt giúp cô lập hoàn toàn không gian vector, cho phép người dùng hoặc giám khảo có thể truy vấn kiểm chứng chéo bất kỳ lúc nào mà không cần chạy lại pipeline từ đầu.
- **Bằng chứng quyết định phù hợp:** Kết quả benchmark trên `papers-baseline` và `papers-corrupted` phản ánh sự phân biệt rạch ròi: Hit Rate 100% vs 60%, không hề có hiện tượng nhiễu chéo.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  chromadb.errors.UniqueConstraintError: Collection papers-baseline already exists.
  ```
- **Lệnh tái hiện:** Chạy lại `python script/run_phase1.py` lần thứ 2 khi thư mục `data/chroma/` đã tồn tại collection từ lần chạy trước.
- **Nguyên nhân gốc:** Hàm `client.create_collection(name=collection_name)` ném ngoại lệ nếu collection cùng tên đã tồn tại trên ổ đĩa.
- **Cách xử lý:** 
  Bổ sung khối lệnh xử lý an toàn trước khi tạo mới collection trong `LocalEmbeddingIndex.build`:
  ```python
  try:
      client.delete_collection(name=collection_name)
  except Exception:
      pass
  collection = client.create_collection(
      name=collection_name,
      configuration={"hnsw": {"space": "cosine"}},
  )
  ```
- **Cách xác minh sau khi sửa:** Chạy lặp lại `run_phase1.py` nhiều lần liên tiếp, hệ thống luôn dọn dẹp sạch sẽ và tạo collection mới thành công mà không gặp lỗi.
- **Điều học được:** Khi làm việc với cơ sở dữ liệu Vector lưu trữ persistent, luôn phải thiết kế các thao tác nạp dữ liệu có tính Idempotent để tránh xung đột trạng thái cũ.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu thô từ Crossref API $\rightarrow$ lưu raw snapshot $\rightarrow$ làm sạch và tạo văn bản nhúng $\rightarrow$ tính toán vector embedding 384 chiều $\rightarrow$ lưu trữ trên ChromaDB vector database.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Đo lường bằng cách kiểm tra xem bài báo chứa câu trả lời đúng (`ground_truth_doc_ids`) có xuất hiện trong danh sách bài báo mà ChromaDB tìm thấy hay không. Nếu có là Hit; sau đó so sánh câu trả lời của AI với câu trả lời chuẩn bằng Token F1 và LLM Judge.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks giám sát lỗi cấu trúc tĩnh (thiếu trường, sai kiểu, trùng lặp, chuỗi quá ngắn). Freshness monitoring giám sát tính thời sự của thông tin (Data Drift theo thời gian).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính khách quan và khoa học. Nếu thay đổi câu hỏi kiểm thử giữa các pha, chúng ta không thể biết sự thay đổi chỉ số là do dữ liệu tốt/xấu hay do câu hỏi dễ/khó.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Dựa trên sự phục hồi của toàn bộ hệ thống chỉ số: Hit Rate đạt 100%, F1 đạt 100%, Quality Report đạt PASSED, và Freshness đạt HEALTHY.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate`   |   100.0% |     60.0% |   100.0% | 4 câu hỏi bị trượt do thiếu tài liệu mục tiêu |
| `mean_token_f1`        |   100.0% |     85.1% |   100.0% | Các câu hỏi tóm tắt bị mất từ khóa chính xác |
| `judge_accuracy`       |   100.0% |     90.0% |   100.0% | LLM Judge phát hiện câu trả lời bị sai lệch |
| `mean_judge_score`     |     5.00 |      4.20 |     5.00 | Giảm từ 5.0 xuống 4.2 do chất lượng câu trả lời suy thoái |
| Quality checks         |   PASSED |    FAILED |   PASSED | Chốt chặn GX 1.x phát hiện vi phạm ngay lập tức |
| Freshness status       |  HEALTHY |  VIOLATED |  HEALTHY | Tỷ lệ stale 40.9% vượt xa ngưỡng cho phép 25% |

### Kết luận từ số liệu
- Việc dữ liệu bị tiêm lỗi làm biến dạng nghiêm trọng không gian vector embedding, khiến thuật toán k-NN cosine tìm kiếm sai lệch tài liệu liên quan.
- Sau khi chạy Idempotent Repair, vector index được tái tạo hoàn toàn, đưa toàn bộ chỉ số Retrieval Hit Rate và Token F1 về mức tuyệt đối 100.0%.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Tầm quan trọng của Cấu trúc Văn bản Nhúng:** Ghép thông tin có cấu trúc 5 phần (Title, Authors, Categories, Published, Summary) mang lại độ chính xác ngữ nghĩa vượt trội so với chỉ embed tóm tắt thuần túy.
2. **Kỹ thuật Vector Isolation:** Tách biệt các collection giúp ngăn ngừa triệt để lỗi rò rỉ dữ liệu giữa các phiên kiểm thử.
3. **Mô hình Hybrid Retrieval:** Kết hợp giữa exact lookup và semantic search là giải pháp tối ưu cho các bài toán QA trên tài liệu học thuật.

### Nếu có thêm thời gian
Tôi sẽ tích hợp kỹ thuật Re-ranking (Cross-Encoder / Cohere Rerank) sau bước vector retrieval để sắp xếp lại top 4 tài liệu có độ liên quan cao nhất trước khi đưa vào LLM.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đỗ Trung Tuyến  
**Ngày xác nhận:** 2026-09-26
