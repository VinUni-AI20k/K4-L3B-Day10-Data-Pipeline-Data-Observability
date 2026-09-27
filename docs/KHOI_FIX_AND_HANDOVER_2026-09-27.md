# Báo cáo sửa lỗi và bàn giao nhánh khoi

Ngày: 27/09/2026. Phạm vi: working tree nhánh `khoi`, không đối chiếu hay tích hợp `origin/main`. Người dùng đã cho phép sửa mã nguồn, tạo test và chạy kiểm chứng; không commit/push và không sửa raw data.

## 1. Kết luận nghiệm thu

Đã xử lý năm nhóm vấn đề trong [audit trước](KHOI_REPO_AUDIT_2026-09-27.md): quality gate chạy muộn, thay index không an toàn, corruption không chạy lặp được, QA lấy nhầm bài khi thiếu DOI, và artifact bàn giao chưa được tập hợp nhất quán. Không giải quyết trạng thái chưa commit bằng cách tự commit; thay vào đó cung cấp manifest, bộ kết quả được chọn và gói ZIP để duyệt.

Run chuẩn duy nhất được chọn: **`khoi_handover_20260927_01`**. [Run manifest](../data/runs/khoi_handover_20260927_01/run_manifest.json) đóng dấu input, source, cấu hình, phiên bản dependency và inventory của hai stage. Run có **49 file**, tổng **2.019.585 byte** trước khi đóng gói. Không lấy metric hoặc report của run lịch sử để ghép vào kết quả mới.

- 24 test hồi quy: đạt.
- 131 kiểm tra độc lập raw/source/artifact/SQLite/metrics/report: đạt.
- Chạy lại hai CLI: thành công, hash cả 49 file không đổi.
- Chuyển nguyên run sang thư mục khác: 99 kiểm tra artifact đạt; 30/30 truy vấn trên Chroma thật trả cùng câu trả lời, retrieved DOI và answer DOI.
- 60 file dữ liệu có trước lượt sửa giữ nguyên hash; cả hai raw gốc được bảo toàn.

Đây là nghiệm thu kỹ thuật offline với **MiniLM và Chroma thật, QA/mock judge**. Chưa xác nhận provider LLM online, Ragas, môi trường cài mới hoàn toàn hay hoàn tất thủ tục học phần.

## 2. Những lỗi đã sửa, vị trí và cách xử lý

