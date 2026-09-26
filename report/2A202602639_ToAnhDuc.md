# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Tô Anh Đức |
| MSSV | 2A202602639 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | haianh |
| Vai trò chính | Pipeline integration, kiểm tra Data Observability và dashboard |
| Repository | https://github.com/AnhDuc0712/K4-L3B-DAY10-haianh-DataPipelineDataObservability |
| Ngày xác nhận | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Pipeline integration và Data Observability | `src/pipelines/phase1.py`, `src/observability/quality.py`, `src/observability/reporting.py` | Raw records, clean dataframe và settings | Baseline metrics, quality/freshness reports và `phase1_report.md` | Hoàn thành |
| Corruption, repair và dashboard | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`, `app.py`, `src/ui/artifacts.py` | Clean dataset, raw snapshot và evaluation set | `corruption_log.json`, corrupted/repaired metrics, `corruption_report.md` và Streamlit dashboard | Hoàn thành |

Mình trực tiếp thực hiện và kiểm tra các phần trên. Pipeline sử dụng output từ ingestion
và cleaning; quality, evaluation và dashboard phụ thuộc vào clean artifacts. Corruption
flow sử dụng clean dataset, còn repair phụ thuộc vào raw snapshot để khôi phục dữ liệu.

## 3. Kết quả và bằng chứng

### Artifact thực tế

```text
app.py
src/ui/artifacts.py
script/run_phase1.py
script/run_corruption_flow.py
data/results/baseline_metrics.json
data/results/corrupted_metrics.json
data/results/repaired_metrics.json
data/results/corruption_log.json
data/quality/baseline_quality_report.json
data/quality/corrupted_quality_report.json
data/quality/repaired_quality_report.json
data/reports/phase1_report.md
data/reports/corruption_report.md
```

### Các lệnh tái hiện và kiểm tra

```powershell
python script/run_phase1.py
python script/run_corruption_flow.py
python -m compileall -q src script
streamlit run app.py
```

Kết quả kiểm tra hiện có:

- `src` và `script` compile thành công.
- Các artifact baseline, corrupted và repaired đều tồn tại.
- `data/results/corruption_log.json` ghi nhận đủ 6 corruption scenarios.
- `streamlit run app.py` chưa chạy được vì `app.py` còn lỗi `IndentationError: unexpected indent` tại dòng 130.
- Hai pipeline command cần được chạy lại lần cuối trước khi nộp để xác nhận exit code của source hiện tại.

## 4. Giải thích kỹ thuật

### Vấn đề pipeline giải quyết

Pipeline mô phỏng một quy trình RAG có observability: dữ liệu học thuật được thu thập, làm sạch, lập chỉ mục và đánh giá; sau đó dữ liệu bị tiêm lỗi có kiểm soát để đo mức suy giảm; cuối cùng hệ thống rebuild từ raw snapshot để kiểm tra khả năng repair.

### Luồng dữ liệu từ Crossref đến ChromaDB

1. Crossref response được lưu tại `data/raw/crossref_response.json` và parse thành `data/raw/crossref_records.json`.
2. Cleaning tạo `papers_clean.csv/json`, chuẩn hóa text, tính `age_days`, loại duplicate theo `paper_id` và tạo `text_for_embedding`.
3. Embedding model tạo vector cho các clean records và lưu index trong `data/chroma/`; embedding artifacts được lưu trong `data/embeddings/`.
4. Retrieval dùng vector index và metadata để lấy context cho test set.
5. Baseline, corrupted và repaired đều dùng cùng `data/eval/test_set.json` để kết quả có thể so sánh.

### Vai trò của quality check và freshness

Quality check dùng các expectation cho row count, not-null, uniqueness và độ dài text. Freshness kiểm tra `age_days > 180`; dataset chỉ được xem là fresh khi tỷ lệ stale không vượt 25%. Quality report cho thấy baseline và repaired PASS, còn corrupted FAIL; freshness của cả ba trạng thái vẫn FRESH vì stale ratio chưa vượt ngưỡng.

### Vì sao phải dùng cùng test set

Dùng cùng 10 câu hỏi và cùng ground-truth document IDs giúp khác biệt metrics phản ánh tác động của corruption/repair, thay vì phản ánh sự khác nhau của bộ câu hỏi. Test set hiện có đủ bốn loại: `summary`, `authors`, `date` và `categories`.

### Repair phục hồi dựa trên artifact và metric nào

Repair rebuild clean data từ `data/raw/crossref_records.json`, sau đó tạo lại embeddings/index, chạy quality check và evaluation. Bằng chứng phục hồi gồm:

- `data/quality/repaired_quality_report.json`: `success=True`.
- `data/results/repaired_metrics.json`: Hit Rate `1.0`, Token F1 `0.5`.
- `data/reports/corruption_report.md`: bảng Baseline vs Corrupted vs Repaired.

## 5. Metrics đã xác nhận

Các số dưới đây được đọc từ `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json` và `data/results/repaired_metrics.json`.

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| `retrieval_hit_rate` | 1.0 | 0.9 | 1.0 |
| `mean_token_f1` | 0.5 | 0.4 | 0.5 |
| `judge_accuracy` | 0.5 | 0.4 | 0.5 |
| `mean_judge_score` | 3.0 | 2.7 | 3.0 |
| `samples` | 10 | 10 | 10 |
| Quality checks | PASS | FAIL | PASS |
| Freshness status | FRESH | FRESH | FRESH |

Ragas không được dùng để suy ra các số trên; cả ba metrics JSON đều ghi rõ Ragas pass được skip nếu chưa bật `RUN_RAGAS=1`.

## 6. Lỗi hoặc blocker đã xử lý

### Lỗi dữ liệu trong quá trình repair

- **Lỗi:** Giá trị summary rỗng từ CSV có thể được pandas đọc thành `NaN` float.
- **Nguyên nhân:** CSV và JSON có cách biểu diễn giá trị rỗng khác nhau.
- **Cách xử lý:** Chuẩn hóa giá trị rỗng trước khi ghép `text_for_embedding` và rebuild context.
- **Bằng chứng:** Repaired dataset có 24 rows, repaired quality report PASS và repaired metrics trở lại baseline.

### Blocker dashboard hiện tại

- **Lỗi thực tế:** `IndentationError: unexpected indent` tại `app.py:130`.
- **Nguyên nhân:** Dòng caption freshness bị thụt lề ngoài phạm vi block/hàm phù hợp.
- **Tác động:** Chưa thể xác nhận dashboard bằng `streamlit run app.py`.
- **Bước tiếp theo:** Sửa indentation, sau đó chạy lại Streamlit và kiểm tra các tab pipeline, quality, freshness và comparison.

## 7. Hai chuỗi nguyên nhân–bằng chứng

### Chuỗi 1: Corruption làm giảm chất lượng RAG

```text
Blank summary / noise / truncated title / dropped records
→ context và coverage bị suy giảm
→ retrieval_hit_rate: 1.0 → 0.9
→ mean_token_f1: 0.5 → 0.4
→ corrupted_quality_report.json: success=False
```

Bằng chứng: `data/results/corruption_log.json`, `data/results/corrupted_metrics.json` và `data/quality/corrupted_quality_report.json`.

### Chuỗi 2: Repair từ raw phục hồi kết quả

```text
Raw snapshot đáng tin cậy
→ rebuild clean records và embeddings/index
→ quality gate: FAIL → PASS
→ retrieval_hit_rate: 0.9 → 1.0
→ mean_token_f1: 0.4 → 0.5
```

Bằng chứng: `data/quality/repaired_quality_report.json`, `data/results/repaired_metrics.json` và `data/reports/corruption_report.md`.

## 8. Một quyết định kỹ thuật quan trọng

Mình chọn repair bằng cách rebuild từ `data/raw/crossref_records.json` thay vì sửa trực tiếp corrupted dataframe. Cách này giữ data lineage, dễ tái lập và giảm nguy cơ mang lỗi cũ sang repaired dataset. Kết quả là repaired dataset có 24 rows, quality gate PASS và metrics trở về baseline.

## 9. Điều học được và hướng cải thiện

### Ba điều học được

1. Pipeline integration cần kiểm tra cả artifact path, schema và metrics giữa các stage; chỉ thấy một file output tồn tại chưa đủ chứng minh flow đúng.
2. Quality check và freshness bổ sung cho nhau: quality phát hiện lỗi schema/content, còn freshness chỉ phản ánh tuổi dữ liệu theo SLA.
3. So sánh baseline/corrupted/repaired chỉ có ý nghĩa khi giữ nguyên evaluation set, metric definition và điều kiện truy xuất.

### Nếu có thêm thời gian

Mình sẽ sửa `app.py`, chạy lại dashboard bằng `streamlit run app.py`, sau đó bổ sung pytest cho pipeline integration, quality gate và comparison report. Cuối cùng sẽ chạy lại hai pipeline command và lưu exit code/log làm bằng chứng cuối cùng.

## 10. Cam kết của thành viên

- [x] Ownership chỉ bao gồm phần pipeline integration, kiểm tra flow, dashboard và tổng hợp report mà mình trực tiếp phụ trách.
- [x] Report có đường dẫn artifact thực tế trong repository.
- [x] Metrics được đối chiếu từ JSON/report hiện có, không tự đoán số liệu.
- [x] Report có giải thích pipeline, quality, freshness, cùng evaluation set và repair.
- [x] Report có lỗi/blocker, nguyên nhân, tác động và bước tiếp theo.
- [x] Report không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** Tô Anh Đức  
**MSSV:** 2A202602639  
**Ngày xác nhận:** 2026-09-26
