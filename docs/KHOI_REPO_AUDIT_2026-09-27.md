# Đánh giá repo nhánh khoi và kế hoạch hoàn thiện

Ngày kiểm tra: **27/09/2026 (Asia/Saigon)**. Phạm vi được người dùng xác nhận: **chỉ nhánh `khoi` đang mở**, gồm working tree và artifact hiện có; không đánh giá thành quả của `origin/main`.

Căn cứ: [CHECKPOINTS.md](CHECKPOINTS.md), [RUBRIC.md](RUBRIC.md) và [SUBMISSION.md](SUBMISSION.md). Trong repo, rubric nằm tại **`docs/RUBRIC.md`**, không phải thư mục gốc.

## 1. Kết luận chính

**Đã triển khai luồng và có artifact đến CP5. CP5 chưa hoàn tất về khả năng chạy lặp an toàn; CP6 chưa đủ bằng chứng nghiệm thu.** Không nên dùng tên báo cáo cũ “STEP_6_FINAL_ACCEPTANCE” để kết luận đã hoàn thành checkpoint 6 của môn học.

- CP0–CP4 có bằng chứng chức năng trên snapshot: 24 bài, cleaning, GX, 10 câu hỏi, baseline và sáu kiểu corruption. Tuy nhiên, baseline hiện có lỗi về thứ tự Quality Gate và chưa được chạy end-to-end mới với ghi đĩa trong lượt kiểm tra này.
- CP5 phục hồi đúng nội dung và metrics trong artifact; hàm repair cho kết quả xác định. **Toàn bộ lệnh corruption chưa chạy lặp được** khi đầu ra đã tồn tại và chưa có cơ chế repair kích hoạt theo cảnh báo để tính bonus tự phục hồi.
- CP6 còn thiếu hồ sơ thực tế trên nhánh này, bản bàn giao Git đầy đủ và bằng chứng live demo/đóng góp/LMS.
- Các số liệu hiện có **nhất quán khi tính lại**. Điểm yếu chính là khả năng chạy lại, bảo vệ index, mức bao phủ của benchmark và chứng minh chất lượng LLM; không có cơ sở từ kiểm tra này để nói metrics bị bịa.

| Chỉ số kiểm chứng từ artifact | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Dòng dữ liệu / tài liệu index | 24 | 20 | 24 |
| DOI duy nhất | 24 | 19 | 24 |
| Câu hỏi dùng chung | 10 | 10 | 10 |
| Retrieval Hit Rate, top-k mặc định 4 | 100% | 80% | 100% |
| Mean Token F1 theo cách tính hiện tại | 1.000000 | 0.974074 | 1.000000 |
| Judge accuracy | 100% | 100% | 100% |
| Mean judge score / 5 | 5.0 | 4.8 | 5.0 |
| GX expectations đạt | 7/7 | 3/7 | 7/7 |
| Quality tổng hợp | Đạt | Không đạt | Đạt |
| Bài quá 180 ngày | 1/24 | 2/20 | 1/24 |
| Freshness SLA | Đạt | Đạt | Đạt |

Hit Rate giảm **20 điểm phần trăm** và phục hồi; F1 giảm khoảng **0.025926**. Đây là suy giảm quan sát được, chưa phải suy giảm mạnh trên mọi loại lỗi. Freshness của corrupted vẫn đạt là **đúng quy tắc hiện tại**: 10% chưa vượt 25%.

Nguồn: [baseline_metrics.json](../data/results/baseline_metrics.json), [corrupted_metrics.json](../data/results/corrupted_metrics.json), [repaired_metrics.json](../data/results/repaired_metrics.json), [corruption_report.md](../data/reports/corruption_report.md).

## 2. Phạm vi, phương pháp và giới hạn kiểm chứng

### 2.1. Trạng thái mã nguồn

HEAD khi kiểm tra: `1d4a9bc`, nhánh `khoi`.

Các thay đổi đã có trước khi kiểm tra:

- `script/run_phase1.py`, `src/pipelines/phase1.py`, `src/observability/reporting.py` đang modified.
- `data/chroma/chroma.sqlite3` đang modified.
- Segment baseline đang được DB tham chiếu, `data/chroma/0a5e1925-42cb-4dd0-88d5-6958b9b49b2b/`, chưa được Git theo dõi.
- Các JSON/CSV clean, embedding manifest, test set, quality, metrics, answers và báo cáo kết quả trong working tree phần lớn chưa được Git theo dõi.
- Ở HEAD của `khoi`, các thư mục `data/clean`, `data/embeddings`, `data/eval`, `data/quality`, `data/reports`, `data/results` chỉ có `.gitkeep` được theo dõi.

Vì vậy **“có trên máy” và “có trong commit bàn giao” là hai trạng thái khác nhau**. Báo cáo này đánh giá working tree hiện tại, không đồng nhất nó với bản clone từ commit HEAD.

### 2.2. Đã đọc và kiểm tra

Đã đọc 24 file Python thuộc `src/` và `script/`, cấu hình môi trường/đóng gói, lockfile ở các mục liên quan, tài liệu hướng dẫn/checkpoint/rubric, các báo cáo cũ và mẫu báo cáo nộp bài. Đã đối chiếu toàn bộ nhóm artifact raw/clean/eval/quality/results/embeddings/reports, đọc hai SQLite Chroma ở chế độ chỉ đọc và kiểm tra segment liên quan.

