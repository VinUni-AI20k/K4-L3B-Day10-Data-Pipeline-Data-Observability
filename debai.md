Bước 0: Khởi Tạo Repo Nhóm & Thiết Lập Git Teamwork
Về bài lab này
Chào mừng bạn đến với tài liệu hướng dẫn thực hành của bài lab Day 10 - Data Pipeline & Data Observability (Lớp L3B).
Hướng Dẫn Kỹ Thuật Chi Tiết (Technical Guide) — Day 10
Chào mừng bạn đến với tài liệu hướng dẫn thực hành của bài lab Day 10 - Data Pipeline & Data Observability (Lớp L3B).

💡 Lời khuyên trước khi bắt đầu: Bài lab này sẽ dẫn dắt bạn qua toàn bộ quy trình xây dựng đường ống dữ liệu (Data Pipeline) chuẩn mực cho AI: từ khâu gom dữ liệu thô, làm sạch, thiết lập chốt kiểm soát chất lượng (Data Observability Gate) với Great Expectations 1.x, cho tới việc chủ động tiêm lỗi dữ liệu (Data Corruption) để quan sát sự suy giảm hiệu năng của mô hình AI và kích hoạt cơ chế phục hồi tự động (Idempotent Recovery). Hãy đi từng bước một cách cẩn thận, đọc kỹ hướng dẫn và đối chiếu đúng Tín hiệu hoàn thành (Pass Signal) ở mỗi bước trước khi chuyển sang bước tiếp theo.
🎯 Nhiệm vụ thực hiện: Trưởng nhóm thực hiện fork và đổi tên repo theo chuẩn quy ước chung, mời toàn bộ thành viên vào danh sách Collaborators. Tất cả các thành viên clone repo về máy local và bắt buộc cấu hình git config user.email trùng khớp với tài khoản GitHub cá nhân để được hệ thống tính điểm Contributor.
Trước khi viết bất kỳ dòng mã nào, nhóm cần chuẩn bị không gian làm việc chung trên GitHub theo đúng quy trình phối hợp nhóm:

0.1. Trưởng nhóm: Fork & Đổi tên Repo
1. Truy cập repo mẫu chính thức của ban tổ chức: 👉 https://github.com/VinUni-AI20k/K4-L3B-Day10-Data-Pipeline-Data-Observability
2. Bấm nút Fork (ở góc trên bên phải) về tài khoản GitHub cá nhân của trưởng nhóm.
3. Đổi tên repo nhóm (Vào Settings -> mục Repository name -> nhập tên mới -> bấm Rename):
Quy tắc đặt tên: K4-L3B-DAY10-<TenNhom>-DataPipelineDataObservability
Ví dụ chuẩn: K4-L3B-DAY10-AlphaTeam-DataPipelineDataObservability
⚠️ Lưu ý kỷ luật: Tuyệt đối KHÔNG tự ý thêm tiền tố GroupXX hoặc TeamXX vào tên repo.
0.2. Mời thành viên vào Repo (Collaborators)
1. Trưởng nhóm vào repo của mình trên GitHub -> Chọn tab Settings -> Chọn mục Collaborators ở thanh bên trái.
2. Bấm nút Add people, tìm kiếm theo GitHub username của từng thành viên trong nhóm và gửi lời mời.
3. Các thành viên kiểm tra Email hoặc truy cập trực tiếp đường link repo của trưởng nhóm để bấm Accept invitation.
0.3. Clone Repo về máy cá nhân
Tất cả các thành viên (bao gồm cả trưởng nhóm) mở terminal trên máy tính của mình và thực hiện clone repo nhóm (thay thế <GitHub_TruongNhom> và <TenNhom> bằng thông tin thật của nhóm bạn):

git clone https://github.com/<GitHub_TruongNhom>/K4-L3B-DAY10-<TenNhom>-DataPipelineDataObservability.git
cd K4-L3B-DAY10-<TenNhom>-DataPipelineDataObservability
Chép
0.4. ⚠️ BẮT BUỘC: Cấu hình Git để được ghi nhận Contributor
Mỗi thành viên trước khi gõ bất kỳ lệnh git commit nào BẮT BUỘC phải cài đặt đúng tên và email trùng khớp với tài khoản GitHub của mình:

