# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                               |
| ----------------- | -------------------------------------------------------------------------------------- |
| Họ và tên         | Phạm Quốc Đạt                                                                          |
| MSSV              | 2A202602384                                                                            |
| Khóa/Lớp          | K4-L3B                                                                                 |
| Tên nhóm          | acer                                                                                   |
| Vai trò chính     | Observability & Evaluation                                                             |
| Repository        | K4-L3B-DAY10-acer-DataPipeline                                                         |
| Ngày hoàn thành   | 2026-09-26                                                                             |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable                     | File/hàm phụ trách                                        | Input nhận vào                              | Output bàn giao                                                         | Trạng thái  |
| -------------------------------------- | --------------------------------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------- | ----------- |
| Benchmark Test Set Generation (Bước 5) | `src/evaluation/testset.py` (`build_test_set`)            | `df` (Cleaned DataFrame từ Bước 3)          | `data/eval/test_set.json` (Bộ 10 câu hỏi Ground Truth chuẩn 4 dạng)    | Hoàn thành  |
| Data Corruption Suite (Bước 7)         | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | `df` (Cleaned DataFrame), `output_log_path` | `corrupted_df` (DataFrame lỗi) & `data/results/corruption_log.json`    | Hoàn thành  |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                      | Thành viên/module được hỗ trợ                                      | Kết quả                                                                                                                                                                             |
| ------------------------------ | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Thống nhất Data Contract       | Hoàng Văn Sơn (`src/ingestion/cleaning.py`)                        | Thống nhất chuẩn schema các cột `authors_joined`, `categories_joined`, `summary` và `text_for_embedding` từ Bước 3 để đầu vào cho bộ sinh test và tiêm lỗi khớp nối chuẩn xác.      |
| Hỗ trợ tích hợp Pipeline Phase 2| Nguyễn Hữu Chương / Hoàng Văn Sơn (`src/pipelines/corruption_flow.py`)| Đảm bảo hàm `corrupt_clean_dataframe` trả về `corrupted_df` đã tái tạo trường `text_for_embedding` phục vụ nạp trực tiếp vào collection `papers-corrupted` của ChromaDB ở Bước 8. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                    | File/hàm/artifact liên quan                               | Kết quả bàn giao                                   | Cách xác minh                                                                                                    |
| -------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Xây dựng bộ câu hỏi Benchmark kiểm thử RAG (10 câu)      | `src/evaluation/testset.py` / `build_test_set`             | `data/eval/test_set.json`                          | Chạy lệnh CLI kiểm thử kiểm tra số lượng câu hỏi sinh ra (10 câu) và cấu trúc JSON đủ 4 dạng bài toán.          |
| Xây dựng bộ công cụ tiêm 6 dạng lỗi thực nghiệm dữ liệu  | `src/ingestion/corruption.py` / `corrupt_clean_dataframe` | `data/results/corruption_log.json`, `corrupted_df` | Chạy lệnh CLI giả lập tiêm lỗi, xác nhận đủ 6 loại lỗi được ghi nhận chi tiết vào tệp nhật ký `corruption_log.json`.|

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
- Tệp `data/eval/test_set.json` chứa đúng 10 câu hỏi chuẩn hóa với ID từ `eval_001` đến `eval_010`, phân bổ đều qua 4 dạng bài toán (`summary`, `authors`, `date`, `categories`), đóng vai trò là Ground Truth độc lập để đo lường định lượng độ chính xác (Hit Rate và Token F1) xuyên suốt cả 3 trạng thái Baseline, Corrupted và Repaired.
- Tệp `data/results/corruption_log.json` lưu vết toàn bộ thông tin biến đổi (trước và sau khi tiêm lỗi) đối với 6 kịch bản dữ liệu bẩn.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Thiếu tập kiểm thử chuẩn hóa khách quan:** Nếu không có bộ câu hỏi Ground Truth cố định và bao quát các trường thông tin chính, hệ thống RAG không thể đo lường định lượng sự suy giảm chất lượng khi gặp sự cố dữ liệu.
2. **Hiện tượng lỗi ngầm (Silent Failure / Data Degradation):** Dữ liệu lỗi trong thực tế (mất tóm tắt, tiêu đề bị cắt cụt, lùi ngày, trùng lặp dòng) không làm sập pipeline (không văng exception cú pháp) nhưng lại khiến vector database lập chỉ mục sai ngữ cảnh, kéo tụt nghiêm trọng chất lượng câu trả lời của LLM. Do đó, cần bộ công cụ mô phỏng chính xác 6 dạng sự cố dữ liệu thực tế này.

