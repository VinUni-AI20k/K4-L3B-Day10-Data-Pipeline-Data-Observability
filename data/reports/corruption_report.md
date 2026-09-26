# Data Observability & Corruption Recovery Report (3-State Comparison)

> **Objective:** Demonstrate detection of Silent Failure via Data Quality Gates (Great Expectations 1.x) and proof of Idempotent Self-Healing / Repair.

## 📊 Bảng Đối Chiếu 3 Trạng Thái (Baseline vs Corrupted vs Repaired)

| Chỉ số / Status | 1️⃣ Baseline (Dữ liệu sạch) | 2️⃣ Corrupted (Tiêm 6 lỗi bẩn) | 3️⃣ Repaired (Sau phục hồi) |
| :--- | :---: | :---: | :---: |
| **Retrieval Hit Rate** | **100.00%** | **50.00%** | **100.00%** |
| **Mean Token F1** | **0.5000** | **0.1800** | **0.5000** |
| **LLM Judge Accuracy** | **50.00%** | **20.00%** | **50.00%** |
| **GX Data Quality Gate** | **PASSED** | **FAILED** | **PASSED** |
| **Freshness SLA Status** | **FRESH** | **FRESH** | **FRESH** |

---

## 🔍 Phân Tích Chi Tiết

1. **Baseline State:** Dữ liệu sạch thu thập từ Crossref API đạt chất lượng tối ưu, Quality Gate báo `PASSED` và Hit Rate đạt mức cao nhất.
2. **Corrupted State (Suy Giảm Quality):** Khi tiêm 6 dạng lỗi bẩn (Drop bản ghi mới, Xóa rỗng summary, Tiêm noise, Truncate tiêu đề, Stale date, Duplicate rows), Data Quality Gate lập tức **báo động đỏ (FAILED)** và chỉ số Retrieval Hit Rate & Token F1 bị sụt giảm rõ rệt.
3. **Repaired State (Tự Phục Hồi Idempotent):** Pipeline kích hoạt cơ chế Idempotent Repair khôi phục từ bản thô gốc `data/raw/crossref_records.json`. Hệ thống lấy lại 100% phong độ ban đầu, Quality Gate trở lại **PASSED**.

---
*Report generated automatically by Day 10 Corruption & Recovery Pipeline.*
