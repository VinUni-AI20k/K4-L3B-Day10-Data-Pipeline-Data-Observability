# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Tô Anh Đức |
| MSSV | 2A202602639 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | haianh |
| Vai trò chính | Pipeline integration, Data Observability và dashboard |
| Repository | https://github.com/AnhDuc0712/K4-L3B-DAY10-haianh-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Pipeline integration | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | Settings và các artifact pipeline | Baseline, corrupted và repaired flow | Hoàn thành |
| Data Observability | `src/observability/quality.py`, `src/observability/reporting.py` | Clean/corrupted/repaired dataframe | Quality, freshness và comparison reports | Hoàn thành |
| Dashboard | `app.py`, `src/ui/artifacts.py` | Các artifact local | Streamlit dashboard | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Kiểm tra tích hợp | Ingestion, cleaning, retrieval và evaluation | Xác nhận các artifact liên kết đúng giữa các stage |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Hoàn thiện corruption flow | `corruption.py`, `corruption_flow.py` | 6 corruption scenarios và `corruption_log.json` | `python script/run_corruption_flow.py` |
| Hoàn thiện repair và comparison | `corruption_flow.py`, `reporting.py` | `repaired_metrics.json`, `corruption_report.md` | So sánh metrics 3 trạng thái |
| Quality và freshness monitoring | `quality.py` | Baseline/corrupted/repaired quality reports | `data/quality/` |
| Dashboard | `app.py`, `src/ui/artifacts.py` | Hiển thị pipeline, quality, freshness và metrics | `streamlit run app.py` |

Output chính: Corrupted Hit Rate `0.9`, Repaired Hit Rate `1.0`; Corrupted Token F1
`0.4`, Repaired Token F1 `0.5`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần mô phỏng dữ liệu bị lỗi, đo mức suy giảm của RAG và khôi phục dữ liệu
đáng tin cậy mà không sửa trực tiếp bản corrupted.

### Cách triển khai

Corruption được thực hiện deterministic trên clean dataframe với sáu scenario:
drop latest records, blank summary, inject noise, truncate title, stale date và
duplicate rows. Repair đọc lại raw records, chạy cleaning, rebuild embedding/index
và evaluation trên cùng test set.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | `data/clean/papers_clean.csv`, raw records, `test_set.json`, Settings |
| Output | Corrupted/repaired clean data, embeddings, metrics, quality reports |
| Module phụ thuộc | `core.config`, `ingestion`, `retrieval`, `evaluation`, `observability` |
| Module sử dụng output | Dashboard và comparison report |
| Điều kiện lỗi cần xử lý | Text rỗng từ CSV có thể được đọc thành `NaN` |

### Cách xác minh

```powershell
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Corrupted metrics giảm và repaired metrics phục hồi.
- **Kết quả thực tế:** Hit Rate `1.0 → 0.9 → 1.0`, Token F1 `0.5 → 0.4 → 0.5`.
- **Artifact/log:** `data/results/`, `data/quality/`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Repair có thể sửa trực tiếp corrupted data hoặc dựng lại từ raw.
- **Các phương án đã cân nhắc:** Sửa tại chỗ; hoặc rebuild từ raw snapshot.
- **Phương án đã chọn:** Rebuild từ `data/raw/crossref_records.json`.
- **Lý do:** Bảo đảm data lineage, reproducibility và idempotence.
- **Bằng chứng:** Repaired dataset có 24 rows, Quality Gate PASS và metrics trở lại baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Text rỗng từ CSV trở thành `NaN` float khi rebuild context.
- **Lệnh hoặc bước tái hiện:** Chạy corruption flow sau khi đọc `papers_clean.csv`.
- **Nguyên nhân gốc:** CSV parser biểu diễn ô text rỗng thành `NaN`.
- **Cách xử lý:** Chuẩn hóa `NaN` thành chuỗi rỗng trước khi tạo `text_for_embedding`.
- **Cách xác minh sau khi sửa:** Corruption flow exit code 0 và tạo đủ artifacts.
- **Điều học được:** Cần xử lý khác biệt kiểu dữ liệu giữa JSON và CSV.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu từ Crossref được lưu raw, clean và chuyển thành embeddings trong ChromaDB.
2. Evaluation set dùng DOI trong `ground_truth_doc_ids` để đo retrieval và answer quality.
3. Quality checks kiểm tra schema/content; freshness kiểm tra `age_days` và SLA riêng.
4. Cùng test set giúp so sánh công bằng giữa baseline, corrupted và repaired.
5. Repair thành công khi dữ liệu về 24 rows, Quality Gate PASS, Hit Rate và Token F1 trở lại baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0 | 0.9 | 1.0 | Phục hồi hoàn toàn |
| `mean_token_f1` | 0.5 | 0.4 | 0.5 | Phục hồi hoàn toàn |
| `judge_accuracy` | 0.5 | 0.4 | 0.5 | Trở lại baseline |
| `mean_judge_score` | 3.0 | 2.7 | 3.0 | Trở lại baseline |
| Quality checks | PASS | FAIL | PASS | Corruption bị quality gate phát hiện |
| Freshness status | FRESH | FRESH | FRESH | Stale ratio chưa vượt 25% |

### Kết luận từ số liệu

1. Corruption làm Quality Gate FAIL và làm Hit Rate giảm `0.1`, Token F1 giảm `0.1`.
2. Repair từ raw snapshot khôi phục Quality Gate, Hit Rate và Token F1 về baseline.

Corruption ảnh hưởng rõ nhất là blank summary, duplicate rows và thay đổi nội dung
context vì làm hỏng các expectation và thông tin được dùng khi retrieval/answer.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data lineage giúp repair an toàn hơn sửa trực tiếp dữ liệu lỗi.
2. Quality Gate cần kiểm tra cả schema, uniqueness, completeness và freshness.
3. Cùng một evaluation set giúp đo rõ ảnh hưởng của data corruption lên RAG.

### Nếu có thêm thời gian

Chạy thêm Ragas và bổ sung unit/integration tests cho cleaning, corruption,
quality reports và comparison report.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích flow end-to-end.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric đối chiếu.
- [x] Báo cáo không chứa `.env`, API key hoặc token.

**Họ và tên:** Tô Anh Đức
**Ngày xác nhận:** 2026-09-26