`acceptance_runs/` là thư mục bị Git ignore chứa lần chạy, môi trường và cache cũ. Chỉ các script kiểm chứng, metadata chạy và log tổng hợp liên quan được dùng làm bằng chứng lịch sử; không coi thư viện bên thứ ba/cache là mã nguồn dự án cần duyệt từng file.

### 2.3. Cách giữ nguyên file

- Không chạy cài đặt dependency, tải model, gọi API thật, tạo test file, tạo log file, checkout, commit hoặc push.
- Python chạy qua stdin với `-B`; harness có audit hook chặn thao tác ghi/xóa/đổi tên và mạng.
- Ingestion, cleaning, corruption, test set, freshness và GX được chạy lại trong bộ nhớ.
- GX thật chạy với store trong RAM và tắt tạo thư mục Data Docs tạm **chỉ trong harness**. Expectations và thuật toán của repo không bị sửa.
- Kiểm tra agent dùng LangChain thật và mock model của repo, index bằng manifest trong RAM. Client provider thật được thay bằng mock khi kiểm tra routing.
- Kiểm tra orchestration/failure dùng mock tại biên ghi file, model và database; không giả định các mock này chứng minh MiniLM/Chroma chạy end-to-end.
- SQLite mở bằng URI `mode=ro&immutable=1`; không mở `PersistentClient` lên DB hiện hữu.
- Đối chiếu SHA-256 của **101 file dự án/artifact** trước và sau các phép kiểm tra: **không đổi, không xuất hiện file mới** trước khi tạo báo cáo này. Phạm vi hash không gồm `.git`, `.env`, virtualenv, cache hay `acceptance_runs/`.

**Không chạy nguyên xi hai CLI để tạo lại artifact**, vì baseline chắc chắn ghi đè dữ liệu/index và GX/thư viện có thể tạo file tạm. Điều đó trái với giới hạn chỉ được tạo báo cáo Markdown. Kết quả dưới đây phân biệt rõ kiểm tra mới trong RAM, artifact hiện hữu, log cũ và nhận định từ mã nguồn.

### 2.4. Môi trường kiểm tra

Interpreter: `.venv/Scripts/python.exe`, Python **3.11.9**. Các phiên bản sau khớp các mục tương ứng trong `uv.lock`:

| Package | Phiên bản |
| --- | --- |
| chromadb | 1.5.9 |
| great-expectations | 1.18.0 |
| sentence-transformers | 5.5.1 |
| langchain | 1.3.4 |
| pandas | 3.0.3 |
| numpy | 2.4.6 |

`pytest` chưa được cài trong `.venv`; nó là dependency tùy chọn `dev`, nên đây không phải lỗi khiến baseline bắt buộc phải fail. Không có bộ pytest/CI trong mã nguồn nhánh này. `pipelines` importable qua cấu hình đường dẫn hiện có của `.venv`.

Các log cũ trong `acceptance_runs/final_source_clean_env_20260926_01/` và lần `recheck_20260926_01/` ghi hai entrypoint exit 0 và 33/33 kiểm tra artifact. Đây là bằng chứng đã từng chạy bằng wrapper/output riêng; **không chứng minh nguyên trạng working tree hiện tại chạy thành công một lần mới**. Báo cáo cũ nói virtualenv thiếu dependency không còn phản ánh đúng `.venv` hiện tại.

## 3. Đối chiếu từng checkpoint

| CP | Đánh giá nhánh khoi hiện tại | Bằng chứng và phần còn thiếu |
| --- | --- | --- |
| **CP0** | Đạt phần ingestion offline; môi trường có dependency | Hai raw snapshot parse thành 24 records giống nhau. Thử giả lập mạng lỗi và HTTP 429 đều fallback đúng; 429 gọi ba lần. Chưa kiểm tra API/key thật hoặc tái cài môi trường trong lượt này. Nhánh chỉ có API snapshot chưa tự tạo parsed artifact còn thiếu. |
| **CP1** | Đạt dữ liệu chuẩn; cần hoàn thiện xử lý biên và vị trí gate | Clean 24 DOI duy nhất, đủ 16 cột và 5 phần embedding text; khớp dữ liệu lưu. GX thật đạt 7/7. Freshness đúng ngưỡng 180 ngày và 25%. Tuổi không hữu hạn có thể lọt; Quality Gate đang nằm sau indexing/evaluation. |
| **CP2** | Đạt artifact và cấu trúc benchmark | Test set sinh lại giống file lưu: 10 câu, summary 3/authors 3/date 2/categories 2. SQLite baseline có 24 tài liệu, dimension 384. Chưa encode/query MiniLM mới; benchmark phụ thuộc exact DOI. |
| **CP3** | Có baseline/report và bằng chứng chạy cũ; chưa chốt nghiệm thu bản hiện tại | Tính lại metrics từ answers khớp hoàn toàn. Báo cáo baseline đủ kết quả. Cần chạy lại bản đã sửa thứ tự gate trong output riêng; báo cáo cũ không thay thế kiểm chứng regression hiện tại. |
| **CP4** | Đạt cơ chế corruption và có suy giảm đo được | Sáu lỗi thật, deterministic, log khớp dữ liệu. Corrupted 20 dòng/19 DOI; GX fail 4 checks; Hit Rate 1.0 → 0.8. Chưa có phân tích độc lập hiệu ứng của cả sáu lỗi. |
| **CP5** | Đạt phục hồi nội dung và bảng so sánh; chưa hoàn chỉnh khả năng vận hành lặp | Repair hai lần từ raw với ngày baseline cho cùng dữ liệu, khớp saved baseline/repaired. Metrics phục hồi. `main()` corruption tái hiện `FileExistsError` với output hiện có; repair chưa do quality failure kích hoạt; chưa chặn việc công nhận repaired khi quality fail. |
| **CP6** | Chưa đủ điều kiện xác nhận hoàn thành | TEAM và báo cáo nhóm/cá nhân ở nhánh này còn là mẫu. Artifact/mã nguồn chưa được bàn giao đầy đủ vào Git. Không có xác minh live demo, tất cả thành viên trên main và từng lượt nộp LMS trong phạm vi này. |

