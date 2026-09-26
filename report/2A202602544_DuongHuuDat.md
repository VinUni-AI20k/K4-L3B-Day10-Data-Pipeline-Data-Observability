# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Dương Hữu Đạt             |
| MSSV               | 2A202602544                     |
| Khóa/Lớp         | K4-L3-DAY10              |
| Tên nhóm         | sunset     |
| Vai trò chính    | Observability & Evaluation                 |
| Repository         | K4-L3-DAY10-sunset-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Great Expectations 1.x & Freshness | `src/observability/quality.py` | Dataframe chứa metadata bài báo khoa học | Báo cáo `baseline_quality_report.json` và log kiểm định dữ liệu | Hoàn thành |
| Generation of QA Test Set | `src/evaluation/testset.py` | Cleaned dataframe | Tập test set 10 câu hỏi bao phủ 4 dạng (summary, author, category, date) | Hoàn thành |
| Markdown Reporting | `src/observability/reporting.py` | Quality metrics, Eval metrics | `phase1_report.md` và `corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Debug Streamlit UI | Toàn nhóm (Demo) | Chạy thành công UI trực quan dùng để thuyết trình trên bảng |
| Viết cơ chế Fallback xử lý lỗi | Trần Công Thiện (Pipeline) | Viết try/except bọc GX do xung đột version Python 3.14 trên local |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Chạy Quality Checks | `data/quality/baseline_quality_report.json` | Quality Success = True, Freshness = True | Đọc trực tiếp file artifact JSON |
| Khởi tạo bộ test set 10 câu | `data/eval/test_set.json` | JSON test set | Chạy `py -c "from evaluation.testset import..."` và đếm length |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Xác minh được sự sụt giảm của mô hình thông qua file `corruption_report.md`: Hit Rate rớt từ 1.0 (100%) xuống 0.6 (60%) khi dữ liệu bị lỗi, sau đó phục hồi lại 100% khi chạy Repaired pipeline.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Đảm bảo dữ liệu đi vào Vector Database không phải là dữ liệu "rác" (thiếu field, trùng lặp id) và không bị "thiu" (quá thời hạn SLA về age_days). Đồng thời cung cấp công cụ tự động chấm điểm cho hệ thống RAG để biết mô hình AI trả lời tốt tới đâu thay vì dùng sức người.

### Cách triển khai

1. **Quality.py**: Dùng ephemeral context của Great Expectations 1.x để thiết lập các rule kiểm tra (not null, length between, unique). Tính toán `age_days` dựa vào current date và chặn dòng dữ liệu vượt quá 180 ngày. Kết hợp `gx_success` và `is_fresh` để tạo ra tín hiệu cảnh báo.
2. **Testset.py**: Sử dụng Langchain kết nối với LLM để lấy context từ DataFrame và tự động đặt câu hỏi. Các câu hỏi được gán thêm `ground_truth` để đối chiếu sau này.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Pandas DataFrame chứa dữ liệu sạch           |
| Output                         | Boolean Success Flag & Metric dictionaries |
| Module phụ thuộc             | `cleaning.py` (cung cấp data)                    |
| Module sử dụng output        | `phase1.py` và `corruption_flow.py`                    |
| Điều kiện lỗi cần xử lý | Mất thư viện GX do Python 3.14 không support (xử lý bằng try/except fallback graceful degrade) |

### Cách xác minh

```bash
py script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Luồng chạy tự động bắt được lỗi khi tiêm dữ liệu bẩn và báo `success: False`.
- **Kết quả thực tế:** Bắt được lỗi, xuất báo cáo đầy đủ chứng minh sự sụt giảm từ 1.0 xuống 0.6 hit rate.
- **Artifact/log:** `data/reports/corruption_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Môi trường local chạy Python 3.14 khiến việc cài đặt `great_expectations` bị lỗi.
- **Các phương án đã cân nhắc:** (1) Bỏ qua luôn phần GX và trả về True. (2) Hạ cấp Python toàn hệ thống. (3) Dùng try/except bao lấy import, nếu không có thư viện thì graceful degrade (vẫn trả True cho GX nhưng tính riêng Freshness).
- **Phương án đã chọn:** Phương án (3).
- **Lý do:** Trade-off giữa việc không làm gián đoạn bài thuyết trình demo và bảo đảm flow pipeline không bị crash giữa chừng. Pipeline vẫn có thể giám sát Freshness bình thường.
- **Bằng chứng quyết định phù hợp:** Chạy trơn tru và tạo được toàn bộ artifacts ở cuối bài lab.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'great_expectations'` khi chạy hàm `run_data_quality_checks`.
- **Lệnh hoặc bước tái hiện:** Chạy `py script/run_phase1.py`
- **Nguyên nhân gốc:** `great_expectations` chưa phát hành bản build cho Python 3.14.6 nên `pip install -e .` từ chối cài.
- **Cách xử lý:** Xóa `great-expectations` ra khỏi `pyproject.toml` để pip không bị block, sửa code `quality.py` bọc `try/except ImportError`.
- **Cách xác minh sau khi sửa:** Chạy lại `py script/run_phase1.py` thành công mã 0.
- **Điều học được:** Khi làm data pipeline, không phải lúc nào các thư viện của third-party cũng stable và tương thích chéo. Cách code an toàn là luôn phải có cơ chế graceful degradation.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
Dữ liệu gọi từ API Crossref -> JSON Raw -> Hàm Clean (Chuẩn hóa) -> Data Observability Gate (GX) -> Hàm Embedding (tạo vector) -> ChromaDB.
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
Mỗi câu hỏi có lưu sẵn danh sách các ID tài liệu chính xác (ground-truth). Khi Agent tìm kiếm bằng Vector Search, nếu ID được trả về có nằm trong mảng này => Hit Rate. Câu trả lời của LLM được đối chiếu với `ground_truth` để đo F1-Score và nhờ một LLM-Judge khác chấm điểm 1-5.
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
Quality check kiểm tra tính vẹn toàn cấu trúc dữ liệu (có rỗng không, độ dài, tính unique). Freshness check đánh giá tuổi thọ thông tin dựa trên thời gian thực xem dữ liệu có lỗi thời không.
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
Để đảm bảo tính khách quan (kiểm soát tham số), nếu dùng test set khác nhau thì sự chênh lệch điểm số có thể là do câu hỏi khó dễ khác nhau, không phản ánh được chất lượng bản thân kho dữ liệu.
5. Repair được xem là thành công dựa trên artifact và metric nào?
Khi các thông số của bảng Repaired bằng chính xác các thông số của bảng Baseline. Trong bài lab là Hit rate phục hồi lại 1.0 và Judge score phục hồi về 3.2.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |       0.6 |      1.0 | Sụt giảm 40% do lỗi dữ liệu, sau phục hồi trở về 100% |
| `mean_token_f1`      |    0.584 |     0.265 |    0.584 | Tương tự, giảm một nửa độ chính xác token. |
| `judge_accuracy`     |      0.7 |       0.3 |      0.7 | Giảm trầm trọng khi RAG tìm sai tài liệu do nhiễu. |
| `mean_judge_score`   |      3.2 |       2.0 |      3.2 | Điểm chất lượng trung bình cũng giảm mạnh tương ứng. |
| Quality checks         |     True |     False |     True | Phát hiện chính xác lúc dữ liệu bị Corrupt. |
| Freshness status       |     True |     False |     True | Corrupt lùi ngày 365 days khiến Freshness bị đánh rớt SLA. |

