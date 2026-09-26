# Báo cáo thành viên 2 — Evaluation & Failure Injection Engineer

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Minh Ngọc |
| MSSV | 2A202602530 |
| Khóa / lớp | K4-L3B |
| Nhóm | TeamVN |
| Ngày thực hiện | 2026-09-26 |
| Repository | https://github.com/haikunn11/K4-L3B-Day10-TeamVN-DataPipelineDataObservability |
| Vai trò | Evaluation & Failure Injection Engineer, theo ảnh phân công nhóm |

## 2. Vai trò và phạm vi công việc

| Deliverable | File | Trạng thái |
| --- | --- | --- |
| Benchmark 10 câu, đủ 4 nhóm | `src/evaluation/testset.py` | Đã triển khai, kiểm thử và sinh JSON |
| Sáu kịch bản làm bẩn dữ liệu | `src/ingestion/corruption.py` | Đã triển khai, kiểm thử và sinh log |
| Log kiểm định | `data/results/corruption_log.json`, `member2_validation.json` | Đã sinh từ lần chạy thực tế |
| Kiểm thử và lệnh bàn giao | `tests/test_member2.py`, `script/verify_member2.py` | 15 kiểm thử đạt |
| Hỗ trợ import độc lập | `src/evaluation/__init__.py` | Nạp metrics khi cần, giữ API công khai |

Phạm vi chính tương ứng CP2 và CP4. Cleaning, Quality Gate GX, embedding/index, orchestration và repair là các phần tích hợp của nhóm. Báo cáo này không xác nhận các phần đó đã hoàn thành.

## 3. Kết quả bàn giao và bằng chứng

| Artifact | Kết quả |
| --- | --- |
| [test_set.json](../data/eval/test_set.json) | 10 câu trên 10 bài khác nhau: summary 3, authors 3, date 2, categories 2 |
| [corruption_log.json](../data/results/corruption_log.json) | 6 sự kiện, tham số, số dòng, paper IDs và giá trị trước/sau |
| [member2_validation.json](../data/results/member2_validation.json) | Kiểm định schema/luồng cục bộ, tín hiệu dữ liệu và SHA-256 nguồn/benchmark |
| [member2_snapshot_fixture.json](../data/eval/member2_snapshot_fixture.json) | 24 bản ghi snapshot được bổ sung các cột theo clean schema để kiểm thử |
| [member2_corrupted_fixture.json](../data/eval/member2_corrupted_fixture.json) | 21 dòng sau corruption, 19 paper IDs duy nhất |

**Nguồn bằng chứng:** snapshot `data/raw/crossref_records.json`, ngày tham chiếu cố định `2026-09-26`. Chế độ `--snapshot-fixture` chỉ bổ sung helper columns từ snapshot đã có văn bản thuần. Đây không phải kết quả chạy `build_clean_dataframe`, không phải kết quả GX hay đánh giá RAG. Các fixture được lưu trong `data/eval/` để nhận diện rõ nguồn gốc.

## 4. Giải thích kỹ thuật

### Benchmark

Hàm `build_test_set(df, output_path)` kiểm tra ít nhất 10 bản ghi, các trường bắt buộc là chuỗi không rỗng, ngày ISO hợp lệ và paper IDs duy nhất. Sau đó sắp xếp theo ngày xuất bản giảm dần, dùng paper ID để phân xử khi trùng ngày, rồi chọn 10 vị trí cách đều từ mới nhất tới cũ nhất. Kết quả không phụ thuộc thứ tự dòng đầu vào.

Các loại câu hỏi được luân phiên `summary`, `authors`, `date`, `categories`. Ground truth lấy từ dữ liệu sạch: câu đầu của summary (khớp cách trả lời trong `retrieval/qa.py`), `authors_joined`, `published`, `categories_joined`. Mỗi câu chứa `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`. Với tiêu đề chứa dấu nháy đơn, câu hỏi trích dẫn paper ID để tránh lỗi parser tiêu đề của QA hiện có.