Kết luận checkpoint nên dùng khi báo cáo tiến độ: **“Đã có triển khai và kết quả đến CP5; đang hoàn thiện khả năng chạy lại, kiểm soát chất lượng và hồ sơ CP6.”**

## 4. Đối chiếu RUBRIC.md

Rubric không quy định thang điểm con cho từng lỗi. Bảng này đánh giá bằng chứng theo trọng số; không tự đặt mức trừ điểm và không thay điểm của giảng viên.

| Hạng mục | Điểm tối đa | Đánh giá bằng chứng | Việc cần bổ sung để bảo vệ điểm tối đa |
| --- | ---: | --- | --- |
| Cấu trúc và môi trường | 10 | Module rõ; pyproject/requirements/lock có đủ; có venv đã cài | Chuẩn hóa cách chạy cả hai entrypoint, cấu hình output riêng, xác minh bản bàn giao từ môi trường sạch. |
| Raw ingestion và lineage | 15 | Đạt trên snapshot; network/429 fallback có kiểm tra mới | Hoàn chỉnh trường hợp chỉ có response snapshot và kiểm tra schema payload trước khi parse. |
| Cleaning và pre-embed modeling | 15 | Đạt trên dữ liệu chuẩn; loại tag, chuẩn DOI, deduplicate, age và 5 phần text | Chốt chính sách ngày tương lai và kiểm tra tính nhất quán published/age. |
| Embedding và vector store | 10 | Có MiniLM code, manifest và vector 384 chiều, ba collection đúng số lượng | Chứng minh encode/search mới trong lần nghiệm thu được phép ghi; sửa khả năng mất collection khi build lỗi và đường dẫn manifest không di chuyển được. |
| Multi-provider QA agent | 10 | Mock agent dùng tool trả đúng 10/10 câu; google/gemini/openai/anthropic routing đúng qua client mock | Kiểm tra trả lời ngoài corpus; tích hợp/đo riêng agent thật. Baseline hiện đo QA trích xuất metadata, không đo agent LLM. |
| Baseline evaluation | 10 | Đủ 10 câu/4 nhóm; Hit Rate/F1/answers/report nhất quán | Bổ sung câu hỏi ngữ nghĩa không tiết lộ ID, metric theo loại câu và provenance của judge. |
| GX 1.x và Freshness | 15 | Đúng API 1.x; 7 expectations thuộc 4 loại; biên SLA đúng | Gate phải chạy trước publish/index; chặn tuổi không hữu hạn và dữ liệu thời gian không nhất quán. |
| Corruption, repair và impact analysis | 15 | Đủ sáu lỗi, dữ liệu repair đúng và bảng ba trạng thái có suy giảm | Chạy lặp an toàn, kiểm tra repaired quality, đánh giá ảnh hưởng từng lỗi và giải thích giới hạn benchmark. |

**Chưa có cơ sở xác nhận điểm tối đa 100/100.** Nhiều deliverable cốt lõi đã có, nên cũng không phù hợp đánh giá dự án là scaffold chưa làm.

| Bonus | Tối đa | Trạng thái chỉ trên nhánh khoi |
| --- | ---: | --- |
| B1 Dashboard/drift monitor | +5 | Không thấy mã/artefact dashboard trong working tree này. |
| B2 Automated self-healing | +5 | Repair chạy theo chuỗi cố định; chưa có điều kiện cảnh báo → repair/rollback được kiểm chứng. |
| B3 Pytest CI, coverage >80% | +5 | Chưa có bộ test/CI và không có số đo coverage. Harness kiểm tra trong lượt này không thay thế deliverable đó. |

Chưa xác nhận bonus. Rubric chỉ xét bonus khi phần bắt buộc đạt ít nhất 85 và tổng bonus không quá 10.

Về deductions: `.env` không nằm trong tracked files và truy vấn lịch sử local theo đường dẫn `.env` không có kết quả. Quét một số mẫu secret phổ biến trong file tracked hiện tại không tìm thấy khớp; đây không phải chứng nhận toàn bộ lịch sử không có secret. Chưa có bằng chứng để kết luận vi phạm deadline/LMS. TEAM chưa điền có nguy cơ bị trừ theo rubric, nhưng chưa xác định số thành viên thực tế từ nhánh này nên không tự tính mức phạt.