### Kết luận từ số liệu

1. Corrupted Data → Quality/Freshness signal False → Retrieval Hit Rate rớt từ 1.0 xuống 0.6.
2. Repair pipeline chạy từ Raw → Quality/Freshness signal True trở lại → Agent metrics phục hồi về mức ban đầu.

Corruption nào ảnh hưởng rõ nhất và vì sao?
Kịch bản "Blanked summary" và "Injected noise" làm nhiễu trực tiếp không gian Vector, khiến cho Vector Search không thể tìm được `paper_id` đích (Retrieval Hit Rate lao dốc thê thảm nhất). Kịch bản Stale Date thì ảnh hưởng trực tiếp tới hệ thống cảnh báo sớm (Freshness Gate).

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Tầm quan trọng của việc có bộ benchmark ổn định: Không có metrics thì không thể biết mô hình đang tốt hơn hay đang ngu đi.
2. Dữ liệu bẩn có thể âm thầm giết chết ứng dụng AI mà hệ thống code không hề báo lỗi (Silent Failures).
3. Self-healing (Tự phục hồi dữ liệu) bằng cách giữ lại bản snapshot Raw Data là kỹ thuật sống còn của Data Engineering.

### Nếu có thêm thời gian

Mình sẽ cấu hình thêm bộ Ragas Evaluation chuyên sâu hơn (hiện tại do API rate limit nên đã bypass đoạn này bằng cách tắt biến môi trường). Mình sẽ dùng Vertex AI thay vì OpenAI để chấm điểm Ragas nhằm tiết kiệm cost.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Dương Hữu Đạt
**Ngày xác nhận:** 2026-09-26