Benchmark phải được tạo từ baseline và giữ nguyên khi đánh giá corrupted/repaired. Không tạo lại ground truth từ dữ liệu đã bị làm bẩn.

### Sáu kịch bản corruption

Hàm `corrupt_clean_dataframe(df, output_log_path)` làm việc trên bản sao, với tối thiểu 10 bản ghi sạch và paper IDs duy nhất. Tỷ lệ được làm tròn lên (`ceil`), lựa chọn bản ghi theo thứ tự ngày/ID cố định, không dùng ngẫu nhiên.

| Thứ tự | Kịch bản | Quy tắc | Số bản ghi tác động trong lần chạy |
| --- | --- | --- | ---: |
| 1 | Drop latest records | Xóa 20% số dòng ban đầu mới nhất | 5 |
| 2 | Blank summary | Xóa summary của 20% số dòng còn lại | 4 |
| 3 | Inject noise | Thêm một câu rác vào đầu summary của nhóm 20% tiếp theo | 4 |
| 4 | Truncate title | Cắt tiêu đề nhóm 20% tiếp theo còn 7 ký tự | 4 |
| 5 | Stale date | Lùi published 730 ngày, tăng age_days cùng lượng, trên 40% dòng còn lại | 8 |
| 6 | Duplicate rows | Sao chép 10% dòng còn lại, giữ nguyên paper_id | 2 |

Sau khi sửa dữ liệu, tính lại `summary_chars` và `text_for_embedding` gồm Title, Authors, Published, Categories, Summary. Bước này bảo đảm lỗi đi vào nội dung được embedding, tránh tình huống metadata đã hỏng nhưng vector vẫn được tạo từ nội dung cũ. Không khử trùng lặp sau khi cố ý tạo duplicate.

Log có sáu phần trong `scenarios`; mỗi phần chứa `scenario`, `parameters`, `rows_before`, `rows_after`, `affected_count`, `affected_paper_ids`, `changes`. Mỗi change chứa `paper_id`, `before`, `after`. Drop ghi trạng thái tồn tại/ngày; duplicate ghi số lần xuất hiện; các lỗi cập nhật ghi giá trị trường bị thay đổi. Log không phải bản sao đầy đủ để khôi phục dòng đã xóa: repair vẫn cần raw snapshot.

### Contract tích hợp

| Thành phần | Contract |
| --- | --- |
| Input benchmark | `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`: chuỗi không rỗng |
| Input corruption | Các cột trên và `age_days`: số ngày nguyên, hữu hạn, không âm; title dài ít nhất 8 ký tự |
| Ngày | Chuỗi ISO 8601; hỗ trợ ngày hoặc timestamp có múi giờ |
| Output benchmark | Danh sách 10 dictionary và JSON tại đường dẫn truyền vào |
| Output corruption | DataFrame mới, giữ cột bổ sung, cập nhật helper fields; JSON log |
| Lỗi đầu vào | `ValueError` rõ trường thiếu/sai; không ghi artifact khi validation thất bại |
| Phụ thuộc | pandas và các tiện ích JSON/câu đầu trong `core.utils` |
| Bên tiêu thụ | `evaluation.metrics`, `pipelines.phase1`, `pipelines.corruption_flow`, retrieval/index và Quality Gate |

### Cách xác minh

