# Báo cáo cá nhân — 02489_HaiHoang

- **Thành viên:** Hải Hoàng (02489)
- **Nhóm/lớp:** Trike — K4-L3B-DAY10
- **Phạm vi:** Làm sạch dữ liệu và tích hợp baseline pipeline Phase 1
- **Ngày ghi nhận:** 2026-09-26

## Công việc phụ trách

1. Hoàn thiện `src/ingestion/cleaning.py`, hàm `build_clean_dataframe(records, run_date)`.
2. Hoàn thiện `src/pipelines/phase1.py`, hàm `run_phase1_pipeline(settings)`, và chạy tuyến Phase 1 qua `script/run_phase1.py`.

## Cách thực hiện và quyết định kỹ thuật

- Chuyển từng `PaperRecord` thành một dòng DataFrame; giải mã HTML, bỏ thẻ markup còn sót, chuẩn hóa khoảng trắng, DOI, tác giả, lĩnh vực và ngày ISO. Bỏ bản ghi thiếu DOI, tiêu đề, tóm tắt hoặc ngày xuất bản hợp lệ.
- Tính `age_days = (run_date.date() - published).days`, `summary_chars`, `authors_joined`, `categories_joined`; ghép năm dòng Title, Authors, Published, Categories, Summary thành `text_for_embedding`.
- Khử trùng lặp theo `paper_id`, giữ bản ghi đầu, rồi sắp xếp theo ngày xuất bản và DOI để đầu ra ổn định.
- Pipeline ưu tiên records snapshot đã lưu khi không yêu cầu refresh. Khi chạy mới, hàm ingest tự xử lý API/snapshot. Pipeline ghi CSV/JSON sạch, chạy quality gate và freshness trước khi xây Chroma index, tạo test set, đánh giá RAG, rồi sinh báo cáo.
- Chặn bước index/đánh giá nếu quality gate thất bại; nhờ vậy dữ liệu không đạt chuẩn không đi vào baseline.

## Đầu ra và bằng chứng

| Đầu ra | Kết quả ghi nhận |
| --- | --- |
| [Dữ liệu sạch CSV](../data/clean/papers_clean.csv) và [JSON](../data/clean/papers_clean.json) | 24 bài báo sạch từ 24 raw records |
| [Báo cáo Phase 1](../data/reports/phase1_report.md) | Có bảng nguồn, kết quả đánh giá, quality gate và freshness |
| [Baseline metrics](../data/results/baseline_metrics.json) | Hit Rate 1,00; mean Token F1 0,80; judge accuracy 0,80 |
| [Quality report](../data/quality/baseline_quality_report.json) | `success=true`, 24 dòng |

Báo cáo chạy toàn tuyến ghi Chroma collection `papers-baseline`, embedding model `sentence-transformers/all-MiniLM-L6-v2` và runtime `SentenceTransformer`. Chỉ số Hit Rate được đo trên 10 câu hỏi chứa đúng tiêu đề bài báo; vì vậy chưa đại diện cho câu hỏi diễn đạt tự do.

## Kiểm tra và giới hạn

Lệnh kiểm tra cleaning từ snapshot được thực hiện ở bước trước và cho kết quả 24 dòng. Pipeline Phase 1 đã chạy và sinh các artifact nêu trên. Snapshot Crossref hiện có 0/24 bài có `subject`, nên hai câu hỏi `categories` đạt Token F1 bằng 0 dù tổng Hit Rate là 100%. Đây là giới hạn của nguồn dữ liệu và benchmark hiện tại, chưa phải bằng chứng cho chất lượng RAG trên truy vấn thực tế.

## Liên kết với toàn tuyến và hướng cải thiện

`crossref_records.json` là input của cleaning; DataFrame sạch cung cấp `text_for_embedding` cho index, các cột nội dung cho test set, và `age_days` cho freshness. DOI được giữ xuyên suốt để so khớp document ID trong retrieval với `ground_truth_doc_ids`. Khi có pha corruption và repair, cần đánh giá cả ba trạng thái trên cùng test set rồi đối chiếu metrics và quality report; hiện chưa có hai bộ kết quả sau baseline.

Quyết định đặt quality gate trước index làm lỗi dữ liệu lộ ra sớm và để lại báo cáo kiểm tra. Bước cải thiện cụ thể là bổ sung nguồn bài có `subject`, chạy lại pipeline và xem Token F1 của nhóm `categories` có tăng hay không; đồng thời thử câu hỏi không chứa nguyên tiêu đề để đo retrieval sát cách dùng thực tế hơn.

## Bàn giao

Các file mã nguồn và artifact ở trên là phần đóng góp được ghi nhận cho Hải Hoàng. Thành viên cần rà soát cách diễn đạt và xác nhận nội dung báo cáo cá nhân trước khi nộp.
