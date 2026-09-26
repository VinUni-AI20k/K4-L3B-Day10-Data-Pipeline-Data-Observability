# Báo Cáo Pha 1 — Baseline Data Pipeline & Observability
**Dự án:** K4-L3B-Day10 — Data Pipeline & Data Observability for RAG  
**Nhóm:** Team VN | **Thời gian sinh báo cáo:** 2026-09-26 04:23:10 UTC  
**Trạng thái kiểm định toàn diện:** **PASS**

---

## 1. Tóm tắt kết quả Baseline (Executive Summary)

Pha 1 đã thiết lập thành công chu trình dữ liệu sạch khép kín cho hệ thống RAG Agent:
- **Nguồn dữ liệu:** Crossref REST API (24 bài báo khoa học).
- **Chỉ số Retrieval Hit Rate:** **100.00%** trên bộ Benchmark 10 câu hỏi chuẩn hóa.
- **Chỉ số Mean Token F1:** **1.0000**, phản ánh độ chính xác trích xuất nội dung từ tập văn bản sạch.
- **Judge Accuracy:** **100.00%** (Điểm trung bình: 5.00/5.0).
- **Great Expectations 1.x Quality Gate:** **PASS** (vượt qua 100% các kỳ vọng về schema, nullability, tính duy nhất và độ dài chuỗi).
- **Freshness SLA:** **FRESH** (Tỷ lệ bài báo quá hạn 180 ngày: 4.17%, dưới ngưỡng cảnh báo 25%).

---

## 2. Thông tin Ingestion & Nguồn dữ liệu

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Nguồn API** | `Crossref REST API` |
| **Truy vấn (Query)** | `agentic retrieval augmented generation large language model` |
| **Bộ lọc (Filter)** | `from-pub-date:2026-03-30,has-abstract:true` |
| **Số bản ghi thô** | `24` bản ghi |
| **Thời điểm thu thập** | `2026-09-26T04:23:02.781139+00:00` |
| **Cơ chế Data Lineage** | Lưu trữ snapshot gốc tại `data/raw/crossref_response.json` và `data/raw/crossref_records.json` |

---

## 3. Tiền xử lý & Chuẩn hóa Dữ liệu (Data Cleaning & Modeling)

- Khử trùng lặp theo `paper_id` tuyệt đối.
- Loại bỏ các thẻ JATS XML (`<jats:p>`, `<jats:title>`) và chuẩn hóa Unicode whitespace.
- Tính toán chính xác độ tuổi bài báo `age_days = (run_date - published).days` theo chuẩn UTC.
- Cấu trúc hóa trường `text_for_embedding` gồm 5 phần chuẩn:
  ```text
  Title: <title>
  Authors: <authors_joined>
  Published: <published>
  Categories: <categories_joined>
  Summary: <summary>
  ```
- Dữ liệu sạch được lưu đồng thời tại `data/clean/papers_clean.csv` và `data/clean/papers_clean.json`.

---

## 4. Vector Store & Indexing (ChromaDB)

- **Vector Database:** ChromaDB (Persistent storage tại `data/chroma`).
- **Collection Name:** `papers-baseline`.
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, cosine distance space).
- **Số tài liệu đã nhúng:** 24 documents có metadata đầy đủ.

---

## 5. Kết quả Đánh giá RAG Baseline

| Chỉ số | Điểm số Baseline | Ý nghĩa nghiệp vụ |
| :--- | :---: | :--- |
| **Retrieval Hit Rate** | **1.0000** (100.0%) | Tỷ lệ truy xuất trúng tài liệu chứa câu trả lời trong top-4 |
| **Mean Token F1** | **1.0000** | Độ trùng khớp n-gram từ vựng giữa câu trả lời và ground truth |
| **Judge Accuracy** | **1.0000** (100.0%) | Tỷ lệ câu trả lời được đánh giá đạt chuẩn nội dung |
| **Mean Judge Score** | **5.00 / 5.0** | Điểm số chất lượng câu trả lời trung bình |
| **Số mẫu benchmark** | **10** | 10 câu hỏi bao phủ 4 nhóm: summary, authors, date, categories |

---

## 6. Data Observability: Great Expectations 1.x & Freshness SLA

### Great Expectations 1.x Validation Suite (Ephemeral Context)

| Expectation Type | Cột kiểm định | Trạng thái |
| :--- | :--- | :---: |
| `ExpectTableRowCountToBeBetween` | `table-level` | **PASSED** |
| `ExpectColumnValuesToNotBeNull` | `paper_id` | **PASSED** |
| `ExpectColumnValuesToNotBeNull` | `title` | **PASSED** |
| `ExpectColumnValuesToNotBeNull` | `text_for_embedding` | **PASSED** |
| `ExpectColumnValuesToBeUnique` | `paper_id` | **PASSED** |
| `ExpectColumnValueLengthsToBeBetween` | `title` | **PASSED** |
| `ExpectColumnValueLengthsToBeBetween` | `summary` | **PASSED** |

### Giám sát Freshness SLA

| Thuộc tính Freshness | Giá trị |
| :--- | :--- |
| **Ngày xuất bản mới nhất** | `2026-07-22` |
| **Ngày xuất bản cũ nhất** | `2026-03-28` |
| **Ngưỡng SLA (ngày)** | `180 ngày` |
| **Số bài báo quá hạn (>180 ngày)** | `1 / 24` |
| **Tỷ lệ quá hạn (Stale Ratio)** | `4.17%` (Ngưỡng cho phép: <= 25%) |
| **Kết luận Freshness** | **FRESH** |

---

## 7. Kết luận Pha 1

Hệ thống Baseline đã đạt chuẩn 100% về cả chất lượng dữ liệu đầu vào và năng lực truy xuất thông tin của RAG Agent. Dữ liệu đã sẵn sàng để chuyển sang Pha 2 nhằm thực hiện tiêm lỗi mô phỏng (Data Corruption Suite) và đánh giá khả năng tự phục hồi.
