# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Đức Triệu |
| MSSV               | 2A202602978 |
| Khóa/Lớp         | K4 - L3B |
| Tên nhóm         | 5changlinhngulam |
| Vai trò chính    | Evaluation & observability owner |
| Repository         | https://github.com/ductrieunguyen897-code/K4-L3B-Day10-5changlinhngulam-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Evaluation set | `src/evaluation/testset.py` (`build_test_set`) | Cleaned DataFrame | `data/eval/test_set.json` (10 câu, 4 loại) | Hoàn thành |
| Quality gate | `src/observability/quality.py` (`run_data_quality_checks`, `evaluate_freshness_sla`, `build_freshness_report`) | Cleaned/corrupted/repaired DataFrame | `data/quality/*_quality_report.json`, `*_freshness_report.json` | Hoàn thành |
| Reporting | `src/observability/reporting.py` (`generate_phase1_report`, `generate_corruption_report`) | Metrics + quality + freshness dict | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Xác minh metrics trước khi tổng hợp comparison report | Thành viên 3 — `corruption_flow.py` | Đối chiếu `corrupted_metrics.json`/`repaired_metrics.json` với số liệu in ra console, xác nhận khớp trước khi ghi report |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Implement `build_test_set` | `src/evaluation/testset.py` | 10 câu hỏi, đều 4 loại (summary/authors/date/categories, xoay vòng theo `index % 4`) | Lệnh kiểm tra bước 5 → in `Sinh được 10 câu hỏi test` |
| Implement `run_data_quality_checks` (Great Expectations 1.x Ephemeral Context) | `src/observability/quality.py` | 6 Expectations (row count, 3× not-null, uniqueness, length), trả `{"success": bool, ...}` | Lệnh kiểm tra bước 4 → in `Quality check status = True` |
| Implement `evaluate_freshness_sla` + `build_freshness_report` | `src/observability/quality.py` | Freshness JSON với `stale_rows/total_rows/stale_ratio/is_fresh` | `data/quality/freshness_report.json` |
| Implement `generate_phase1_report`/`generate_corruption_report` | `src/observability/reporting.py` | 2 markdown report tự động sinh từ dict metrics/quality/freshness | `data/reports/phase1_report.md`, `corruption_report.md` |

Output cụ thể: `data/quality/baseline_quality_report.json` ghi lại đầy đủ 6 `expectation_config` với kết quả `success` của từng cái, giúp Thành viên 3 debug ngay khi corruption flow báo fail (biết chính xác Expectation nào fail, không chỉ biết "fail chung chung").

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Cần một cơ chế tự động hóa việc đánh giá "dữ liệu có đủ tốt để đưa vào RAG hay không" — cả về cấu trúc (Great Expectations) lẫn về thời gian (freshness) — và biến kết quả đánh giá đó thành báo cáo có thể đọc được ngay, không cần tự tra JSON.

### Cách triển khai

`run_data_quality_checks` dùng chuẩn GX 1.x Ephemeral Context: `gx.get_context(mode="ephemeral")` → `add_pandas` → `add_dataframe_asset` → `add_batch_definition_whole_dataframe` → `get_batch`. Với mỗi Expectation, gọi `batch.validate(expectation)` riêng lẻ (thay vì gộp vào một Expectation Suite) để lấy được `to_json_dict()` chi tiết cho từng check, phục vụ log/debug. `overall_success` là AND của tất cả Expectations **và** kết quả `evaluate_freshness_sla` — nghĩa là dữ liệu chỉ "pass" nếu vừa đúng cấu trúc vừa còn tươi mới.

`evaluate_freshness_sla` tính `stale_ratio = stale_rows / total_rows` với `stale_rows` là số dòng có `age_days > freshness_threshold_days` (180), và gắn cờ `is_fresh = stale_ratio <= 0.25`. Tách hàm này riêng để cả `run_data_quality_checks` (gate pass/fail) và `build_freshness_report` (báo cáo độc lập, dùng bởi cả baseline lẫn corrupted/repaired) đều dùng chung một logic tính toán, tránh lệch số liệu giữa hai nơi.