## 5. Kết quả chạy kiểm tra mới

| Mã | Kiểm tra thực hiện | Kết quả |
| --- | --- | --- |
| T01 | Parse AST toàn bộ 24 file Python | Không có lỗi cú pháp. |
| T02 | Đọc cả hai raw snapshot, đối chiếu mọi PaperRecord | 24/24, cùng nội dung và DOI. |
| T03 | Cleaning tại ngày 26/09/2026, đối chiếu saved JSON | Khớp 24 dòng/16 cột; 24 DOI duy nhất. |
| T04 | Cleaning/freshness tại ngày kiểm tra 27/09/2026 | 24 dòng, 1 bài quá 180 ngày, SLA đạt. |
| T05 | Sinh test set không truyền output path | 10 câu/4 nhóm, khớp saved test set. |
| T06 | Corruption hai lần trong RAM; so input và log | 20 dòng/19 DOI; 6 event; deterministic; input không đổi; output/log khớp file lưu. |
| T07 | Repair từ raw hai lần cùng ngày baseline | Khớp baseline và repaired đã lưu. |
| T08 | Mock lỗi mạng, 429 và response thành công | Fallback 24 records; 429 thử 3 lần; nhánh thành công gọi ghi 2 artifact qua mock. |
| T09 | GX thật, in-memory store không tạo Data Docs | Baseline 7/7; corrupted 3/7; repaired 7/7. |
| T10 | Biên SLA: tuổi 180/181, stale 6/24 và 7/24 | 180 không stale; 25% đạt; 29.17% không đạt. |
| T11 | Age toàn -1, NaN, -Infinity | -1 và -Infinity vẫn báo fresh; NaN bị đánh dấu không fresh. Cần sửa kiểm tra dữ liệu số và chính sách ngày tương lai. |
| T12 | Tính lại Hit Rate, Token F1 và tổng hợp judge cho 30 answers | Tất cả khớp metrics JSON; câu hỏi/ground truth nhất quán với test set. |
| T13 | So CSV/JSON, manifest/document content | Số dòng và các trường vô hướng/text/age kiểm tra đều khớp ở ba trạng thái. |
| T14 | SQLite immutable, quick_check, collections, vectors | Cả 2 DB trả ok; số tài liệu 24/20/24; dimension 384; 68 vector FLOAT32 dài 1536 byte, norm xấp xỉ 1; các thư mục vector segment đang tham chiếu đều tồn tại. |
| T15 | LangChain agent thật + mock model repo + manifest index | 10/10 câu benchmark trả đúng ground truth bằng tool lookup. Không chứng minh retrieval ngữ nghĩa hoặc provider online. |
| T16 | Routing google/gemini/openai/anthropic, constructor mock | Gọi đúng constructor tương ứng. Mock judge dùng heuristic fallback như dự kiến. |
| T17 | DOI không tồn tại với index giả lập trả ứng viên không liên quan | Cả QA và mock agent trả tên tác giả của bài khác; chưa từ chối câu hỏi. |
| T18 | Gọi corruption main với dependency nặng được cô lập | Mock provider: FileExistsError vì output tồn tại. Gemini: RuntimeError yêu cầu LLM_PROVIDER=mock. Không ghi file. |
| T19 | Baseline 23 records, mô phỏng quality fail và ghi/index bằng mock | Thứ tự thực tế: ghi clean → index → testset → evaluate → quality fail → report → RuntimeError. |
| T20 | Index build, giả lập embed_documents ném lỗi | Xóa collection cũ → tạo collection rỗng → lỗi embedding. |
| T21 | Index load sau đổi settings.paths.chroma_dir | Vẫn truyền đường dẫn tuyệt đối cũ từ manifest vào constructor. |
| T22 | Chỉ có response snapshot, giả lập parsed path không tồn tại | Đọc được 24 records nhưng không gọi lưu parsed artifact. |
| T23 | Crossref payload có message=null | AttributeError: 'NoneType' object has no attribute 'get'. |
| T24 | Hash bảo toàn trước khi tạo báo cáo | 101 file không đổi, không có file dự án mới. |

T14 xác nhận cấu trúc/giá trị vector đang lưu; không thể chỉ từ dimension/norm chứng minh chắc chắn model đã tạo ra chúng. T15–T21 sử dụng biên mock rõ ràng, không được gọi là chạy lại end-to-end MiniLM + Chroma.

### Lỗi của harness do ràng buộc chỉ đọc

Lần thử ban đầu import thư viện bị guard chặn mở thiết bị `nul`; đây không phải file dữ liệu, nên harness được điều chỉnh cho phép thiết bị null. GX mặc định dù dùng ephemeral context vẫn thử tạo TemporaryDirectory cho Data Docs và bị guard chặn, dẫn đến `FileNotFoundError: No usable temporary directory found`.

Sau đó harness dùng `DataContextConfig` với `InMemoryStoreBackendDefaults(init_temp_docs_sites=False)`; GX chạy thành công, không ghi file. Lần import/agent ban đầu còn dò temp nhiều lần; harness sau đặt đường dẫn temp có sẵn, và lần kiểm tra orchestration/agent cuối exit 0 với **0 thao tác ghi bị yêu cầu**. Các lỗi này do chế độ audit nghiêm ngặt, không được tính là lỗi GX/production của repo.

