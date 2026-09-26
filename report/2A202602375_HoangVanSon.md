# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Hoàng Văn Sơn             |
| MSSV               | 2A202602375                     |
| Khóa/Lớp         | K4-L3B              |
| Tên nhóm         | acer     |
| Vai trò chính    | Trưởng nhóm / Pipeline Integrator & Data Foundation                 |
| Repository         | K4-L3B-DAY10-acer-DataPipeline |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Ingestion & Data Fetching | `src/ingestion/crossref.py` (fetch_source_records, parse_crossref_payload) | Truy vấn cấu hình từ `settings` | JSON gốc và danh sách `PaperRecord` | Hoàn thành |
| Data Cleaning | `src/ingestion/cleaning.py` (build_clean_dataframe) | `PaperRecord` list | Cleaned DataFrame `papers_clean.csv` | Hoàn thành |
| Observability | `src/observability/quality.py` (run_data_quality_checks) | Cleaned DataFrame | Báo cáo Great Expectations `baseline_quality_report.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Sửa lỗi model_dump | `cleaning.py` | Sửa lỗi `AttributeError` bằng cách đổi lại logic dùng `r.__dict__` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Lấy dữ liệu bài báo | `data/raw/crossref_records.json` | 24 bài báo khoa học | `python -c "from core.config..."` |
| Làm sạch và chuẩn hoá dữ liệu | `data/clean/papers_clean.json` | Dữ liệu sạch có `text_for_embedding` | `python -c "from ingestion.cleaning..."` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
Tạo ra file dữ liệu sạch đã được tính toán cột `age_days` và chuẩn hóa chuỗi để chuẩn bị cho việc embedding.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng pipeline cơ bản để kéo dữ liệu tự động từ API Crossref, sau đó làm sạch và chuẩn hóa trước khi đưa vào RAG agent để tránh "rác" làm giảm chất lượng retrieval.

### Cách triển khai
- Dùng `requests` gọi Crossref API với điều kiện tìm kiếm và giới hạn số lượng.
- Lưu trữ dữ liệu JSON thô (raw snapshot) để backup và debug.
- Lọc bỏ các bài không có ID/Title, chuyển chuỗi thời gian thành kiểu ngày tháng.
- Dùng Great Expectations để đặt rule kiểm tra các trường thiết yếu (`paper_id`, `summary`) tránh rỗng hoặc trùng lặp.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Metadata JSON từ Crossref API           |
| Output                         | Clean DataFrame và File JSON/CSV chứa data sạch |
| Module phụ thuộc             | `core/config.py`                    |
| Module sử dụng output        | `evaluation/testset.py`, Pipeline vector search                    |
| Điều kiện lỗi cần xử lý | Gọi API thất bại (Timeout/429), dữ liệu thiếu trường |

### Cách xác minh

```bash
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
```
- **Kết quả mong đợi:** In ra `Tín hiệu hoàn thành: Clean thành công 24 dòng`
- **Kết quả thực tế:** In ra đúng như mong đợi.
- **Artifact/log:** `data/raw/crossref_records.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Xử lý dữ liệu trả về từ API Crossref.
- **Các phương án đã cân nhắc:** Dùng Pydantic `BaseModel` hay `dataclass` tiêu chuẩn.
- **Phương án đã chọn:** Dùng `dataclass` tiêu chuẩn và `__dict__`.
- **Lý do:** Giữ code nhẹ nhàng, ít phụ thuộc thư viện ngoài cho việc modeling dữ liệu đơn giản.
- **Bằng chứng quyết định phù hợp:** Chuyển đổi qua lại giữa list dictionary và dataframe diễn ra mượt mà không gặp lỗi validation quá cứng nhắc.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `AttributeError: 'PaperRecord' object has no attribute 'model_dump'`
- **Lệnh hoặc bước tái hiện:** Chạy hàm `build_clean_dataframe`.
- **Nguyên nhân gốc:** `PaperRecord` được định nghĩa là một Python `dataclass`, không phải là Pydantic model nên không có hàm `model_dump()`.
- **Cách xử lý:** Thay `r.model_dump(mode="json")` bằng `r.__dict__`.
- **Cách xác minh sau khi sửa:** Chạy lại file clean và kết quả thành công.
- **Điều học được:** Nắm vững sự khác biệt giữa chuẩn `dataclasses` của Python và thư viện `pydantic`.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   API -> Raw JSON -> Parse thành đối tượng `PaperRecord` -> Chuyển thành Pandas DataFrame -> Làm sạch (xoá trùng, null, thêm cột helper) -> Dùng embedding model mã hoá văn bản -> Lưu vào ChromaDB vector index.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Dùng các câu hỏi (từ test set) truy vấn vào vector index. So sánh ID của document được truy xuất (retrieved) với ground-truth ID trong tập test để tính toán độ chính xác.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks (dùng Great Expectations) bắt lỗi cấu trúc, thiếu dữ liệu, trùng lặp. Freshness kiểm tra "độ tươi" (tuổi) của dữ liệu (ví dụ: cảnh báo nếu số bài báo quá 180 ngày vượt 25%).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính công bằng (A/B Testing), giúp thấy rõ sự sụt giảm đo đếm được khi bị lỗi (corrupted) và sự phục hồi sau đó (repaired).
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Sự quay trở lại mức baseline của các metric như `retrieval_hit_rate` và các file báo cáo GX không còn lỗi/cảnh báo.

## 8. Phân tích kết quả
*(Chưa cập nhật đầy đủ - Đang trong quá trình chạy Pipeline Phase 1 & 2)*

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. Việc quản lý dữ liệu ở nhiều trạng thái (raw, clean) rất quan trọng để có thể rollback (repaired) khi hỏng.
2. Data Observability bằng Great Expectations giúp phát hiện lỗi "im lặng" (silent failures) từ sớm.
3. Chất lượng data đầu vào ảnh hưởng trực tiếp và nghiêm trọng đến chất lượng câu trả lời của RAG Agent.

### Nếu có thêm thời gian
Sẽ thêm cơ chế tự động gửi cảnh báo qua Slack/Email khi pipeline gặp lỗi Data Quality hoặc báo động về Freshness.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hoàng Văn Sơn  
**Ngày xác nhận:** 2026-09-26