`generate_corruption_report` nhận đủ 3 bộ metrics + 2 cặp quality/freshness (corrupted, repaired) để dựng bảng so sánh 3 cột (Baseline/Corrupted/Repaired) — bảng này chính là bằng chứng trực tiếp cho phần "So sánh 3 trạng thái" mà bài lab yêu cầu.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `pd.DataFrame` đã clean/corrupted/repaired; `Settings` (ngưỡng freshness, đường dẫn output) |
| Output                         | `dict` `{"success": bool, "row_count": int, "expectations": [...], "freshness": {...}}`; JSON ghi vào `data/quality/` |
| Module phụ thuộc             | `great_expectations` 1.23.2, `core.utils.write_json` |
| Module sử dụng output        | `pipelines/phase1.py`, `pipelines/corruption_flow.py` (đọc `quality_report`/`freshness_report` để đưa vào `generate_*_report`) |
| Điều kiện lỗi cần xử lý | DataFrame rỗng (0 dòng) → `evaluate_freshness_sla` trả `is_fresh=False` thay vì chia cho 0 |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print('Tín hiệu hoàn thành: Quality check status =', res['success'])"
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
```

- **Kết quả mong đợi:** `Quality check status = True` và `Sinh được 10 câu hỏi test`.
- **Kết quả thực tế:** Khớp đúng như mong đợi.
- **Artifact/log:** `data/quality/baseline_quality_report.json`, `data/eval/test_set.json` (không chứa secret).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định freshness threshold nên là ngưỡng cứng trên từng dòng (age_days > X → fail ngay) hay ngưỡng tỉ lệ (% dòng cũ vượt quá Y% → cảnh báo).
- **Các phương án đã cân nhắc:** (1) Fail toàn bộ batch nếu có bất kỳ dòng nào `age_days > 180`; (2) Chỉ cảnh báo nếu tỉ lệ dòng cũ vượt 25% tổng số dòng.
- **Phương án đã chọn:** Phương án (2) — ngưỡng tỉ lệ 25%.
- **Lý do:** Yêu cầu bài lab nêu rõ "Nếu tỉ lệ bài báo cũ vượt quá 25%, hệ thống lập tức gắn cờ cảnh báo". Ngưỡng cứng theo từng dòng sẽ khiến pipeline fail liên tục chỉ vì một vài bài báo hợp lệ nhưng xuất bản hơi lâu, trong khi dữ liệu tổng thể vẫn có giá trị sử dụng cho RAG — ngưỡng tỉ lệ phản ánh đúng "sức khỏe tổng thể" của corpus hơn.
- **Bằng chứng quyết định phù hợp:** Baseline có 1/24 (4.17%) bài cũ nhưng vẫn `is_fresh=True` — đúng như kỳ vọng (1 bài cũ không nên làm cả corpus "stale"). Sau khi corruption đẩy stale_ratio lên 34.78%, hệ thống mới chuyển sang `is_fresh=False`, đúng ngưỡng 25% đề bài yêu cầu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Lần chạy thử đầu tiên, `ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30)` fail trên dữ liệu baseline hợp lệ, dù summary rõ ràng dài hơn 30 ký tự.
- **Lệnh hoặc bước tái hiện:** Gọi `run_data_quality_checks(df, settings, "test")` ngay sau khi build DataFrame từ `cleaning.py` phiên bản chưa xử lý `summary_chars`/whitespace kỹ.
- **Nguyên nhân gốc:** DataFrame truyền vào có cột `summary` chứa khoảng trắng thừa ở object dtype không nhất quán (một số giá trị bị đọc lại từ JSON dưới dạng khác dtype), khiến Expectation đo độ dài trên giá trị chưa qua `normalize_whitespace`.
- **Cách xử lý:** Đảm bảo `cleaning.py` luôn `normalize_whitespace(summary)` trước khi đưa vào DataFrame, để `summary` trong `papers_clean.csv`/`.json` luôn nhất quán trước khi Quality Gate đọc lại.
- **Cách xác minh sau khi sửa:** Chạy lại `run_data_quality_checks` trên `s.paths.clean_json` → `success=True`, tất cả 6 Expectations pass (xem `baseline_quality_report.json`).
- **Điều học được:** Quality Gate chỉ tốt bằng dữ liệu nó nhận — cần đảm bảo hợp đồng dữ liệu (data contract) giữa bước cleaning và bước quality check được giữ nhất quán, không giả định ngầm rằng dữ liệu "chắc chắn sạch" chỉ vì đã qua bước cleaning.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. Dữ liệu từ Crossref qua `crossref.py`/`cleaning.py` thành DataFrame sạch, sau đó `retrieval/index.py` encode bằng MiniLM và nạp vào ChromaDB — tôi không sở hữu bước này nhưng cần hiểu để biết `text_for_embedding` là input trực tiếp cho embedding.
2. Evaluation set tôi sinh ra gắn `ground_truth_doc_ids` chính là `paper_id` của tài liệu nguồn — khi đánh giá, hệ thống kiểm tra retrieval có trả về đúng `paper_id` đó trong top-k không (`retrieval_hit_rate`), và so sánh nội dung câu trả lời với `ground_truth` (token F1 + LLM-judge).
3. Quality checks (GX Expectations) là kiểm tra "tại thời điểm hiện tại, dữ liệu có đúng cấu trúc/không rỗng/không trùng không" — độc lập với thời gian. Freshness monitoring là kiểm tra "dữ liệu này có đang già đi so với ngưỡng SLA không" — phụ thuộc trực tiếp vào `age_days`, tức phụ thuộc thời điểm chạy pipeline (`run_date`). Hai khái niệm này bổ sung nhau: dữ liệu có thể đúng cấu trúc nhưng đã cũ (stale), hoặc mới nhưng sai cấu trúc (invalid).
4. Test set phải giữ nguyên vì nếu đổi ground-truth giữa 3 lần đánh giá, không thể phân biệt được chênh lệch metric là do corruption/repair hay do đổi câu hỏi — phá vỡ tính so sánh được (comparability).
5. Repair thành công dựa trên: `repaired_quality_report.json.success=True`, `repaired_freshness_report.json.is_fresh=True` với `stale_ratio` quay về đúng baseline (4.17%), và `repaired_metrics.json` có 4 chỉ số agent bằng đúng `baseline_metrics.json`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.6000 |   1.0000 | Quality gate fail (duplicate) xảy ra đồng thời với hit rate giảm — hai signal cùng hướng |
| `mean_token_f1`      |   0.7000 |    0.3788 |   0.7000 | Giảm gần 46% tương đối |
| `judge_accuracy`     |   0.7000 |    0.3000 |   0.7000 | Giảm mạnh nhất trong 4 metric (57% tương đối) |
| `mean_judge_score`   |   3.8000 |    2.7000 |   3.8000 | Giảm 1.1/5 điểm |
| Quality checks         |     Pass |      Fail |     Pass | Fail vì `ExpectColumnValuesToBeUnique(paper_id)` |
| Freshness status       |    Fresh |     Stale |    Fresh | stale_ratio 4.17%→34.78%→4.17% |

### Kết luận từ số liệu

1. Data corruption (stale-date injection làm 4/20 dòng bị cộng thêm 365 ngày `age_days`) → `stale_ratio` tăng từ 4.17% lên 34.78%, vượt ngưỡng SLA 25% → `is_fresh` chuyển False → đồng thời `judge_accuracy` giảm mạnh nhất (0.7→0.3) vì các câu hỏi loại `date` nhận câu trả lời sai lệch 365 ngày.
2. Repair action (rebuild `age_days` từ `run_date` hiện tại và raw `published` gốc, không cộng dồn phần bị corrupt) → `stale_ratio` phục hồi đúng 4.17% → `judge_accuracy` phục hồi đúng 0.7, chứng tỏ freshness signal và agent metric liên hệ nhân quả rõ ràng qua trục thời gian.

Corruption nào ảnh hưởng rõ nhất và vì sao: Từ góc độ observability, **duplicate rows** là corruption bộc lộ rõ nhất qua Quality Gate (fail ngay lập tức, dễ phát hiện tự động), trong khi **stale date** là corruption bộc lộ rõ nhất qua Freshness Monitoring (đẩy vượt ngưỡng 25%) và có liên hệ trực tiếp nhất với sự sụt giảm `judge_accuracy` — cho thấy hai lớp observability (quality vs freshness) bắt được hai *loại* lỗi khác nhau, không thể thay thế cho nhau.

Kết quả khác kỳ vọng: tôi kỳ vọng `blanked_summary`/`noise_injected` sẽ là nguyên nhân chính khiến `mean_token_f1` giảm (vì trực tiếp phá nội dung câu trả lời `summary`), nhưng khi đối chiếu `corrupted_answers.json`, phần giảm token F1 lớn nhất lại đến từ các câu hỏi `date`/`authors` bị ảnh hưởng gián tiếp bởi việc tài liệu ground-truth bị drop khỏi index (retrieval miss hoàn toàn → F1 = 0), lớn hơn phần giảm do nội dung summary bị nhiễu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data quality gate và freshness monitoring nên được thiết kế là hai lớp kiểm tra độc lập, cùng đóng góp vào một cờ `success` tổng, để không bỏ sót loại lỗi nào.
2. Ghi chi tiết từng Expectation (không chỉ tổng `success`) là bắt buộc để debug nhanh khi tích hợp — nếu chỉ trả `True/False`, đội tích hợp sẽ mất nhiều thời gian đoán nguyên nhân fail.
3. Corruption ảnh hưởng đến RAG agent qua nhiều đường khác nhau (retrieval miss, nội dung nhiễu, thời gian sai) — một report so sánh 3 trạng thái chỉ thực sự hữu ích khi đi kèm với corruption log chi tiết theo từng `paper_id`.

### Nếu có thêm thời gian

Tôi sẽ thêm Expectation kiểm tra định dạng ngày (`published` phải match regex `YYYY-MM-DD`) để bắt lỗi format sớm hơn, thay vì chỉ dựa vào `age_days` sau khi đã parse. Đo cải thiện bằng cách tiêm một corruption "invalid date format" mới và xác nhận Quality Gate fail đúng tại Expectation đó thay vì lỗi runtime khi tính `age_days`.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đức Triệu
**Ngày xác nhận:** 2026-09-26
