# Báo cáo cá nhân — Nguyễn Việt Hoàng

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Nguyễn Việt Hoàng |
| MSSV | 02424 |
| Khóa/Lớp | K4-L3-DAY10 |
| Tên nhóm | [BỔ SUNG TÊN NHÓM] |
| Vai trò chính | Data Corruption & Repair |
| Repository | https://github.com/thaihoaho-code/K4-L3B-DAY10-5AE-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File/hàm phụ trách | Input | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Data corruption suite | `src/ingestion/corruption.py` / `corrupt_clean_dataframe` | Clean dataframe | Corrupted dataframe và `data/results/corruption_log.json` | Hoàn thành |
| Corruption flow và repair | `src/pipelines/corruption_flow.py` / `run_corruption_flow_pipeline`, `repair_from_raw_snapshot` | Baseline artifacts, raw snapshot, evaluation set | Corrupted/repaired artifacts, metrics và comparison report | Hoàn thành |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/artifact | Kết quả | Cách xác minh |
|---|---|---|---|
| Tiêm 6 dạng lỗi dữ liệu | `src/ingestion/corruption.py` | 24 bản ghi đầu vào tạo thành 20 bản ghi corrupted; log có đủ 6 scenario | Unit test trên snapshot local |
| Đo lường và phục hồi | `src/pipelines/corruption_flow.py` | Retrieval hit rate `1.0 → 0.5 → 1.0`; Token F1 `0.487 → 0.217 → 0.487` | `data/results/*_metrics.json` và `data/reports/corruption_report.md` |

Artifact chính:

- `data/results/corruption_log.json`
- `data/clean/papers_clean_corrupted.json`
- `data/clean/papers_clean_repaired.json`
- `data/results/corrupted_metrics.json`
- `data/results/repaired_metrics.json`
- `data/reports/corruption_report.md`

## 4. Giải thích kỹ thuật

### Vấn đề cần giải quyết

Pipeline cần mô phỏng dữ liệu bẩn trong production, đo được mức suy giảm của hệ thống RAG, sau đó phục hồi từ nguồn đáng tin cậy thay vì sửa trực tiếp dữ liệu đã bị biến đổi.

### Cách triển khai

`corrupt_clean_dataframe` tạo bản copy độc lập của clean dataframe và áp dụng deterministic các scenario: bỏ 20% bài mới nhất, blank summary, inject noise, truncate title dưới 8 ký tự, lùi ngày xuất bản 365 ngày và duplicate row. Sau đó các trường dẫn xuất được rebuild và toàn bộ `paper_id` bị tác động được ghi vào corruption log.

`run_corruption_flow_pipeline(settings)` lưu corrupted artifacts, build collection `papers-corrupted`, chạy evaluation trên cùng evaluation set, gọi `repair_from_raw_snapshot(settings)`, build collection `papers-repaired`, chạy lại evaluation và tạo báo cáo so sánh.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | `data/clean/papers_clean.json`, `data/raw/crossref_records.json`, `data/eval/test_set.json`, baseline metrics |
| Output | Corruption log, corrupted/repaired clean data, Chroma manifests, metrics và comparison report |
| Module phụ thuộc | `cleaning.py`, `crossref.py`, `quality.py`, `evaluation/metrics.py`, `retrieval/index.py`, `reporting.py` |
| Module sử dụng output | Quality gate, evaluation, report và live demo |
| Điều kiện lỗi | Thiếu baseline artifact, thiếu raw snapshot, dataframe rỗng hoặc report không được tạo |

### Cách xác minh