Lỗi OpenBLAS/paging file nằm trong [báo cáo chẩn đoán cũ](../data/reports/phase1_openblas_diagnostic_report.md). Không tái hiện lỗi đó trong các phép kiểm tra mới; không suy diễn rằng hệ thống vẫn đang thiếu bộ nhớ như tại thời điểm log cũ.

## 6. Lỗi và khoảng trống cần xử lý, theo ưu tiên

Các thay đổi dưới đây **chỉ là đề xuất**, chưa thực hiện. Số dòng tham chiếu theo working tree tại thời điểm kiểm tra.

### F01 — P1: Quality Gate chạy quá muộn, dữ liệu không đạt đã vào index

**Vị trí:** [phase1.py](../src/pipelines/phase1.py), `run_phase1_pipeline`, dòng 31, 37, 49, 67 và nhánh raise cuối hàm.

T19 tái hiện việc clean output, index, test set và evaluation đều xảy ra trước khi chất lượng được kiểm tra. Khi gate fail, pipeline có ném RuntimeError nhưng index/artifact mới đã được tạo hoặc thay thế. Đây là regression so với mô tả pipeline trong báo cáo STEP_3_4_5 cũ.

**Đề xuất sửa:** Sau cleaning, tính GX/freshness trước indexing/evaluation. Ghi diagnostic của lần thất bại vào output riêng; chỉ công nhận/publish baseline khi gate pass. Tách thư mục/kết quả của từng run để không trộn một lần chạy lỗi với baseline tốt.

**Nghiệm thu:** Với 23 dòng hoặc dữ liệu vi phạm title/summary/freshness, trả trạng thái thất bại; không gọi index build/evaluation và hash của baseline được công nhận trước đó không đổi. Dữ liệu hợp lệ vẫn chạy đủ sáu bước chức năng.

### F02 — P1: Index build có thể làm mất collection đang tốt khi embedding lỗi

**Vị trí:** [index.py](../src/retrieval/index.py), `LocalEmbeddingIndex.build`, dòng 93–109.

T20 xác nhận collection cũ bị xóa, collection rỗng được tạo, sau đó mới gọi `embed_documents`. Nếu encode/add thất bại, không có rollback. Việc bắt toàn bộ Exception quanh delete cũng có thể che lỗi khác với “collection chưa tồn tại”.

**Đề xuất sửa:** Encode và kiểm tra vector trước; build vào collection của run mới; kiểm tra count/query rồi mới chuyển manifest/tham chiếu serving. Giữ bản tốt cũ đến khi run mới được công nhận. Chỉ bắt ngoại lệ cần thiết và ghi rõ nguyên nhân.

**Nghiệm thu:** Inject failure tại encode/add/validation; baseline cũ vẫn truy vấn được và manifest cũ không bị đổi.

### F03 — P1: Corruption CLI không chạy lặp được; repair chưa có gate nghiệm thu

**Vị trí:** [corruption_flow.py](../src/pipelines/corruption_flow.py), `main`, dòng 24–47 và 127–140; [reporting.py](../src/observability/reporting.py), `generate_corruption_report`, dòng 109–110; [corruption.py](../src/ingestion/corruption.py), dòng 31–32 nếu truyền log path đã tồn tại.

Lỗi tái hiện:

```text
FileExistsError: Comparison would replace existing data: .../data/results/corruption_log.json, ...
RuntimeError: Set LLM_PROVIDER=mock for the offline comparison run.
```

Từ chối ghi đè có tác dụng bảo vệ kết quả cũ, nhưng hiện không có CLI chọn output/run mới. Có đầu ra dở dang sau một lần lỗi cũng chặn lần chạy tiếp. Hàm cleaning lặp lại xác định không tương đương toàn pipeline idempotent.

Mã nguồn tính `repaired_quality` nhưng không kiểm tra `success` trước khi index/evaluate/in báo cáo hoàn thành. Repair cũng diễn ra theo chuỗi cố định, không có nhánh điều kiện từ quality/freshness; chưa đủ bonus B2.

**Đề xuất sửa:** Thêm `--output-dir`/`--run-id`, run manifest và quy tắc resume hoặc nhận diện run đã hoàn thành. Cho phép chạy lại an toàn, không yêu cầu người dùng xóa bằng tay toàn bộ data. Kiểm tra baseline đầu vào thuộc cùng run và quality hợp lệ; yêu cầu repaired quality pass trước khi công nhận phục hồi. Với mục tiêu B2, thêm điều kiện quality/freshness fail → repair/rollback; không repair khi dữ liệu đã đạt.

**Nghiệm thu:** Chạy hai lần cùng input có hành vi lặp an toàn, không nhân đôi tài liệu; chạy run mới không phá run cũ. Run lỗi giữa chừng có cách tiếp tục rõ. Repaired quality fail phải làm lần phục hồi thất bại và giữ bản tốt.

### F04 — P1: Bản bàn giao chưa phản ánh working tree được kiểm tra

**Vị trí:** Git state; ba source file modified, DB modified và artifact untracked nêu ở mục 2.1.