### Cách triển khai
- **Bộ tạo Test Set (`testset.py`):**
  - Sử dụng biểu thức chính quy (Regex) bóc tách chính xác câu văn đầu tiên của trường `summary` làm Ground Truth ngắn gọn, súc tích đại diện cho bản tóm tắt.
  - Chuẩn hóa ngày xuất bản về định dạng chuẩn ISO `YYYY-MM-DD`.
  - Phân bổ đều 10 câu hỏi xoay vòng qua 4 dạng bài toán: `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu).
  - Xuất ra JSON có đầy đủ các trường bắt buộc: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.
- **Bộ Tiêm Lỗi (`corruption.py`):**
  - Thao tác trên bản sao `df.copy()` nhằm bảo toàn tính bất biến (immutability) của DataFrame gốc trong bộ nhớ.
  - Lập trình đủ 6 kịch bản lỗi:
    1. *Drop latest records:* Sắp xếp theo `published` giảm dần và cắt bỏ đúng 20% bài báo mới nhất.
    2. *Blank summary:* Xóa trắng trường tóm tắt (`""`) của bản ghi đầu tiên.
    3. *Inject noise:* Chèn chuỗi ký tự rác vào đầu trường tóm tắt.
    4. *Truncate title:* Cắt ngắn tiêu đề xuống dưới 8 ký tự (`[:6]`).
    5. *Stale date:* Trừ ngày xuất bản đi 365 ngày và cập nhật tăng `age_days`.
    6. *Duplicate rows:* Nhân đôi 1 bản ghi và đưa ngược lại DataFrame.
  - **Tái tạo ngữ cảnh embedding (`_rebuild_text_for_embedding`):** Sau khi sửa tiêu đề hoặc tóm tắt, thực hiện ghép lại trường `text_for_embedding` theo đúng cấu trúc chuẩn của Bước 3 để vector embedding của tài liệu thực sự bị sai lệch khi nạp vào ChromaDB.
  - Ghi toàn bộ lịch sử biến đổi ra `data/results/corruption_log.json`.

### Input, output và contract

| Thành phần              | Mô tả                                                                                                                                           |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                   | `pd.DataFrame` sạch chứa các cột: `paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `text_for_embedding`.   |
| Output                  | `data/eval/test_set.json` (List[Dict] 10 câu hỏi benchmark) và `data/results/corruption_log.json` cùng DataFrame lỗi `corrupted_df`.          |
| Module phụ thuộc        | `src/ingestion/cleaning.py` (Cung cấp schema dữ liệu sạch), `src/core/config.py` (Cung cấp cấu hình đường dẫn lưu trữ `Paths`).               |
| Module sử dụng output   | `src/pipelines/phase1.py` (sử dụng testset), `src/pipelines/corruption_flow.py` (sử dụng `corrupted_df` để index và đối chiếu suy giảm RAG). |
| Điều kiện lỗi cần xử lý | Xử lý `published` bị sai lệch kiểu dữ liệu hoặc NaT; xử lý an toàn khi số dòng dữ liệu nhỏ hơn 10 dòng; tự tạo thư mục cha nếu chưa tồn tại.  |

### Cách xác minh

