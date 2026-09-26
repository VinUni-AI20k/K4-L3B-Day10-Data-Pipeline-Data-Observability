# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Hữu Thành             |
| MSSV               | 2A202602813                     |
| Khóa/Lớp         | K4 - Lớp B              |
| Tên nhóm         | Enigma     |
| Vai trò chính    | RAG, Vector Database & Evaluation Benchmark (`retrieval/`, `testset.py`) |
| Repository         | https://github.com/hungdq1306/K4-L3B-Day10-Enigma-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Benchmark Test Set | `src/evaluation/testset.py` | Cleaned dataframe 24 dòng | `data/eval/test_set.json` (10 câu test chuẩn 4 nhóm) | Đang thực hiện |
| Vector Indexing & Embeddings | `src/retrieval/index.py`, `embeddings.py` | Clean dataframe, MiniLM model | ChromaDB collection `papers-baseline`, `papers-corrupted`, `papers-repaired` | Đang thực hiện |
| Multi-Provider RAG QA | `src/retrieval/qa.py`, `llm.py` | Query, Search Results | LLM Answers & Retrieval Scores | Đang thực hiện |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Kiểm tra schema đầu vào cho ChromaDB | Đặng Quang Hưng (`cleaning.py`) | Thống nhất cấu trúc `text_for_embedding` và metadata đầy đủ |
| Tích hợp metric vào báo cáo | Hà Thị Mỹ Linh (`reporting.py`) | Cung cấp dữ liệu Hit Rate và Token F1 |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sinh 10 câu hỏi benchmark | `src/evaluation/testset.py` | `data/eval/test_set.json` | Kiểm tra len(testset) == 10 |
| Nạp dữ liệu vào ChromaDB | `src/retrieval/index.py` | Collection ChromaDB lưu trữ local | Query vector tương đồng |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Thiết lập kho vector lưu trữ embeddings từ văn bản khoa học và xây dựng bộ benchmark testset khách quan gồm 4 nhóm câu hỏi (`summary`, `authors`, `date`, `categories`) để đo lường chính xác năng lực Retrieval và Answer Generation của Agent.

### Cách xác minh
```bash
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
```

## 5. Quyết định kỹ thuật & Điều học được
Sử dụng mô hình embedding `sentence-transformers/all-MiniLM-L6-v2` nhẹ, nhanh, chạy offline hiệu quả, kết hợp ChromaDB PersistentClient giúp cô lập rành mạch 3 collection riêng biệt phục vụ so sánh.

## 6. Cam kết của thành viên
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** Nguyễn Hữu Thành  
**Ngày xác nhận:** 2026-09-26