Đặc biệt, SQLite baseline hiện tham chiếu segment mới chưa tracked. Nếu chỉ commit SQLite mà bỏ segment, bản clone có thể không đầy đủ. Bản HEAD cũng chưa chứa các báo cáo/metrics được dùng để kết luận.

**Đề xuất xử lý sau khi ổn định mã:** Chọn bản nguồn và một bộ artifact nhất quán theo cùng run; kiểm tra đủ DB/segment/manifest nếu bàn giao persist directory; commit các deliverable thực tế được yêu cầu. Nếu chọn tái sinh DB, phải cung cấp đường tái sinh đã kiểm chứng và không để manifest trỏ tới máy cũ. Không gom cache/virtualenv/secret vào commit.

**Nghiệm thu:** Một bản clone/checkout biệt lập của commit dự kiến bàn giao có đủ artifact yêu cầu hoặc tái sinh được theo hướng dẫn; metrics/report khớp. Lượt audit này không thực hiện commit.

### F05 — P1: Không có chính sách từ chối khi hỏi DOI ngoài corpus

**Vị trí:** [qa.py](../src/retrieval/qa.py), `answer_question`, dòng 33–50; [llm.py](../src/retrieval/llm.py), `_MockPaperChatModel._generate`, nhánh lookup thất bại → semantic search.

T17 hỏi DOI `10.invalid/not-in-corpus`; khi search trả ứng viên khác, QA và mock agent trả `Quang Le, Yen Vu`. Đây là phép thử có index giả lập; nó chứng minh thiếu guard ở tầng trả lời, không phải phép đo chất lượng search thật.

**Đề xuất sửa:** Với câu hỏi định danh rõ DOI, nếu ID không tồn tại thì trả lời không đủ dữ liệu, không dùng metadata của DOI khác. Với câu hỏi mở, áp dụng chính sách độ tin cậy và dẫn nguồn. Thêm challenge set ngoài corpus, DOI bị drop và trường metadata rỗng.

**Nghiệm thu:** Câu hỏi về DOI không có hoặc đã bị drop phải từ chối hoặc nói rõ không tìm thấy; không trả thông tin của tài liệu thay thế như thể đúng đối tượng.

### F06 — P2: Benchmark che một phần tác động corruption; số judge chưa phản ánh LLM

**Vị trí:** [testset.py](../src/evaluation/testset.py), dòng 29–46; [qa.py](../src/retrieval/qa.py), dòng 33–44; [metrics.py](../src/evaluation/metrics.py), dòng 33–70 và 115–137; [reporting.py](../src/observability/reporting.py).

- 10/10 câu có DOI; lookup đưa tài liệu exact match lên đầu. Hit Rate vì thế đo cả lookup, không đo riêng semantic retrieval.
- Summary reference và câu trả lời đều lấy câu đầu summary, nên baseline F1=1 là kết quả dễ đạt với benchmark này.
- Chỉ q001 và q002 mất retrieval hit. q002 vẫn F1=1 vì tác giả bài thay thế trùng đáp án.
- Stale date tác động DOI `...1806`, nhưng câu benchmark cho bài đó hỏi summary. Truncate title tác động `...1805`, nhưng câu benchmark hỏi authors và vẫn lookup bằng DOI. Blank/noise/duplicate không có câu hỏi tương ứng nhạy với đúng trường bị đổi.
- 30/30 judge verdicts trong artifact ghi fallback heuristic. `judge_accuracy=100%` không phải 100% đúng theo LLM độc lập.
- `_token_f1` dùng set token, bỏ tần suất. Ví dụ `a a a b` và `a b b b` vẫn cho 1.0. Báo cáo hiện có mô tả token-set overlap nên đây là giới hạn định nghĩa, không phải bằng chứng tính sai so với code.
- `refresh_test_set` được khai báo nhưng không dùng; phase1 luôn gọi sinh lại test set. Khi input đổi, benchmark có thể thay mà không có phiên bản/hash.

**Đề xuất sửa:** Giữ benchmark 10 câu theo lab và phiên bản/hash ổn định; thêm một tập đánh giá độc lập gồm câu paraphrase không DOI, câu ngoài corpus và kiểm tra nhạy theo sáu lỗi. Báo cáo riêng exact lookup/semantic retrieval, Hit@1/Hit@k, chỉ số theo loại câu và độ giảm/phục hồi. Ghi `judge_backend`, số lượt fallback và nguyên nhân đã che bí mật; có strict mode nếu tuyên bố dùng LLM judge. Chốt tên/định nghĩa token-set F1 hoặc đổi sang multiset và tạo run metric mới, không sửa tay số cũ.

**Nghiệm thu:** Không thay ground truth giữa ba trạng thái trong một run. Nêu rõ lỗi nào làm đổi quality, retrieval hoặc answer và lỗi nào không. Nếu kết quả không giảm, báo trung thực; không điều chỉnh sau khi xem kết quả để ép mức sụt giảm.

### F07 — P2: Freshness thiếu kiểm tra tuổi hữu hạn và nhất quán với ngày

**Vị trí:** [quality.py](../src/observability/quality.py), `_freshness_metrics`, dòng 12–31; [cleaning.py](../src/ingestion/cleaning.py), tính `age_days` trong `build_clean_dataframe`.