```bash
# Xác minh Bước 5: Sinh tập Benchmark Testset
python -c "from evaluation.testset import build_test_set; import pandas as pd; df=pd.DataFrame([{'paper_id': f'10.1000/{i}', 'title': f'Paper {i}', 'summary': f'Sentence one of {i}. Sentence two.', 'published': '2024-01-01', 'authors_joined': 'Alice, Bob', 'categories_joined': 'CS.AI'} for i in range(10)]); r=build_test_set(df, 'data/eval/test_set.json'); print(f'Tín hiệu hoàn thành: Sinh được {len(r)} câu hỏi test .')"

# Xác minh Bước 7: Tiêm 6 dạng lỗi thực nghiệm
python -c "import pandas as pd; from datetime import timezone; from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; s=load_settings(); df=pd.DataFrame([{'paper_id': f'10.1000/{i}', 'title': f'Research Paper Long Title Number {i}', 'summary': f'This is the full summary for paper {i}. Detailed experimental observations.', 'published': pd.Timestamp.now(timezone.utc) - pd.Timedelta(days=i*10), 'authors_joined': f'Author A{i}, Author B{i}', 'categories_joined': 'cs.AI, cs.LG', 'summary_chars': 70} for i in range(10)]); c_df=corrupt_clean_dataframe(df, s.paths.corruption_log); print('Tín hiệu hoàn thành: Nhật ký lỗi data/results/corruption_log.json được ghi lại chi tiết.')"
```

- **Kết quả mong đợi:** Cả hai lệnh chạy trơn tru, xuất ra đúng định dạng JSON và in tín hiệu hoàn thành ra console.
- **Kết quả thực tế:** Console in ra: `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test .` và `Tín hiệu hoàn thành: Nhật ký lỗi data/results/corruption_log.json được ghi lại chi tiết.`
- **Artifact/log:** `data/eval/test_set.json` và `data/results/corruption_log.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi thực hiện tiêm lỗi ở Bước 7, sau khi làm rỗng tóm tắt (`blank_summary`) hoặc cắt ngắn tiêu đề (`truncate_title`), có cần phải xây dựng lại chuỗi văn bản ở cột `text_for_embedding` hay không?
- **Các phương án đã cân nhắc:**
  - *Phương án A:* Chỉ chỉnh sửa giá trị trên các cột đơn lẻ (`title`, `summary`), giữ nguyên cột `text_for_embedding` ban đầu để tối ưu thời gian xử lý.
  - *Phương án B:* Viết thêm hàm phụ trợ `_rebuild_text_for_embedding` để ghép lại toàn bộ chuỗi văn bản biểu diễn tài liệu theo các giá trị vừa bị biến đổi.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Ở downstream pipeline (Bước 8), module Embedding và Vector Database sẽ sử dụng trực tiếp cột `text_for_embedding` để sinh vector biểu diễn. Nếu chọn Phương án A, vector database vẫn index nội dung sạch ban đầu, dẫn đến việc thử nghiệm tiêm lỗi không có tác động thực tiễn và không phản ánh được hiện tượng suy giảm hiệu năng retrieval của hệ thống RAG.
- **Bằng chứng quyết định phù hợp:** Đảm bảo khi chạy Phase 2 đối chiếu hiệu năng, dữ liệu trong ChromaDB collection `papers-corrupted` phản ánh trung thực trạng thái lỗi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  FileNotFoundError: [Errno 2] No such file or directory: '.../data/clean/papers_clean.csv'
  NotImplementedError: Student task: implement corruption flow.
  ```
- **Lệnh hoặc bước tái hiện:** Chạy lệnh kiểm thử gọi tệp `papers_clean.csv` khi các bước upstream (Bước 2, Bước 3, Bước 6) chưa chạy toàn tuyến trên máy cục bộ, hoặc chạy khi tệp mã nguồn chưa được lưu hoàn tất trên IDE.
- **Nguyên nhân gốc:** Thư mục `data/` bị loại trừ bởi `.gitignore` nên các tệp dữ liệu sạch không đồng bộ từ repository của các thành viên khác về máy cá nhân. Đồng thời, tệp `corruption.py` trên ổ cứng vẫn giữ nguyên code mẫu `raise NotImplementedError` do chưa hoàn thành lưu mã nguồn mới.
- **Cách xử lý:** 
  1. Cập nhật và lưu dứt điểm code hoàn thiện vào `src/ingestion/corruption.py`.
  2. Xây dựng câu lệnh kiểm thử độc lập (Isolated Unit Test) bằng cách giả lập DataFrame có schema chuẩn của Bước 3 để kiểm tra logic thuật toán của Bước 5 và Bước 7 mà không bị phụ thuộc vào tệp dữ liệu trung gian trên đĩa.