| Vấn đề | File xử lý | Thay đổi và điều kiện nghiệm thu |
| --- | --- | --- |
| Quality Gate kiểm tra sau khi index | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | Cleaning trong RAM → GX/freshness → benchmark/index. Baseline và repaired không tạo index nếu gate lỗi. Corrupted cố ý được đánh giá trong index riêng để đo tác động; không thay index sạch. |
| Xóa index tốt trước khi embedding thành công | `src/retrieval/index.py` | Encode và kiểm tra vector trước; tạo collection tên riêng; kiểm tra add/count/query rồi mới publish manifest. Nếu lỗi chỉ dọn candidate mới, giữ collection/manifest tốt trước đó. Đóng client trước khi đóng dấu hash. |
| File viết dở khi tiến trình lỗi | `src/core/utils.py` | Ghi file tạm cùng thư mục, flush/fsync và atomic replace; JSON không cho NaN/Infinity. Đây là atomic ở từng file, không phải transaction chung cho mọi artifact. |
| Corruption không chạy lại khi output tồn tại | `src/pipelines/runs.py`, `src/core/config.py`, hai entrypoint trong `script/` | Run riêng, lock writer, source/input/config fingerprint. Run xong được xác minh rồi tái sử dụng; run thất bại giữ diagnostic và retry ở attempt mới. Không ghi đè output lịch sử. |
| DOI không tồn tại nhưng QA trả bài khác | `src/retrieval/identity.py`, `qa.py`, `llm.py`, `agent.py` | Nhận diện DOI/tiêu đề định danh; thiếu exact match thì abstain. Metadata rỗng cũng không suy diễn bằng bài khác. Ghi `answer_doc_ids`, `abstained`; mock agent và semantic tool có cùng ràng buộc. |
| F1 cao dù nguồn sai | `src/evaluation/metrics.py` | Bổ sung source hit, grounded F1, abstention và backend/judge fallback. Grounded F1 bằng 0 nếu nguồn sai, dù từ vựng trùng. Giữ định nghĩa Token F1 cũ và ghi rõ là token-set overlap. |
| Benchmark có thể thay đổi giữa các lượt | `src/evaluation/testset.py`, hai pipeline | Đóng băng 10 câu/4 loại, kiểm tra ID và nguồn/reference; benchmark không hợp lệ bị từ chối thay vì âm thầm sinh bộ mới. Corrupted/repaired dùng cùng bộ baseline. |
| Payload hoặc tuổi dữ liệu không hợp lệ | `src/ingestion/crossref.py`, `src/observability/quality.py` | Payload sai kiểu báo ValueError rõ ràng; age_days phải hữu hạn, nguyên, không âm. GX dùng context in-memory, không sinh Data Docs ngoài run. |
| Import nặng và giới hạn môi trường chạy | `src/retrieval/embeddings.py`, `src/pipelines/__init__.py`, `script/run_phase1.py`, `script/run_corruption_flow.py` | Lazy import, mặc định pool tính toán 1 luồng, HF offline, mock provider và Ragas tắt cho đường chạy nghiệm thu. |
| Thiếu manifest/checker/bàn giao nhất quán | `script/verify_run.py`, `src/observability/reporting.py`, `README.md`, `report/group_report.md` | Checker độc lập đọc SQLite readonly, đối chiếu lineage/inventory/metrics/report. Báo cáo ghi hash raw/testset và backend. README chỉ rõ run được chọn và cách chạy. |
| Chroma cần đóng hoàn toàn trước copy/hash | `pyproject.toml`, `requirements.txt`, `uv.lock` | Nâng lower bound lên `chromadb>=1.5.9` để dùng public client.close; môi trường nghiệm thu đã có phiên bản phù hợp. |

Test mới nằm tại `tests/test_regressions.py`. Hai file module mới là `src/pipelines/runs.py` và `src/retrieval/identity.py`; checker mới là `script/verify_run.py`.

## 3. Run chuẩn và đối chiếu lineage

Run được tạo lúc `2026-09-27T03:56:29.095282+00:00`. Baseline hoàn tất lúc `03:56:35.944339+00:00`, comparison hoàn tất lúc `03:57:18.665211+00:00`. Đây là timestamp trong manifest, không phải thời gian toàn bộ CLI tính cả import.

| Thành phần | Vị trí trong `data/runs/khoi_handover_20260927_01/` |
| --- | --- |
| Raw được sao chép nguyên byte | `raw/crossref_records.json`, `raw/crossref_response.json` |
| Benchmark đầu vào | `inputs/test_set.json` |
| Baseline và benchmark đã serialize | `baseline/attempt-001/` và `baseline/attempt-001/eval/test_set.json` |
| Corrupted + repaired, cùng benchmark | `comparison/attempt-001/` và `comparison/attempt-001/eval/test_set.json` |
| Baseline report | `baseline/attempt-001/reports/phase1_report.md` |
| Bảng ba trạng thái | `comparison/attempt-001/reports/corruption_report.md` |
| Danh mục và SHA-256 | `run_manifest.json` |

SHA-256 raw gốc và bản copy giống nhau:

```text
crossref_records.json  87b6413046082aa85518ebd6142aa5fccc88926dcbb65c83de60e9302e62446e
crossref_response.json d968be684bff7d7fc8245194e46544a3a3f477418437cce993bc17d4ecab5cc0
```

Benchmark đã serialize ở cả hai stage có SHA-256 `19d5ac3b18cab70db178c29a7bac72328f386c375e9df1abe12459fb3b4dd03f`. Hash này khác file benchmark đầu vào do chuẩn hóa newline khi ghi JSON, nhưng nội dung JSON được đối chiếu bằng nhau. Manifest lưu riêng hash đầu vào và artifact, không giả định chúng bằng nhau.