git config --global user.name "Họ và Tên của bạn"
git config --global user.email "email_dang_ky_github@domain.com"
Chép
⚠️ Cảnh báo mất điểm chuyên cần: Giảng viên và trợ giảng sẽ chấm điểm đóng góp cá nhân (Individual Contribution) thông qua thống kê commit tại tab Insights -> Contributors trên GitHub. Nếu bạn không cấu hình email hoặc dùng email khác với tài khoản GitHub, commit của bạn sẽ bị gán là "Anonymous" (vô danh) và GitHub sẽ không tính bạn là Contributor. Điều này đồng nghĩa với việc bạn bị mất toàn bộ điểm thành phần cá nhân theo quy định tại docs/RUBRIC.md. Mỗi thành viên trong nhóm phải có ít nhất 1–2 commit trực tiếp từ tài khoản của mình thể hiện rõ phần công việc được giao.
Đoạn chọn quá dài để đánh dấu.




Bước 1: Khởi Tạo Môi Trường & Cấu Hình
🎯 Nhiệm vụ thực hiện: Kích hoạt môi trường ảo .venv, cài đặt gói dự án ở chế độ phát triển (python -m pip install -e . hoặc uv sync), sao chép .env.example thành .env và dán GOOGLE_API_KEY cá nhân.
1. Mở terminal tại thư mục gốc của project vừa clone về.
1. Kiểm tra phiên bản Python (Yêu cầu Python 3.11, 3.12 hoặc 3.13):
python --version
Chép
1. Kích hoạt môi trường ảo:
Windows PowerShell:
.\.venv\Scripts\Activate.ps1
Chép
(💡 Nếu PowerShell báo lỗi script bị chặn do ExecutionPolicy, chạy lệnh: Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned rồi kích hoạt lại).

Linux / macOS:
source .venv/bin/activate
Chép
1. Cài đặt toàn bộ thư viện & package dự án:
python -m pip install -e .
Chép
(💡 Nếu máy bạn có sẵn công cụ uv, bạn có thể gõ uv sync để cài đặt siêu tốc).

1. Tạo file cấu hình .env từ file mẫu .env.example:
Windows PowerShell:
Copy-Item .env.example .env
Chép
Linux / macOS:
cp .env.example .env
Chép
Mở file .env, tìm dòng GOOGLE_API_KEY= và dán mã API Key của bạn ngay sau dấu =. Không để khoảng trắng thừa, không thêm dấu nháy kép.

1. Kiểm tra kết nối 3 thư viện cốt lõi (ChromaDB, Great Expectations, Sentence-Transformers):
python -c "import chromadb, great_expectations, sentence_transformers; print('Environment Ready!')"
Chép
Tín hiệu hoàn thành: Console in ra dòng chữ: Environment Ready!.
💡 Mẹo gỡ rối (Troubleshooting): Nếu gặp lỗi ModuleNotFoundError, kiểm tra xem terminal đã trỏ đúng vào Python của .venv chưa bằng lệnh where python (Windows) hoặc which python (macOS/Linux). Nếu đường dẫn không chứa .venv, hãy kích hoạt lại môi trường ảo ở mục 3.
Đoạn chọn quá dài để đánh dấu.


Bước 2: Thu Thập Dữ Liệu & Cất Giữ Bản Gốc (`src/ingestion/crossref.py`)
Trong bước này, chúng ta thu thập metadata bài báo học thuật từ Crossref REST API và cất giữ bản sao nguyên gốc (Raw Preservation).

Mục tiêu:
Thu thập metadata từ Crossref REST API công khai.
Chuẩn hóa các trường thông tin: paper_id (DOI), title, summary (loại bỏ các thẻ HTML/XML rác như <jats:p>), authors, categories, published.
Lưu lại 2 file dữ liệu thô (Raw Artifacts) phục vụ Data Lineage:
data/raw/crossref_response.json: Toàn bộ JSON gốc từ API (nguyên bản, không chỉnh sửa).
data/raw/crossref_records.json: Danh sách đối tượng PaperRecord sau khi bóc tách.
🔍 Tại sao phải cất giữ bản thô (Raw Preservation)? Dữ liệu gốc cào về cần được giữ nguyên vẹn để làm điểm tựa phục hồi (Lineage Anchor). Khi các bước biến đổi dữ liệu phía sau xảy ra lỗi, hệ thống có thể chạy lại từ bản thô mà không cần gọi lại API ngoài, tránh nguy cơ bị giới hạn truy cập (Rate Limit).
Cơ chế Cứu hộ Offline (Fallback):
Nếu mạng chập chờn hoặc API Crossref trả về lỗi 429 Too Many Requests, pipeline sẽ tự động chuyển sang đọc file snapshot mẫu có sẵn tại data/raw/crossref_response.json mà không làm gián đoạn bài lab.