- **Cách xác minh sau khi sửa:** Chạy script kiểm thử độc lập trên PowerShell thành công 100%, sau đó kiểm tra tệp `corruption_log.json` sinh ra đầy đủ 6 bản ghi lỗi.
- **Điều học được:** Khi phát triển pipeline phân tán theo nhóm, cần thiết kế các module có tính tách rời (decoupled) cao và luôn chuẩn bị mock data/isolated unit tests để kiểm chứng logic nội tại trước khi ghép nối toàn tuyến.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   API Crossref -> Dữ liệu JSON thô (lưu tại `data/raw/` để làm Lineage Anchor) -> Parse thành đối tượng `PaperRecord` -> Chuyển thành Pandas DataFrame -> Làm sạch ở `cleaning.py` (loại bỏ thẻ rác, tính `age_days`, tạo cột `text_for_embedding`, xoá trùng lặp) -> Dùng embedding model `sentence-transformers` mã hóa -> Lưu vào bộ sưu tập ChromaDB.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Dùng các câu hỏi chuẩn từ `test_set.json` truy vấn vào vector database. So sánh ID của tài liệu được ChromaDB trả về với `ground_truth_doc_ids` để tính `retrieval_hit_rate`, đồng thời đo độ tương đồng giữa câu trả lời sinh ra từ LLM với chuỗi `ground_truth` để tính điểm `mean_token_f1`.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks (Great Expectations) bắt lỗi cấu trúc, thiếu dữ liệu bắt buộc, vi phạm tính duy nhất. Freshness monitoring theo dõi độ tươi mới của dữ liệu dựa trên thời gian xuất bản (gắn cờ cảnh báo nếu tỷ lệ bài báo quá 180 ngày vượt mốc trần 25%).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính nhất quán của thước đo đánh giá (Ground Truth Benchmark). Dùng chung 1 tập 10 câu hỏi cố định giúp thấy rõ định lượng sự sụt giảm hiệu năng khi bị tiêm lỗi và khả năng hồi phục sau khi sửa chữa mà không bị thiên lệch bởi câu hỏi khác nhau.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - *Về Artifact:* Khôi phục sạch lại dữ liệu từ snapshot gốc `data/raw/crossref_response.json` và nạp vào collection `papers-repaired`.
   - *Về Metric:* Các chỉ số RAG (`retrieval_hit_rate`, `mean_token_f1`) hồi phục trở lại tiệm cận mức Baseline, đồng thời báo cáo Great Expectations và Freshness đạt trạng thái hợp lệ (PASSED / FRESH).

## 8. Phân tích kết quả

*(Hiện tại Pipeline toàn tuyến Phase 1 và Phase 2 đang được Trưởng nhóm Hoàng Văn Sơn và nhóm tích hợp chạy đo lường; các chỉ số định lượng chi tiết sẽ được cập nhật đồng bộ sau khi script toàn tuyến hoàn tất.)*

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Quản lý đa trạng thái dữ liệu (Raw & Clean):** Luôn lưu giữ snapshot dữ liệu thô ban đầu để làm điểm tựa Lineage phục hồi hệ thống khi có sự cố mà không phụ thuộc vào API bên thứ ba.
2. **Data Observability bằng Great Expectations:** Đóng vai trò là chốt chặn quan trọng giúp phát hiện lỗi cấu trúc và "lỗi im lặng" (silent failures) từ sớm trước khi nạp vào Vector Database.
3. **Chất lượng dữ liệu quyết định chất lượng AI:** Dữ liệu bẩn ảnh hưởng trực tiếp đến chất lượng retrieval và suy luận của LLM, nhấn mạnh tầm quan trọng của việc kiểm soát chất lượng dữ liệu trong các hệ thống RAG thực tế.

### Nếu có thêm thời gian
Sẽ nghiên cứu xây dựng thêm cơ chế **Tự động sinh Testset động bằng LLM (LLM-assisted Synthetic Test Generation)** thay vì dùng template cố định, nhằm đa dạng hóa câu hỏi (suy luận, phủ định) để kiểm tra độ bền vững (robustness) của pipeline toàn diện hơn.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Quốc Đạt  
**Ngày xác nhận:** 2026-09-26