```bash
python -m compileall -q src/ingestion/corruption.py src/pipelines/corruption_flow.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Console có ba cột Baseline/Corrupted/Repaired và report được tạo.
- **Kết quả đã đối chiếu:** `retrieval_hit_rate` giảm từ `1.0` xuống `0.5`, sau repair trở lại `1.0`; `mean_token_f1` giảm từ `0.4869` xuống `0.2165`, sau repair trở lại `0.4869`.
- **Artifact/log:** `data/results/corruption_log.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md`.

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh:** Có thể cố gắng đảo ngược từng corruption hoặc dựng lại toàn bộ dữ liệu từ raw snapshot.
- **Các phương án:** (1) reverse mutation trên dataframe corrupted; (2) đọc lại `crossref_records.json` và chạy lại cleaning.
- **Phương án đã chọn:** Dựng lại từ raw snapshot qua `repair_from_raw_snapshot`.
- **Lý do:** Raw snapshot là nguồn bất biến; cách này idempotent, không phụ thuộc corruption log và tránh giữ lại lỗi tiềm ẩn.
- **Bằng chứng:** Repaired dataset có 24 dòng, quality gate pass và metrics trở lại bằng baseline.

## 6. Lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Hàm corruption và corruption flow ban đầu còn `NotImplementedError`.
- **Nguyên nhân:** Hai file chỉ có scaffold/TODO, chưa có logic tiêm lỗi, repair và evaluation.
- **Cách xử lý:** Triển khai 6 scenario, public pipeline API, repair từ raw và artifact validation.
- **Cách xác minh:** Compile test, unit test với snapshot 24 bài báo và đối chiếu artifacts trên `main`.
- **Giới hạn còn lại:** Corrupted freshness có 2/20 stale rows, tỷ lệ `0.1` nên vẫn dưới SLA fail threshold `0.25`; quality gate vẫn fail do duplicate và blank summary.

## 7. Hiểu biết về luồng end-to-end

Raw Crossref records được cleaning thành dataframe, sau đó embedding và index vào ChromaDB. Evaluation set giữ nguyên cho ba trạng thái để so sánh công bằng. Corruption tạo dữ liệu lỗi và làm giảm retrieval/answer metrics. Repair đọc lại raw snapshot, cleaning lại từ đầu, tạo collection repaired và đánh giá lại. Repair thành công khi dữ liệu sạch, quality gate pass và metrics phục hồi so với baseline.

## 8. Phân tích kết quả

| Metric | Baseline | Corrupted | Repaired | Nhận xét |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0 | 0.5 | 1.0 | Giảm 50%, phục hồi hoàn toàn |
| `mean_token_f1` | 0.4869 | 0.2165 | 0.4869 | Chất lượng câu trả lời giảm rồi phục hồi |
| `judge_accuracy` | 0.5 | 0.2 | 0.5 | Phục hồi về baseline |
| `mean_judge_score` | 2.8 | 1.8 | 2.8 | Phục hồi về baseline |
| Quality checks | True | False | True | Duplicate và blank summary bị phát hiện |
| Freshness status | True | True | True | Stale ratio 0.1 chưa vượt ngưỡng 0.25 |

Chuỗi bằng chứng thứ nhất là: blank summary/duplicate và các biến đổi nội dung → quality gate fail, retrieval hit rate giảm `1.0 → 0.5` và Token F1 giảm `0.4869 → 0.2165`.

Chuỗi thứ hai là: rebuild từ raw snapshot → dataset 24 dòng, quality pass → retrieval hit rate và Token F1 trở lại baseline.

## 9. Điều học được và hướng cải thiện

1. Corruption suite cần deterministic để kết quả giữa các lần chạy có thể đối chiếu.
2. Repair an toàn nên bắt đầu lại từ nguồn raw đáng tin cậy, không sửa ngược trên dữ liệu lỗi.
3. Data quality và dữ liệu embedding có ảnh hưởng trực tiếp đến retrieval và câu trả lời của RAG.

Nếu có thêm thời gian, nên tăng số dòng stale lên trên 25% để freshness SLA cũng phát tín hiệu fail, đồng thời chuẩn hóa đường dẫn ChromaDB theo dạng portable thay vì đường dẫn tuyệt đối của một máy.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc của tôi.
- [x] Tôi có thể giải thích luồng end-to-end và phần mình phụ trách.
- [x] Kết luận có artifact hoặc metric để đối chiếu.
- [x] Không ghi nhận thành công cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa API key, token hoặc secret.
- [x] Báo cáo này là báo cáo riêng, không sao chép nguyên văn báo cáo nhóm.

**Họ và tên:** Nguyễn Việt Hoàng

**MSSV:** 02424
**Ngày xác nhận:** 2026-09-26
