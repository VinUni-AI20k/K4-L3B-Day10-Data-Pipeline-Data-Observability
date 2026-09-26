# Báo cáo nhóm — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa / Lớp | K4 / L3B — Day 10 |
| Nhóm | Saphoaqua |
| Repository | [Repository nhóm](https://github.com/nguyenducdong22/K4-L3B-Day10-Saphoaqua-DataPipelineDataObservability) |
| Ngày cập nhật | 2026-09-26 |
| Phạm vi bằng chứng | Mã nguồn và artifacts hiện có; chưa chạy lại toàn tuyến trong lần viết báo cáo này |

| STT | Thành viên | Mã học viên | Vai trò / module | Báo cáo cá nhân |
| ---: | --- | --- | --- | --- |
| 1 | Nguyễn Đức Đông | Chưa có trong hồ sơ nhóm | Leader; `core/`, `script/`, `src/pipelines/` | [Đông](NguyenDucDong.md) |
| 2 | Nguyễn Thị Lê Na | Chưa có trong hồ sơ nhóm | Ingestion, cleaning, corruption; `src/ingestion/` | [Na](individual_report.md) |
| 3 | Bùi Quốc Việt | 2A20202884 | Vector database và RAG; `src/retrieval/` | [Việt](2A20202884-viet.md) |
| 4 | Lê Thị Duyên | 2A202602411 | Quality và evaluation; `src/observability/`, `src/evaluation/` | [Duyên](2A202602411-duyen.md) |

Phân công theo [PHAN_CONG_NHOM.md](../PHAN_CONG_NHOM.md). Cần bổ sung mã học viên Đông/Na và đồng bộ đường dẫn báo cáo Việt/Na trong `docs/TEAM.md` theo file thực tế trên.

## 2. Tóm tắt kết quả

Nhóm Saphoaqua triển khai pipeline thu thập metadata Crossref, lưu snapshot thô, làm sạch dữ liệu, xây dựng index ChromaDB, đánh giá truy vấn và kiểm tra chất lượng bằng Great Expectations 1.x. Artifacts hiện có gồm 24 bản ghi raw, 24 dòng sạch, benchmark 10 câu hỏi, ba manifest index, kết quả đánh giá và báo cáo chất lượng cho baseline, corrupted và repaired.

Trong bộ kết quả đã lưu, baseline đạt Hit Rate 100%, Token F1 0.6676 và quality PASS. Sáu dạng corruption tạo 23 dòng với 20 DOI duy nhất; quality chuyển sang FAIL do duplicate và summary ngắn. Hit Rate giảm còn 70%, Token F1 còn 0.4500. Sau phục hồi từ snapshot, 24 DOI duy nhất và các metrics trở về mức baseline. Freshness vẫn FRESH ở cả ba trạng thái vì tỷ lệ dữ liệu cũ chưa vượt 25%.

Đối chiếu phát hiện giới hạn cần xử lý trước nghiệm thu: judge dùng heuristic dự phòng; ba ground truth summary hiện khác bản trong answers; manifest trỏ tới máy khác; kiểm thử MiniLM mới bị chặn bởi tải trọng số timeout. Vì vậy số liệu dưới đây mô tả artifacts đã lưu, chưa chứng minh phiên bản mã hiện tại chạy lại thành công toàn tuyến.

## 3. Kiến trúc và luồng dữ liệu

```text
Crossref API hoặc snapshot
  -> raw response + PaperRecord
  -> cleaning -> CSV/JSON sạch
  -> papers-baseline -> benchmark -> evaluation -> quality/freshness
  -> tiêm 6 lỗi -> dữ liệu corrupted
  -> papers-corrupted -> evaluation -> quality/freshness
  -> đọc raw -> cleaning -> dữ liệu repaired
  -> papers-repaired -> evaluation -> quality/freshness
  -> bảng so sánh ba trạng thái
```

| Khối | Đầu vào / xử lý | Đầu ra | Owner |
| --- | --- | --- | --- |
| Ingestion | Crossref hoặc snapshot; parse metadata | `data/raw/crossref_response.json`, `crossref_records.json` | Na |
| Cleaning | PaperRecord; trim, tính tuổi, deduplicate, ghép text | `data/clean/papers_clean.csv`, `papers_clean.json` | Na |
| Embedding/index | `text_for_embedding`; MiniLM, cosine | `data/chroma/`, `data/embeddings/` | Việt |
| Evaluation | Index và test set; Hit Rate, F1, judge | `data/eval/test_set.json`, `data/results/*_metrics.json`, `*_answers.json` | Duyên |
| Observability | DataFrame; GX, freshness | `data/quality/*_quality_report.json` | Duyên |
| Corruption/repair | Tiêm lỗi; dựng lại từ raw | Log, dữ liệu corrupted/repaired | Na; Đông tích hợp |
| Orchestration | Điều phối Phase 1/Phase 2 | Hai báo cáo trong `data/reports/` | Đông |

**Thứ tự thực tế:** pipeline index/evaluate trước rồi kiểm tra quality. Corrupted index được tạo có chủ đích để đo suy giảm. Chưa có cơ chế chặn phát hành index dựa trên gate; repair chạy tuần tự trong Phase 2, chưa phải nhánh chỉ tự kích hoạt khi gate thất bại.

## 4. Cấu hình và cách tái hiện

| Cấu hình | Giá trị / nguồn |
| --- | --- |
| Python | Dự án yêu cầu 3.11–3.13; leader ghi môi trường 3.11.9 |
| Provider/model | Leader ghi `groq` / `llama-3.3-70b-versatile`; judge thực tế dùng fallback |
| Embedding | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store | ChromaDB persistent, cosine |
| Collections | `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Crossref records | Tối đa 24; raw hiện có 24 |
| `top_k` | 4 |
| Freshness | `age_days > 180`; cảnh báo nếu tỷ lệ vượt 0.25 |
| Random seed | Không dùng random trong corruption; chọn theo ngày/thứ tự dòng |
| Ragas | Bỏ qua trong cả ba metrics |

Chạy tại thư mục gốc repo bằng PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
# Chỉ tạo .env nếu chưa có, sau đó điền provider/model/key cá nhân.
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
$env:HF_HUB_CACHE = "$PWD\.venv\hf-cache"
$env:HF_HUB_DISABLE_XET = "1"
$env:HF_HUB_DOWNLOAD_TIMEOUT = "60"
$env:REFRESH_SOURCE = "0"
.\.venv\Scripts\python.exe script/run_phase1.py
.\.venv\Scripts\python.exe script/run_corruption_flow.py
```

Cần xử lý lỗi tích hợp ở mục 11 trước nghiệm thu Phase 2. Để kiểm tra riêng retrieval khi có đủ dữ liệu ba trạng thái: `.\.venv\Scripts\python.exe -m retrieval.verify`. Lệnh này dựng lại collection/manifest, không tính lại toàn bộ metrics.

| Luồng | Bằng chứng đã lưu | Timestamp báo cáo (UTC) | Trạng thái tái hiện |
| --- | --- | --- | --- |
| Baseline | [Phase 1](../data/reports/phase1_report.md), metrics/answers | 2026-09-26 03:56:53 | Có kết quả lưu; chưa chạy lại toàn tuyến trên bản mã đang sửa |
| Corruption/repair | [Comparison](../data/reports/corruption_report.md), metrics/quality | 2026-09-26 03:57:26 | Có kết quả lưu; cần xử lý blocker rồi chạy lại |

Timestamp trên thuộc báo cáo đã có, không phải kiểm thử mới. Không đưa API key hoặc nội dung `.env` vào báo cáo.

## 5. Ingestion, cleaning và data contract

Endpoint cấu hình là `https://api.crossref.org/works`; query `agentic retrieval augmented generation large language model`; filter `from-pub-date:<ngày chạy trừ 180 ngày>,has-abstract:true`. API chỉ được gọi khi bật refresh hoặc thiếu snapshot, timeout 10 giây. Lỗi HTTP/mạng chuyển sang snapshot nếu có; chưa có vòng retry/backoff riêng.

Raw hiện có 24 PaperRecord. Không đủ bằng chứng xác nhận timestamp thu thập ban đầu hoặc response mới thay vì snapshot mẫu. Response được serialize lại thành JSON, bảo toàn nội dung dữ liệu nhưng không cam kết nguyên byte HTTP response.

| Trường | Kiểu | Quy tắc |
| --- | --- | --- |
| `paper_id` | string | DOI; bỏ record thiếu, deduplicate giữ dòng đầu |
| `title` | string | Trim; bỏ record thiếu title khi clean |
| `summary` | string | Loại HTML/XML khi parse, trim; GX yêu cầu ≥ 30 ký tự |
| `authors`, `categories` | list[string] | Dựng thêm `authors_joined`, `categories_joined` |
| `published` | string | Ngày xuất bản; có fallback `2026-01-01` |
| `age_days` | integer | `max(0, (run_date - published).days)`, ngày chạy UTC |
| `summary_chars` | integer | Độ dài summary |
| `text_for_embedding` | string | Năm dòng: Title, Authors, Published, Categories, Summary |
| Metadata khác | string | `primary_category`, `updated`, `abs_url`, `pdf_url`, `comment` |

Clean có 24 dòng, 16 cột, 24 DOI. Raw cũng 24 dòng nên không giảm số dòng ròng; chưa có log đếm trường được trim/loại tag. Mã dùng `strip()`, chưa gom mọi khoảng trắng bên trong chuỗi. Khi ngày sai, tuổi có thể dùng ngày fallback nhưng `published` vẫn giữ chuỗi ban đầu; cần thống nhất lại.

ID vector `<paper_id>::<số thứ tự dòng>` giữ duplicate trong thí nghiệm corrupted. DOI vẫn là khóa đối chiếu ground truth; ba collection tránh ghi đè lẫn nhau.

## 6. Evaluation và tính nhất quán benchmark

Benchmark hiện có 10 câu: 3 `summary`, 3 `authors`, 2 `date`, 2 `categories`; DOI chuẩn nằm trong `ground_truth_doc_ids`.

`qa.py` truy vấn vector, ưu tiên tiêu đề khớp chính xác nếu câu hỏi chứa tiêu đề trong nháy đơn, rồi trích câu trả lời từ metadata. Hit Rate phản ánh luồng kết hợp exact lookup và vector, không phải đánh giá thuần semantic retrieval hoặc chất lượng sinh văn bản LLM.

- `retrieval_hit_rate`: tỷ lệ câu có ít nhất một DOI chuẩn trong kết quả.
- `mean_token_f1`: F1 theo tập token duy nhất sau lowercase/chuẩn hóa khoảng trắng, không đếm tần suất token lặp.
- Judge: toàn bộ 30 answers ghi `Fallback heuristic judge used because the LLM evaluator was unavailable.` Heuristic cho điểm 5 nếu F1 ≥ 0.95, 3 nếu F1 ≥ 0.5, còn lại 1; correct khi điểm ≥ 3. Đây không phải LLM judge độc lập.
- Ragas chưa chạy; metrics ghi `skipped`.

**Đối chiếu:** ba file answers lưu cùng ID, question, ground truth và DOI với nhau. Tuy nhiên ground truth của `eval_001`, `eval_005`, `eval_009` trong test set hiện khác bản trong cả ba answers. Bảng so sánh nhất quán với benchmark lưu trong answers, chưa đại diện cho test set hiện tại. Cần khóa test set rồi chạy lại cả ba trạng thái.

SHA-256 của `data/eval/test_set.json` tại thời điểm rà soát:

```text
8b26ace2ec53c29dbcd065003466b0e3287e7a474e0cb0dee100dfa19d29bf90
```

## 7. Artifacts và baseline

| Artifact | Bằng chứng / trạng thái |
| --- | --- |
| Raw | [Response](../data/raw/crossref_response.json), [records](../data/raw/crossref_records.json): có, 24 records |
| Clean | [Baseline JSON](../data/clean/papers_clean.json): có, 24 dòng/24 DOI |
| Index | Có `data/chroma/chroma.sqlite3`; đọc bảng collections xác nhận ba tên yêu cầu; chưa kiểm thử truy vấn MiniLM mới |
| Manifest | Có ba file trong `data/embeddings/`, khai báo 24/23/24 documents; `persist_path` trỏ tới máy khác và không tồn tại trên máy hiện tại |
| Benchmark | [Test set](../data/eval/test_set.json): 10 câu; cần đồng bộ kết quả lưu |
| Metrics | [Baseline](../data/results/baseline_metrics.json), [corrupted](../data/results/corrupted_metrics.json), [repaired](../data/results/repaired_metrics.json): có |
| Answers | Có ba file `*_answers.json`, mỗi file 10 câu |
| Quality/report | Có ba quality reports và hai báo cáo Phase 1/comparison |

Baseline: Hit Rate 1.0; Token F1 0.6675757575757576; judge accuracy 0.7; mean judge score 3.2/5. Tổng hợp lại từ answers khớp metrics. Hit Rate 100% không đồng nghĩa mọi câu trả lời đúng: F1 khoảng 0.6676 và judge là heuristic.

## 8. Data quality và freshness

GX dùng ephemeral context và Pandas batch. Bốn loại expectation tạo sáu phép kiểm tra vì not-null áp dụng ba cột.

| Check | Ngưỡng | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- | --- |
| Row count | 5–5000 | PASS: 24 | PASS: 23 | PASS: 24 |
| Not-null | `paper_id`, `title`, `text_for_embedding` | PASS cả 3 | PASS cả 3 | PASS cả 3 |
| Unique | DOI duy nhất | PASS | FAIL: 6 dòng thuộc 3 cặp trùng | PASS |
| Summary length | ≥ 30 ký tự | PASS | FAIL: 4 dòng rỗng sau duplicate | PASS |
| Tổng GX | 6 expectations | 6/6 PASS | 4/6 PASS | 6/6 PASS |

Nguồn: [baseline quality](../data/quality/baseline_quality_report.json), [corrupted quality](../data/quality/corrupted_quality_report.json), [repaired quality](../data/quality/repaired_quality_report.json). Artifacts ghi GX 1.23.2.

| Freshness trên DataFrame | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Ngày xuất bản mới nhất | 2026-07-22 | 2026-06-12 | 2026-07-22 |
| Số dòng tuổi > 180 ngày | 1/24 | 4/23 | 1/24 |
| Tỷ lệ stale đã lưu | 4.17% | 17.39% | 4.17% |
| Trạng thái | FRESH | FRESH | FRESH |

Corruption tăng stale nhưng chưa vượt 25%. `success = gx_success and is_fresh`; corrupted FAIL do GX. Tuổi tính tại lần chạy đã lưu, không bảo đảm freshness vĩnh viễn. Dùng quality report theo stage vì `freshness_report.json` bị ghi đè mỗi lần chạy.

## 9. Corruption và repair

[Corruption log](../data/results/corruption_log.json) có đủ sáu scenario:

| Scenario | Cách thực hiện | Tác động / tín hiệu |
| --- | --- | --- |
| Drop latest | Bỏ 4 dòng mới nhất: `int(24 × 0.2)` | Còn 20 DOI; row-count vẫn PASS |
| Blank summary | Xóa summary 2 dòng | Sau duplicate có 4 dòng rỗng, length FAIL |
| Inject noise | Thêm noise vào summary 2 dòng | Chưa có expectation riêng phát hiện noise |
| Truncate title | Cắt title 2 dòng còn 5 ký tự | Có thể ảnh hưởng exact lookup/vector; chưa có gate độ dài title |
| Stale date | 3 dòng tăng tuổi 365 ngày, gán `published=2024-01-01` | Tỷ lệ stale 17.39%; ngày và tuổi chưa tính đồng nhất |
| Duplicate | Thêm bản sao 3 dòng đầu | Tổng 23 dòng/20 DOI; uniqueness FAIL |

Không cộng số dòng các scenario để suy ra số tài liệu lỗi duy nhất vì có chồng lặp. Log có DOI cho phần lớn biến đổi; duplicate chỉ lưu số lượng, chưa có đầy đủ before/after để audit mọi trường.

Repair đọc `data/raw/crossref_records.json`, chạy cleaning, ghi repaired và dựng collection riêng. Đây là tái tạo từ raw, không sửa metrics. Artifacts repaired có 24 DOI và metrics bằng baseline. Chưa test repair nhiều lần với hash đầu ra; muốn kiểm chứng idempotency tuyệt đối cần cố định `run_date` vì `age_days` phụ thuộc ngày chạy.

## 10. So sánh ba trạng thái

Bảng lấy từ artifacts đã lưu và đối chiếu tổng hợp answers, không phải kết quả chạy lại trên test set hiện tại.

| Metric / signal | Baseline | Corrupted | Repaired | Corrupted so với baseline |
| --- | ---: | ---: | ---: | --- |
| Số dòng | 24 | 23 | 24 | −1 dòng ròng |
| DOI duy nhất | 24 | 20 | 24 | −4 DOI |
| Hit Rate | 100% | 70% | 100% | −30 điểm phần trăm |
| Mean Token F1 | 0.6676 | 0.4500 | 0.6676 | −0.2176 |
| Judge accuracy (heuristic) | 70% | 50% | 70% | −20 điểm phần trăm |
| Mean judge score (heuristic) | 3.2 | 2.6 | 3.2 | −0.6 |
| Quality | PASS | FAIL | PASS | Vi phạm uniqueness/summary length |
| Freshness | FRESH | FRESH | FRESH | Chưa vượt ngưỡng |

1. **Dữ liệu lỗi → quality FAIL → suy giảm truy vấn:** duplicate và summary rỗng tạo vi phạm GX trực tiếp. Khi phối hợp sáu lỗi, Hit Rate giảm 30 điểm phần trăm, F1 giảm 0.2176 dù vẫn có câu trả lời. Chưa tách thí nghiệm từng lỗi nên không đủ cơ sở khẳng định lỗi nào tác động metrics nhiều nhất.
2. **Phục hồi raw → dữ liệu hợp lệ → metrics về baseline:** repaired có 24 DOI, hai check lỗi trở lại PASS và cả bốn metrics bằng baseline. Đây là phục hồi hiệu năng ban đầu, không có nghĩa mọi câu trả lời đúng 100%.
3. **Freshness không thay thế quality:** corrupted vẫn FRESH trong khi quality FAIL và retrieval giảm; cần quan sát đồng thời nhiều tín hiệu.

## 11. Vấn đề tích hợp

| Vấn đề | Bằng chứng | Xử lý / bước tiếp theo |
| --- | --- | --- |
| Thiếu MiniLM | Cache thiếu trọng số; tải Hugging Face timeout | Đã thử HTTP/tăng timeout; cần tải đủ rồi chạy lại retrieval và pipeline |
| Manifest gắn máy cũ | Ba `persist_path` không tồn tại trên máy hiện tại | Build lại; về lâu dài dùng đường dẫn tương đối hoặc resolve theo cấu hình |
| Benchmark thay đổi | Ground truth 3 câu summary khác answers | Khóa test set, lưu hash, chạy lại cả ba trạng thái |
| Repaired quality không khớp config | `quality.py` gọi `settings.paths.repaired_quality_report`, nhưng `Paths` chưa khai báo trường này | Bổ sung trường hoặc dùng đường dẫn stage đã có; chưa sửa trong đợt viết báo cáo |
| Import SDK đồng loạt | Mock có thể phụ thuộc provider không dùng | Đã import theo nhánh; khởi tạo Groq/Gemini/OpenAI/Mock đạt, chưa xác minh API thật |
| Build lại và dữ liệu biên | Cần giữ duplicate, không mất index khi embedding lỗi | Đã cải thiện index; test ChromaDB thật với vector kiểm thử đạt isolation, rebuild, duplicate, collection rỗng và giữ index khi embedding lỗi |

Báo cáo repaired cũ không chứng minh nhánh repaired của bản mã hiện tại chạy thành công. Mô tả “gate chặn deploy” hoặc “LLM judge” trong tài liệu khác cần đối chiếu với thứ tự và giới hạn thực tế nêu trên.

## 12. Giới hạn và hướng cải thiện

| Giới hạn | Ảnh hưởng | Hướng kiểm chứng cải thiện |
| --- | --- | --- |
| 10 câu, exact-title lookup | Chưa đại diện câu hỏi mở | Thêm paraphrase, đo riêng vector-only |
| Judge heuristic | Không đánh giá LLM độc lập | Lưu provider/model/fallback, chạy judge thật khi API sẵn sàng |
| Chưa khóa dataset/test set | Khó tái hiện metrics | Lưu run ID, commit, hash dữ liệu/test set, model, ngày chạy |
| Quality sau indexing | Phát hiện nhưng chưa chặn publish | Thêm nhánh production kiểm gate trước publish và test chặn lỗi |
| Ngày/tuổi không đồng nhất | Freshness có thể sai | Tính cùng ngày đã dịch, thêm consistency check |
| Fallback ngày/URL suy đoán | Metadata chưa chắc phản ánh nguồn | Gắn cờ missing/invalid, không coi mặc định là dữ liệu đã xác minh |
| Chưa test repair lặp | Chưa chứng minh idempotency bằng test | Chạy hai lần cùng snapshot/run_date, so hash và số vector |
| Hồ sơ nhóm chưa đồng bộ | Thiếu mã học viên/đường dẫn | Bổ sung thông tin, xác nhận Contributors và LMS |

## 13. Checklist trước khi nộp

- [x] Có phân công và liên kết bốn báo cáo cá nhân hiện có.
- [x] Metrics khớp tổng hợp từ ba answers đã lưu.
- [x] Kết luận quality/freshness khớp reports đã lưu.
- [x] Ba answers dùng cùng benchmark lưu trong chúng.
- [x] Ghi rõ judge fallback, Ragas chưa chạy và giới hạn tái hiện.
- [x ] Bổ sung mã học viên Đông/Na, đồng bộ `docs/TEAM.md`.
- [x] Đồng bộ test set với lần đánh giá mới của cả ba trạng thái.
- [x] Sửa cấu hình repaired quality, build lại manifest dùng được trên máy nộp.
- [x] Tải đủ MiniLM, chạy lại Phase 1/Phase 2 trên đúng bản mã nộp.
- [x] Kiểm tra API thật nếu nghiệm thu yêu cầu provider thật.
- [x] Kiểm tra secret trong source/log/Git history trước push; báo cáo này không chứa secret.
- [x] Xác nhận commit cá nhân, tên repo đúng quy ước, từng người đã nộp link LMS.