Đã kiểm tra raw → clean, tuổi bài theo ngày cố định của run, clean → embedding document/metadata, embedding → SQLite IDs/count/dimension, answers → aggregate metrics và metrics → bảng report. Baseline/repaired clean và metrics khớp hoàn toàn.

## 4. Kết quả thực tế

| Chỉ số | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Số dòng | 24 | 20 | 24 |
| Số câu benchmark | 10 | 10 | 10 |
| Retrieval Hit Rate | 1.0 | 0.8 | 1.0 |
| Mean Token F1 | 1.0 | 0.8 | 1.0 |
| Grounded Token F1 | 1.0 | 0.8 | 1.0 |
| Answer source hit rate | 1.0 | 0.8 | 1.0 |
| Abstention rate | 0% | 20% | 0% |
| Judge accuracy | 1.0 | 0.8 | 1.0 |
| Judge mean score | 5.0 | 4.2 | 5.0 |
| Heuristic judge count | 10 | 10 | 10 |
| GX expectations đạt | 7/7 | 3/7 | 7/7 |
| Quality Gate | Đạt | Không đạt | Đạt |
| Bài quá 180 ngày | 1/24 | 2/20 | 1/24 |
| Freshness SLA | Đạt | Đạt | Đạt |
| Challenge ngoài corpus đạt | 3/3 | 8/8 | 3/3 |

Corrupted còn 19 DOI phân biệt trong 20 dòng do có duplicate. Sáu loại corruption đều được ghi log. Freshness vẫn đạt vì tỷ lệ stale 10% chưa vượt ngưỡng 25%; cảnh báo chính ở run này là quality, không được diễn giải là freshness đã thất bại.

F1 corrupted cũ khoảng 0.974 trong artifact lịch sử không còn là bằng chứng được chọn. F1 mới 0.8 phản ánh việc từ chối hai câu có nguồn đã mất, thay vì trả thông tin của bài khác. Không sửa raw hoặc thay benchmark để tạo mức suy giảm này.

## 5. Kiểm thử, lỗi và bằng chứng

24 unittest bao gồm: atomic write; lỗi encode/add/publish không mất index cũ; relocation manifest; quality thất bại trước index; benchmark sai; lock; retry sau failure; input/source/config thay đổi; output root không an toàn; raw chỉ có response; DOI ngoài corpus; metadata rỗng; mock tool agent; wrong-source F1; freshness boundary/NaN/Infinity; malformed Crossref; và repaired gate không được phép index khi fail.

Các tình huống lỗi trong test được chủ động tiêm bằng fixture/double. Đây là kiểm thử đường thất bại, không phải lỗi còn tồn tại trong run chuẩn. MiniLM, Chroma, GX và mock tool agent cũng đã được chạy thực tế ở các bước nghiệm thu tương ứng. Toàn bộ test suite kết thúc exit code 0; hai CLI baseline/comparison kết thúc exit code 0.

Bằng chứng được tập hợp ở [handover/evidence](../handover/evidence/):

- `artifact_verification.json`: 131 kiểm tra cùng metrics và count từng collection.
- `preservation.json`: 60 file dữ liệu cũ không đổi và hash raw.
- `lineage_verification.json`: raw/clean/benchmark khớp.
- `reuse_verification.json` và log hai CLI: chạy lại không ghi artifact.
- `relocation_verification.json`: 99 kiểm tra và 30 truy vấn tương đương.
- `regression_tests.log`: log chạy lại bộ 24 test trước khi đóng gói.

`git diff --check` không phát hiện lỗi whitespace. Git cảnh báo LF sẽ chuyển sang CRLF khi Git xử lý một số file; đây không phải runtime failure. Vì manifest dùng hash byte, checkout/source đổi newline có thể làm kiểm tra source không khớp: dùng gói ZIP giữ byte hoặc tạo run ID mới cho source checkout đó.

## 6. Bàn giao Chroma và chạy lại

Gói bàn giao: [handover/khoi_handover_20260927_01.zip](../handover/khoi_handover_20260927_01.zip). Gói gồm source, dependency metadata, test, hướng dẫn, raw/benchmark gốc, toàn bộ run chuẩn và evidence. Không chứa `.env`, `.git`, virtualenv, model cache hay artifact của run khác. Model MiniLM cần có trong cache hoặc tải theo README trên máy mới.

