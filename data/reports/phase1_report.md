# Báo cáo Phase 1 — Baseline

## Dữ liệu đầu vào

| Mục | Giá trị |
| --- | --- |
| Nguồn | Crossref REST API |
| Chế độ | Raw records snapshot |
| Raw records | 24 |
| Clean records | 24 |
| Papers with categories | 0 |
| Câu hỏi benchmark | 10 |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Embedding runtime | ONNXMiniLM_L6_V2 |
| Chroma collection | papers-baseline |

## Chỉ số đánh giá RAG

| Chỉ số | Giá trị |
| --- | ---: |
| Số câu hỏi | 10 |
| Retrieval Hit Rate | 100.00% |
| Mean Token F1 | 0.8000 |
| Judge accuracy | 80.00% |
| Mean judge score | 4.20/5 |
| Số câu dùng heuristic judge | 10 |

| Loại câu hỏi | Số câu | Hit Rate | Token F1 |
| --- | ---: | ---: | ---: |
| summary | 3 | 100.00% | 1.0000 |
| authors | 3 | 100.00% | 1.0000 |
| date | 2 | 100.00% | 1.0000 |
| categories | 2 | 100.00% | 0.0000 |

## Kiểm định chất lượng GX 1.x

**Kết quả gate:** Đạt (24 bản ghi).

| Expectation | Cột | Kết quả |
| --- | --- | --- |
| ExpectTableRowCountToBeBetween | — | Đạt |
| ExpectColumnValuesToNotBeNull | paper_id | Đạt |
| ExpectColumnValuesToNotBeNull | title | Đạt |
| ExpectColumnValuesToNotBeNull | text_for_embedding | Đạt |
| ExpectColumnValuesToBeUnique | paper_id | Đạt |
| ExpectColumnValueLengthsToBeBetween | summary | Đạt |

## Độ tươi dữ liệu

| Chỉ số | Giá trị |
| --- | ---: |
| Ngưỡng tuổi | 180 ngày |
| Bài báo quá hạn | 0/24 |
| Tỷ lệ quá hạn | 0.00% |
| Ngưỡng cảnh báo | 25% |
| Freshness SLA | Đạt |
| Mới nhất | 2026-09-15 |
| Cũ nhất | 2026-04-01 |

Judge dùng heuristic khi nhà cung cấp LLM không khả dụng; Retrieval Hit Rate và Token F1 vẫn được tính từ câu trả lời truy xuất.

Crossref không cung cấp subject cho các bài trong snapshot này. 2 câu hỏi categories kiểm tra khả năng xử lý metadata thiếu; Token F1 của nhóm là 0.0000.

Các câu hỏi benchmark chứa đúng tiêu đề bài báo; bước QA ưu tiên tra cứu tiêu đề chính xác trước khi tính Hit Rate.