`pd.to_numeric(...).notna()` vẫn coi `-Infinity` hợp lệ. Cả cột age=-Infinity báo fresh. Số âm cũng được chấp nhận mà chưa nêu chính sách ngày tương lai. Freshness dựa trực tiếp vào cột age; không đối chiếu với published/run_date.

**Đề xuất sửa:** Xác nhận age hữu hạn, kiểu hợp lệ, tương ứng ngày xuất bản/ngày chạy; quy định rõ ngày tương lai có được chấp nhận hay cần cảnh báo. Giữ nguyên biên SLA đúng hiện tại: >180 ngày và stale ratio >25%.

**Nghiệm thu:** NaN/Infinity/-Infinity/tuổi không nhất quán phải không được báo “fresh” bình thường; 6/24 stale vẫn đạt, 7/24 không đạt. Tách “freshness tại thời điểm benchmark” với “freshness tại ngày phục vụ”; việc cố định ngày baseline để so sánh repair là hợp lý nhưng không thay giám sát thời gian thực.

### F08 — P2: Manifest embedding không di chuyển được sang workspace khác

**Vị trí:** [index.py](../src/retrieval/index.py), dòng 119 và `load` dòng 132–139.

Manifest lưu `persist_path` tuyệt đối. T21 đổi `settings.paths.chroma_dir` nhưng `load()` vẫn dùng đường dẫn cũ trong manifest.

**Đề xuất sửa:** Lưu path tương đối kèm schema/version hoặc resolve từ cấu hình/project root hiện tại; kiểm tra collection/manifest/hash tương ứng. Các đường dẫn trong artifact là đường dẫn sinh lúc chạy, không phải literal ổ đĩa hardcode trong source; không tự áp mức phạt hardcode của rubric.

**Nghiệm thu:** Di chuyển bản dự án sang thư mục khác vẫn load đúng ba collection mà không sửa JSON bằng tay.

### F09 — P2: Fallback raw chưa đảm bảo đủ lineage và lỗi schema chưa thống nhất

**Vị trí:** [crossref.py](../src/ingestion/crossref.py), `parse_crossref_payload` dòng 32–36 và `fetch_source_records` dòng 95–126.

Nếu chỉ có response snapshot, fetch trả 24 records nhưng không lưu `crossref_records.json`; trong khi corruption flow bắt buộc có file parsed này. Payload `message=null` gây AttributeError ngoài nhóm ngoại lệ fallback đang bắt.

**Đề xuất sửa:** Kiểm tra schema từng tầng và báo ValueError có ngữ cảnh; khi offline bootstrap từ response, tạo parsed raw artifact còn thiếu trong chế độ có quyền ghi. Không ghi đè snapshot tốt khi refresh không hợp lệ; thêm provenance/hash giúp nhận diện raw của từng baseline.

**Nghiệm thu:** Khởi đầu chỉ với snapshot response vẫn tạo đủ hai raw artifact và đi tiếp được tới repair. Payload null/sai kiểu được xử lý rõ ràng, có fallback khi snapshot hợp lệ tồn tại.

### F10 — P2: Hướng dẫn môi trường và báo cáo nộp bài chưa hoàn thiện

**Vị trí:** [run_corruption_flow.py](../script/run_corruption_flow.py), [README.md](../README.md), [TEAM.md](TEAM.md), [group_report.md](../report/group_report.md), [individual_report.md](../report/individual_report.md), các STEP summary.

Entrypoint corruption chưa có bootstrap src và giới hạn luồng như baseline. Trong `.venv` hiện tại import path đã hoạt động, nên **không kết luận CLI đang lỗi ModuleNotFoundError**. Tuy nhiên môi trường chỉ cài requirements mà chưa cài project/PYTHONPATH có thể khác; hướng dẫn hiện thiếu quy trình tái hiện rõ cho nhánh này.

`.env.example` mặc định Gemini, còn corruption buộc mock. Các summary cũ mô tả baseline chống ghi đè/gate trước index, khác source đang modified. TEAM và báo cáo nộp bài vẫn có placeholder.

**Đề xuất sửa:** Thống nhất cách chạy qua package/module hoặc bootstrap tương đương; ghi rõ interpreter, cài project, mock mode, cách chọn run/output và cấu hình luồng. Cập nhật báo cáo với commit/run thực tế. Nhóm tự điền danh tính, đóng góp và báo cáo cá nhân; không dùng tên checkpoint của quá trình làm việc thay kết quả học phần.

**Nghiệm thu:** Người mới theo README chạy được hai lệnh trên bản bàn giao; không cần đoán Python/PYTHONPATH/provider. TEAM, báo cáo và evidence khớp, không còn ô mẫu dùng như kết quả đã hoàn thành.

## 7. Kế hoạch tiếp theo

Thứ tự dưới đây ưu tiên đóng lỗi làm hỏng lần chạy trước khi bổ sung bonus. Chưa thực hiện bước sửa nào.