Lệnh thực tế đã chạy tại thư mục gốc dự án trên Windows:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe script/verify_member2.py --snapshot-fixture
```

Kết quả: **15 tests, OK**; verifier in **PASS: 10 benchmark questions; 6 corruption scenarios; 24 -> 21 rows.** Các kiểm thử bao gồm ground truth, độ phủ câu hỏi, dữ liệu thiếu/sai, không sửa input, ngày có timezone, làm tròn trên nhiều kích thước corpus, cập nhật embedding fields, tính tái lập và dùng log để tái hiện cả sáu phép biến đổi.

Khi nhận dữ liệu sạch từ thành viên phụ trách cleaning, chạy:

```powershell
.venv/Scripts/python.exe script/verify_member2.py --clean-json data/clean/papers_clean.json
```

Lệnh này tạo lại benchmark/log từ clean JSON thật, ghi corrupted JSON tại `data/clean/papers_clean_corrupted.json`. Đây là bước chuẩn bị một lượt benchmark mới; nó ghi đè benchmark/log hiện có. Trong luồng baseline → corrupted → repaired của nhóm, chỉ build benchmark một lần, rồi dùng lại cùng file cho cả ba trạng thái.

## 5. Quyết định kỹ thuật quan trọng

Chọn lấy mẫu theo thứ tự ngày/ID cố định thay vì lấy ngẫu nhiên. Cách này cho kết quả tái lập ngay cả khi input bị đảo thứ tự, đồng thời bao phủ bài mới nhất và cũ nhất. Đổi lại, đây là benchmark nhỏ theo metadata, chưa đại diện đầy đủ cho truy vấn ngữ nghĩa phức tạp.

Giữ ground truth sạch và paper IDs cố định giúp phép so sánh không bị thay đổi đáp án theo dữ liệu lỗi. Kiểm thử xác nhận corruption không sửa bytes của benchmark và không sửa DataFrame đầu vào.

## 6. Lỗi và blocker đã xử lý

- Hai hàm ban đầu ném `NotImplementedError` với thông báo `Student task: implement test set builder.` và `Student task: implement corruption flow.` Đã thay bằng triển khai có kiểm tra contract và log, xác minh bằng 15 kiểm thử.
- `evaluation/__init__.py` ban đầu import `metrics` ngay lập tức, kéo theo datasets, retrieval và các thư viện model khi chỉ cần benchmark. Đã chuyển exports của metrics sang lazy import; kiểm thử xác nhận import benchmark không nạp `evaluation.metrics` hay `sentence_transformers`.
- Python trong `.venv` dùng bản Microsoft Store, bị chặn trong sandbox (`The file cannot be accessed by the system.`). Đã chạy các lệnh kiểm thử trong chế độ được môi trường phê duyệt; không thay đổi interpreter của dự án.
- Blocker tích hợp còn lại: `cleaning.py`, `quality.py`, `phase1.py`, `corruption_flow.py` còn TODO trong phiên làm việc này. Vì vậy chỉ xác minh hai module với fixture, chưa có cơ sở kết luận về chất lượng RAG hoặc repair. Nhóm cần hoàn thiện các module này rồi chạy hai entrypoint pipeline.

## 7. Hiểu biết luồng end-to-end

1. Crossref cung cấp raw metadata; cleaning chuẩn hóa văn bản, ID, ngày và helper fields; embedding biến `text_for_embedding` thành vector để nạp index.
2. `ground_truth_doc_ids` cho biết tài liệu đúng cần xuất hiện trong retrieval. `ground_truth` là đáp án tham chiếu để đo Token F1 và các chỉ số đánh giá câu trả lời.
3. Quality checks kiểm tra cấu trúc và nội dung như thiếu dữ liệu, trùng ID, độ dài summary. Freshness đo tuổi dữ liệu và tỷ lệ quá hạn; dữ liệu đúng schema vẫn có thể cũ.
4. Cùng test set, model và cấu hình retrieval giúp thay đổi chỉ số phản ánh ảnh hưởng của dữ liệu.
5. Repair cần dựng lại từ raw đáng tin cậy, tạo lại index, chạy quality/freshness và đo lại trên benchmark cũ. Cần so sánh artifacts và metrics với baseline, đồng thời kiểm tra repair lặp lại không làm phát sinh khác biệt dữ liệu.

## 8. Phân tích kết quả thực tế

Các tín hiệu sau được tính trực tiếp trên snapshot fixture và corrupted fixture, không phải GX validation:

| Tín hiệu | Trước corruption | Sau corruption |
| --- | ---: | ---: |
| Tổng số dòng | 24 | 21 |
| Paper IDs duy nhất | 24 | 19 |
| Summary rỗng | 0 | 4 |
| Summary chứa tiền tố rác | 0 | 4 |
| Tiêu đề dưới 8 ký tự | 0 | 4 |
| Dòng trùng thêm theo paper_id | 0 | 2 |
| Dòng quá 180 ngày | 1 | 10 |
| Tỷ lệ quá 180 ngày | 4,17% | 47,62% |

Tám dòng bị lùi ngày kết hợp với dòng cũ có sẵn và bản sao của dòng cũ khiến tổng số dòng stale là 10. Tỷ lệ cuối vượt ngưỡng SLA 25% trong đề bài; đây là tín hiệu từ phép đếm, chưa phải kết quả gọi Quality Gate.

Hai trong mười câu benchmark có ground-truth document bị xóa. Nếu index corrupted chứa đúng corpus còn lại, không có vector cũ sót lại và vẫn dùng benchmark này, retrieval hit rate không thể vượt 80%. Đây là **giới hạn suy ra từ độ phủ tài liệu**, không phải retrieval hit rate đã đo.

Chuỗi nguyên nhân có bằng chứng: drop 5 bài mới → mất ground-truth document của 2 câu; blank/noise/truncate/stale → các tín hiệu dữ liệu xấu tăng như bảng trên. Mức ảnh hưởng thực tế tới agent cần đo sau khi tích hợp; chưa xếp hạng corruption nào gây hại nhất. Chuỗi repair → tín hiệu phục hồi → metric phục hồi chưa được kiểm chứng.

| Chỉ số toàn pipeline | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| retrieval_hit_rate | Chưa đo | Chưa đo | Chưa đo |
| mean_token_f1 | Chưa đo | Chưa đo | Chưa đo |
| judge_accuracy / mean_judge_score | Chưa đo | Chưa đo | Chưa đo |
| GX quality checks | Chưa chạy | Chưa chạy | Chưa chạy |
| Freshness qua module observability | Chưa chạy | Chưa chạy | Chưa chạy |

Lưu ý khi đọc kết quả sau tích hợp: QA hiện có ưu tiên tra cứu chính xác tiêu đề/ID trước kết quả tìm kiếm vector. Vì vậy benchmark này đo hành vi QA của repo, không tách riêng chất lượng semantic retrieval thuần túy.

## 9. Điều học được và hướng cải thiện

1. Metadata và trường embedding phải đồng bộ sau mỗi biến đổi, nếu không thử nghiệm corruption sẽ đo sai tác động.
2. Log theo paper ID và giá trị trước/sau giúp chứng minh lỗi đã được tiêm; chỉ đếm số dòng cuối là chưa đủ vì duplicate có thể che bớt mất dữ liệu.
3. Tín hiệu chất lượng dữ liệu và chất lượng câu trả lời là hai lớp bằng chứng khác nhau; cần đo cả hai khi tích hợp.

Hướng cải thiện: chạy từng corruption riêng trên cùng baseline để tách tác động, bổ sung câu hỏi diễn đạt lại không dùng tiêu đề chính xác và đo Hit Rate/Token F1 cho từng nhóm. Giữ snapshot, benchmark và cấu hình cố định giữa các lần đo.

## 10. Tự kiểm tra và xác nhận của thành viên

Báo cáo được chuẩn bị từ mã nguồn và kết quả chạy trong workspace với hỗ trợ AI. Thành viên cần đọc, kiểm tra và tự xác nhận mức hiểu trước khi nộp:

- [ ] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi giải thích được benchmark, sáu lỗi, log và luồng end-to-end.
- [ ] Tôi đã đối chiếu các kết luận với artifact và hiểu giới hạn chưa tích hợp.
- [ ] Tôi đã rà soát báo cáo và thay đổi trước khi commit bằng tài khoản của mình.

**Họ và tên:** Nguyễn Minh Ngọc  
**Ngày tự xác nhận:** Chưa xác nhận.