Baseline có `chroma.sqlite3` và segment `4e04524d-fee3-46ed-ab4c-96683e76ee71`. Comparison có `chroma.sqlite3` và hai segment `0391b2bf-3d7a-4170-97a2-7e8b3779e506`, `0f77f12a-82d9-4765-9570-61eb3a65450d`. Mỗi segment gồm `header.bin`, `length.bin`, `link_lists.bin`, `data_level0.bin`. Checker đối chiếu segment DB tham chiếu; không chỉ bàn giao riêng SQLite.

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
.venv/Scripts/python.exe -B script/verify_run.py data/runs/khoi_handover_20260927_01 --project-dir .
.venv/Scripts/python.exe -B script/run_phase1.py --run-id khoi_handover_20260927_01
.venv/Scripts/python.exe -B script/run_corruption_flow.py --run-id khoi_handover_20260927_01
```

Hai lệnh cuối tái sử dụng run đã hoàn tất sau xác minh. Để thực sự tính lại toàn pipeline, đổi cả hai sang cùng run ID mới. Không sửa manifest hoặc artifact của run chuẩn. Kết quả kiểm tra ZIP và SHA-256 của ZIP nằm trong `handover/package_verification.json` bên ngoài archive để tránh vòng tham chiếu hash.

## 7. Đối chiếu checkpoint/rubric và phần còn lại

Đối chiếu [CHECKPOINTS.md](CHECKPOINTS.md) và [RUBRIC.md](RUBRIC.md) — file RUBRIC thực tế nằm trong `docs/`, không ở root:

| Phạm vi | Trạng thái và giới hạn |
| --- | --- |
| CP1–CP3 | Có bằng chứng local snapshot, clean/model/index 24 tài liệu, 10 câu/4 loại và baseline end-to-end. Artifact mới nằm trong run riêng; mapping đường dẫn nêu ở trên. |
| CP4 | Có đủ sáu corruption, quality alert, metric suy giảm và log. |
| CP5 | Repair từ raw, dữ liệu/metric phục hồi, báo cáo ba trạng thái; chạy lặp giữ nguyên artifact và relocation đã kiểm chứng. |
| CP6 | Đã chuẩn bị artifact và hướng dẫn demo. Chưa thể xác nhận live demo/Q&A, contributors trên main, báo cáo cá nhân hoặc LMS. |
| Rubric môi trường/ingestion/cleaning/index/eval/observability/corruption | Có bằng chứng kỹ thuật local tương ứng; chưa kiểm chứng cài sạch trên máy giám khảo. Không tự kết luận điểm tối đa. |
| Multi-provider QA | Mock được kiểm chứng; không suy rộng sang Google/OpenAI/Anthropic chưa chạy. |
| Bonus auto-repair | Có quality alert kích hoạt repair trong corruption flow; không phải daemon giám sát production. Giảng viên quyết định điểm. |
| Bonus dashboard/test coverage | Không bổ sung dashboard trong lượt này; unittest không chứng minh yêu cầu Pytest CI/coverage >80%. Không tự nhận bonus. |

Giới hạn vận hành: giữ collection cũ để an toàn, chưa có tự động garbage collection; retry chạy lại toàn stage; tiến trình bị kill có thể để lại lock cần kiểm tra hoặc chọn run mới. Benchmark có DOI và QA lấy metadata nên chưa đánh giá đầy đủ semantic retrieval hoặc sinh câu trả lời mở. Không có chứng nhận chất lượng LLM online từ điểm mock judge.

Nhóm cần tự xác nhận danh tính/đóng góp trong `docs/TEAM.md`, hoàn thiện báo cáo cá nhân, duyệt thay đổi, trình bày demo và nộp LMS. Không có commit/push/merge trong lượt này theo yêu cầu. Dữ liệu/DB cũ vốn đã modified trước lượt sửa vẫn được giữ nguyên; không được coi những thay đổi có sẵn đó là thay đổi mới của lượt này.