| Bước | Công việc | File chính cần sửa/tạo ở lượt được phép sửa | Tiêu chí hoàn tất |
| --- | --- | --- | --- |
| **1** | Chốt contract run, output riêng và benchmark version | `src/core/config.py`, `script/run_phase1.py`, `script/run_corruption_flow.py`, `README.md` | Chọn được run/output; phân biệt read-only audit với sinh artifact; một run gắn raw/testset/config/commit. |
| **2** | Đưa gate trước index; bảo vệ collection tốt | `src/pipelines/phase1.py`, `src/retrieval/index.py` | T19/T20 đảo thành kết quả an toàn; lỗi không thay baseline đã công nhận. |
| **3** | Hoàn thiện chạy lặp và repair | `src/pipelines/corruption_flow.py`, `src/observability/reporting.py`, `src/ingestion/corruption.py` | Chạy lặp/resume rõ; repaired quality fail không được công nhận thành công; artifact không trộn run. |
| **4** | Vá validation và khả năng di chuyển | `src/observability/quality.py`, `src/ingestion/crossref.py`, `src/retrieval/index.py` | Age không hữu hạn bị phát hiện; raw bootstrap đủ lineage; manifest dùng được ở thư mục khác. |
| **5** | Tăng chất lượng QA và bằng chứng đánh giá | `src/retrieval/qa.py`, `src/retrieval/llm.py`, `src/evaluation/testset.py`, `src/evaluation/metrics.py`, `src/observability/reporting.py` | Từ chối DOI ngoài corpus; bộ câu hỏi cố định; judge provenance; metrics theo nhóm và tác động từng lỗi. |
| **6** | Bổ sung test tự động và chạy nghiệm thu mới | Dự kiến `tests/`, cấu hình dev/CI hoặc script test riêng | Test lỗi thực tế F01–F09; chạy cả hai pipeline với MiniLM/Chroma thật trên output biệt lập; lặp lần hai an toàn. Nếu xin B3 phải đo coverage >80% và có CI/one-click. |
| **7** | Chốt deliverable CP6 | `docs/TEAM.md`, `report/group_report.md`, các báo cáo cá nhân, README và bộ artifact được chọn | Commit nguồn/artifact đầy đủ; kiểm tra bản clone; live demo/Q&A; từng người xác nhận đóng góp và nộp LMS. |
| **8 — tùy chọn** | Bonus sau khi phần bắt buộc ổn định | Dashboard và/hoặc nhánh điều kiện auto-repair | Chứng minh bằng chạy thật; không tự tính điểm khi chưa đạt điều kiện rubric. |

### Bộ nghiệm thu đề xuất sau khi sửa

1. Khởi tạo môi trường theo lock và hướng dẫn được thống nhất; chạy từ commit dự kiến nộp.
2. Dùng raw snapshot hiện có, mock provider và test set đã khóa. Baseline phải có 24 tài liệu, 10 câu, quality pass và artifact cùng run.
3. Chạy corruption/repair: đủ sáu event, quality phản ánh lỗi, so sánh metrics thực đo; repaired dữ liệu đúng và quality pass.
4. Chạy lại cùng run/input: không mất baseline, không duplicate, hành vi resume/reuse hoặc run mới đúng thiết kế.
5. Inject lỗi quality, encode, add và output dở dang: giữ nguyên run tốt; lỗi phải báo đúng tầng.
6. Chạy challenge set DOI ngoài corpus và từng trường bị corrupt; kiểm chứng grounding và provenance của judge.
7. Di chuyển/clone bản bàn giao sang thư mục khác và chạy theo README.
8. Đối chiếu nhóm/cá nhân/main/LMS bằng bằng chứng thực tế do nhóm cung cấp. Ngày audit muộn hơn deadline trong tài liệu không đủ để kết luận đã nộp muộn.

Không nên bắt đầu bằng sửa tay metrics hoặc xóa toàn bộ `data/` để lệnh chạy được. Các số liệu cũ hiện nhất quán và cần được giữ làm bằng chứng so sánh.

## 8. Ghi chú tái hiện kiểm tra chỉ đọc

Các probe chạy bằng dạng `@' ... '@ | .venv/Scripts/python.exe -B -` trong PowerShell; không lưu harness thành file. Biến môi trường override chỉ trong tiến trình Python kiểm tra: mock provider, tắt Ragas/refresh/mạng và giới hạn luồng số học.

Các thao tác đại diện:

```python
# Chỉ các hàm có output_path/report_name mặc định None.
raw = load_raw_records(settings.paths.raw_records_json)
clean = build_clean_dataframe(raw, recorded_baseline_run_date)
questions = build_test_set(clean)
corrupted = corrupt_clean_dataframe(clean)
freshness = build_freshness_report(clean, settings)
# GX cần context in-memory không tạo Data Docs tạm trong chế độ audit.
# Không gọi LocalEmbeddingIndex.build/load lên persistent DB trong audit.
```

```python
# Đọc DB hiện hữu, không tạo WAL/SHM hay chạy migration.
sqlite3.connect(
    database.resolve().as_uri() + "?mode=ro&immutable=1",
    uri=True,
)
```

Các bước dùng mock đã nêu ở T08, T15–T23 phải tiếp tục được ghi nhãn rõ nếu được chuyển thành test chính thức. Không dùng kết quả mock để tuyên bố đã chạy API, model embedding hoặc Chroma search thật.

**File mới duy nhất của lượt đánh giá: `docs/KHOI_REPO_AUDIT_2026-09-27.md`. Không sửa source, cấu hình, dữ liệu, báo cáo cũ hoặc commit.**

