# Phần 3 — Bùi Quốc Việt: Vector Database & RAG Retrieval

## Các thành phần

- `embeddings.py`: dùng `sentence-transformers/all-MiniLM-L6-v2`, chuẩn hóa vector và cache mô hình trong tiến trình.
- `index.py`: lưu ChromaDB vào `data/chroma`, tìm kiếm cosine, lưu manifest để tải lại index. ID vector gồm DOI và số thứ tự dòng để giữ được các dòng trùng của thí nghiệm corruption.
- `llm.py`: khởi tạo provider theo `LLM_PROVIDER` và `LLM_MODEL`; chỉ import SDK của provider được chọn. Groq sử dụng endpoint tương thích OpenAI. Mock không cần API key.
- `qa.py`: trả lời benchmark bằng metadata của tài liệu tìm được; ưu tiên tiêu đề khớp chính xác. Đây là truy vấn trích xuất, không gọi LLM.
- `agent.py`: đưa ngữ cảnh truy xuất vào LLM để trả lời câu hỏi tự do.

| Dữ liệu đầu vào | Collection | Manifest trong `data/embeddings/` |
| --- | --- | --- |
| `papers_clean.json` | `papers-baseline` | `papers_embeddings.json` |
| `papers_clean_corrupted.json` | `papers-corrupted` | `papers_embeddings_corrupted.json` |
| `papers_clean_repaired.json` | `papers-repaired` | `papers_embeddings_repaired.json` |

Mỗi lần build chỉ thay thế collection của trạng thái tương ứng. Việc tính embedding diễn ra trước khi thay thế collection; thao tác thay thế không phải transaction nên lỗi ghi ChromaDB vẫn cần chạy build lại. Các batch tuân theo giới hạn của ChromaDB: https://docs.trychroma.com/reference/python.

## Chạy kiểm tra trong PowerShell

Chạy tại thư mục gốc repo, sau khi có đủ ba file JSON trong `data/clean/`:

```powershell
$env:HF_HUB_CACHE = "$PWD\.venv\hf-cache"
$env:HF_HUB_DISABLE_XET = "1"
$env:HF_HUB_DOWNLOAD_TIMEOUT = "60"
.\.venv\Scripts\python.exe -m retrieval.verify
```

Lần đầu cần mạng để tải mô hình. Lệnh này tạo lại ba collection và manifest từ dữ liệu hiện có, kiểm tra số dòng, lưu/tải lại, truy vấn vector, câu trả lời metadata, tính cô lập và Mock LLM. Không gọi API LLM có phí, không tạo lại dữ liệu sạch/bẩn/phục hồi.

Sau khi tải xong có thể chạy offline:

```powershell
$env:HF_HUB_CACHE = "$PWD\.venv\hf-cache"
$env:HF_HUB_OFFLINE = "1"
.\.venv\Scripts\python.exe -m retrieval.verify
```

Tín hiệu hoàn thành: ba dòng `PASS papers-...` và `PASS: three isolated collections, RAG metadata answers, and Mock LLM`.

Để dùng LLM thật, đặt provider, model tương ứng và API key trong `.env`. Kiểm tra khởi tạo provider không chứng minh API key, quota hoặc quyền truy cập model hợp lệ; cần gọi API thực tế để xác nhận các yếu tố đó.