🎯 Nhiệm vụ của bạn: Mở file src/ingestion/crossref.py, đọc docstring và hoàn thiện logic 2 hàm: 1. parse_crossref_payload(payload): Bóc tách cấu trúc payload JSON từ API Crossref thành danh sách các đối tượng PaperRecord. 2. fetch_source_records(settings): Gọi API Crossref (hoặc kích hoạt fallback đọc snapshot mẫu), lưu JSON gốc vào data/raw/crossref_response.json và lưu danh sách records vào data/raw/crossref_records.json.
Kiểm tra bước 2:

python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
Chép
Tín hiệu hoàn thành: Console in ra Tín hiệu hoàn thành: Đã tải 24 bài báo.


Bước 3: Làm Sạch Dữ Liệu & Chuẩn Bị Văn Bản Tạo Vector (`src/ingestion/cleaning.py`)
Dữ liệu thô tải về cần được chuẩn hóa khoảng trắng, định dạng ngày tháng và định dạng văn bản phục vụ Embedding.

Mục tiêu:
Loại bỏ khoảng trắng thừa, chuẩn hóa định dạng văn bản.
Tính toán tuổi đời dữ liệu: age_days = (run_date - published).days.
Ghép nối các trường thành một đoạn ngữ cảnh hoàn chỉnh text_for_embedding:
Title: <Tiêu đề bài báo>
Authors: <Danh sách tác giả>
Published: <Ngày xuất bản>
Categories: <Lĩnh vực chuyên môn>
Summary: <Tóm tắt nội dung>
Chép
Khử trùng lặp bản ghi theo khóa duy nhất paper_id.
🎯 Nhiệm vụ của bạn: Mở file src/ingestion/cleaning.py, hoàn thiện hàm build_clean_dataframe(raw_records, run_date) để biến đổi danh sách PaperRecord thành một pandas.DataFrame sạch, tính toán cột age_days, tạo cột tổng hợp text_for_embedding và loại bỏ hoàn toàn các dòng trùng lặp paper_id.
Kiểm tra bước 3:

python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
Chép
Tín hiệu hoàn thành: Console in ra Tín hiệu hoàn thành: Clean thành công 24 dòng.


Bước 4: Thiết Lập Chốt Kiểm Soát Dữ Liệu (Observability Gate) với Great Expectations 1.x (`src/observability/quality.py`)
Trước khi đưa dữ liệu vào Vector Database, dữ liệu phải vượt qua chốt kiểm định chất lượng nghiêm ngặt.

Chuẩn Great Expectations 1.x:
Sử dụng chuẩn Ephemeral Context hiện đại trên GX 1.x:

context = gx.get_context(mode="ephemeral")
data_source = context.data_sources.add_pandas(name="papers_source")
data_asset = data_source.add_dataframe_asset(name="papers_asset")
batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
batch = batch_def.get_batch(batch_parameters={"dataframe": df})
Chép
4 Hàng Rào Kiểm Định (Expectations) Bắt Buộc:
1. ExpectTableRowCountToBeBetween: Số lượng bản ghi nằm trong ngưỡng 5 đến 5000 dòng.
2. ExpectColumnValuesToNotBeNull: Các cột quan trọng paper_id, title, text_for_embedding không được rỗng (null).
3. ExpectColumnValuesToBeUnique: Mỗi bài báo paper_id là duy nhất, không trùng lặp.
4. ExpectColumnValueLengthsToBeBetween: Trường summary có độ dài tối thiểu 30 ký tự.
Giám Sát Độ Tươi Mới (Freshness Monitoring):
Đo lường tỉ lệ bài báo cũ (age_days > 180 ngày). Nếu tỉ lệ bài báo cũ vượt quá 25%, hệ thống lập tức gắn cờ cảnh báo is_fresh = False.

🎯 Nhiệm vụ của bạn: Mở file src/observability/quality.py, hoàn thiện hàm run_data_quality_checks(df, settings, stage) sử dụng Great Expectations 1.x Ephemeral Context để thiết lập và kiểm định 4 Expectations bắt buộc trên, kết hợp gọi hàm evaluate_freshness_sla() để kiểm tra độ tươi mới của dữ liệu và trả về dict kết quả chứa {"success": bool, ...}.
Kiểm tra bước 4:

python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print('Tín hiệu hoàn thành: Quality check status =', res['success'])"
Chép
Tín hiệu hoàn thành: Console in ra Tín hiệu hoàn thành: Quality check status = True.


Bước 5: Tạo Bộ Đề Đánh Giá Chuẩn (Benchmark Test Set) (`src/evaluation/testset.py`)
Để đánh giá chất lượng câu trả lời của AI, chúng ta xây dựng bộ dữ liệu kiểm thử (Ground Truth) gồm 10 câu hỏi thuộc 4 dạng bài toán:

1. summary: Hỏi tóm tắt nội dung chính của bài báo.
2. authors: Hỏi về tác giả công trình nghiên cứu.
3. date: Hỏi thời điểm xuất bản.
4. categories: Hỏi về lĩnh vực chuyên môn.
Mỗi câu hỏi trong test_set.json có định dạng:

{
  "id": "eval_001",
  "question_type": "summary",
  "question": "What is the summary of the paper '<Title>'?",
  "ground_truth": "<Nội dung câu đầu tóm tắt chuẩn>",
  "ground_truth_doc_ids": ["<DOI bài báo>"]
}
Chép
🎯 Nhiệm vụ của bạn: Mở file src/evaluation/testset.py, hoàn thiện hàm build_test_set(df, output_path) để tự động trích xuất từ DataFrame dữ liệu sạch 10 câu hỏi Ground Truth phân bổ đều qua 4 dạng bài toán trên và lưu thành file data/eval/test_set.json.
Kiểm tra bước 5:

python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
Chép
Tín hiệu hoàn thành: Console in ra Tín hiệu hoàn thành: Sinh được 10 câu hỏi test.



Bước 6: Chạy Toàn Tuyến Dữ Liệu Sạch (Baseline Pipeline) (`script/run_phase1.py`)
🎯 Nhiệm vụ của bạn: Mở file src/pipelines/phase1.py, hoàn thiện hàm run_phase1_pipeline(settings) để xâu chuỗi 6 bước pipeline hoàn chỉnh: Ingest ➔ Clean ➔ Index ChromaDB ➔ Sinh Testset ➔ Đánh giá Baseline RAG Hit Rate & Token F1 ➔ Great Expectations Quality Gate và xuất báo cáo data/reports/phase1_report.md. Sau đó, thực thi script chạy toàn tuyến Phase 1:
python script/run_phase1.py
Chép
Tín hiệu hoàn thành: - File data/clean/papers_clean.csv xuất hiện đầy đủ các dòng sạch. - File data/results/baseline_metrics.json ghi nhận các chỉ số ban đầu (Hit Rate và Token F1). - File data/reports/phase1_report.md được sinh ra với bảng số liệu chi tiết.

Bước 7: Tiêm Lỗi Dữ Liệu Thực Nghiệm (Data Corruption Suite)
Tại src/ingestion/corruption.py, chúng ta giả lập 6 dạng sự cố dữ liệu thực tế:

1. Drop latest records: Bỏ rơi 20% các bài báo mới nhất.
2. Blank summary: Xóa trắng phần tóm tắt ở một số dòng.
3. Inject noise: Chèn các chuỗi ký tự rác vào tóm tắt.
4. Truncate title: Cắt ngắn tiêu đề xuống dưới 8 ký tự.
5. Stale date: Lùi ngày xuất bản về 365 ngày trước.
6. Duplicate rows: Nhân đôi các dòng để tạo trùng lặp.
🎯 Nhiệm vụ của bạn: Mở file src/ingestion/corruption.py, hoàn thiện hàm corrupt_clean_dataframe(clean_df, log_path) để tiêm 6 dạng lỗi trên vào dữ liệu sạch và ghi lại nhật ký toàn bộ các dòng bị biến đổi vào data/results/corruption_log.json.
Kiểm tra bước 7:

python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Tín hiệu hoàn thành: Corrupted {len(c)} dòng')"
Chép
Tín hiệu hoàn thành: Nhật ký lỗi data/results/corruption_log.json được ghi lại chi tiết.

Bước 8: Đo Lường Suy Giảm, Phục Hồi Dữ Liệu & Đối Chiếu 3 Trạng Thái
🎯 Nhiệm vụ của bạn: Mở file src/pipelines/corruption_flow.py, hoàn thiện hàm run_corruption_flow_pipeline(settings) để: 1. Nạp dữ liệu bẩn vào ChromaDB và đo lường sự suy giảm hiệu năng của AI (quan sát hiện tượng Silent Failure). 2. Kích hoạt hàm phục hồi an toàn repair_from_raw_snapshot() từ snapshot thô ban đầu để ghi đè dữ liệu hỏng. 3. Tái đánh giá hệ thống và kết xuất bảng so sánh 3 trạng thái tại data/reports/corruption_report.md. Sau đó, thực thi script chạy toàn tuyến Phase 2:
python script/run_corruption_flow.py
Chép
Tín hiệu hoàn thành: - Console in ra bảng so sánh hiệu năng 3 cột rõ ràng (Baseline vs Corrupted vs Repaired). - Báo cáo data/reports/corruption_report.md được tạo thành công, thể hiện rõ mức độ phục hồi hiệu năng của hệ thống.