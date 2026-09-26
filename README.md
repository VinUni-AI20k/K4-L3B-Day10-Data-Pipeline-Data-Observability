# K4-L3B-Day10 — Data Pipeline & Data Observability for RAG

> **Repository:** `K4-L3B-DAY10-Team03-DataPipelineDataObservability`  
> **Hình thức:** Teamwork (Nhóm 4 thành viên) | **Lớp:** K4 - Lớp B (Ca Sáng)  
> **Ngày hoàn thành:** 26/09/2026 | **Hạn nộp LMS:** 23:59:59 cùng ngày  

---

## 👥 Danh Sách Thành Viên & Phân Công

| STT | Họ và tên | MSSV | Vai trò & Trách nhiệm chính |
| :---: | :--- | :---: | :--- |
| 1 | **Đặng Thái Anh** | 2A202602740 | **Trưởng nhóm / Data Foundation, Ingestion & Idempotent Recovery** (`crossref.py`, `cleaning.py`, raw data snapshot, 6 corruption scenarios) |
| 2 | **Nguyễn Đức Anh** | 2A202602888 | **Pipeline Integrator & Data Orchestration** (`core/`, `phase1.py`, `corruption_flow.py`, `script/`, Self-Healing & Pytest CI) |
| 3 | **Đỗ Trung Tuyến** | 2A202602427 | **RAG Agent & Vector Index Architecture** (`retrieval/index.py`, `embeddings.py`, `agent.py`, `qa.py`, ChromaDB collections) |
| 4 | **Nguyễn Khánh Duy** | 2A202602403 | **Data Observability, Freshness SLA & Benchmark Evaluation** (`quality.py` GX 1.x, `testset.py`, `metrics.py`, reporting, HTML Dashboard) |

---

## 📊 Bảng Đối Chiếu Hiệu Năng 3 Trạng Thái (Performance Benchmarks)

| Chỉ số Đánh Giá | Baseline (Sạch) | Corrupted (Tiêm 6 lỗi) | Repaired (Phục hồi) | Delta Suy Thoái | Đánh Giá Phục Hồi |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Retrieval Hit Rate (@4)** | **100.0%** | **60.0%** | **100.0%** | **-40.0%** | Phục hồi hoàn toàn 100% |
| **Mean Token F1 Score** | **100.0%** | **85.1%** | **100.0%** | **-14.9%** | Phục hồi hoàn toàn 100% |
| **Judge Evaluation Accuracy** | **100.0%** | **90.0%** | **100.0%** | **-10.0%** | Phục hồi hoàn toàn 100% |
| **Mean Judge Score (1-5)** | **5.00** | **4.20** | **5.00** | **-0.80** | Đạt điểm tối đa 5.00 |
| **GX 1.x Quality Gate** | **PASSED (True)** | **FAILED (False)** | **PASSED (True)** | Chặn dữ liệu bẩn | Chốt chặn an toàn |
| **Freshness SLA Status** | **HEALTHY (4.2%)** | **VIOLATED (40.9%)** | **HEALTHY (0.0%)** | > 25% ngưỡng SLA | Phục hồi độ tươi chuẩn |

---

## 🚀 Hướng Dẫn Chạy Nhanh (Quickstart)

### 1. Kích hoạt môi trường ảo
```bash
# Windows PowerShell
.venv\Scripts\activate
```

### 2. Chạy Baseline Pipeline (Pha 1)
```bash
python script/run_phase1.py
```
*Thu thập 24 bài báo khoa học từ Crossref, làm sạch dữ liệu, nạp ChromaDB `papers-baseline`, kiểm định GX 1.x và Freshness SLA, xuất báo cáo `data/reports/phase1_report.md`.*

### 3. Chạy Data Observability & Corruption Flow (Pha 2 & 3)
```bash
python script/run_corruption_flow.py
```
*Tiêm 6 lỗi dữ liệu, chứng minh hiện tượng Silent Failure (Hit Rate giảm còn 60.0%), sau đó thực hiện Idempotent Repair từ raw snapshot, khôi phục 100% hiệu năng và xuất báo cáo `data/reports/corruption_report.md`.*

### 4. Demo Tính Năng Tự Động Phục Hồi - Automated Self-Healing (Bonus B2)
```bash
python script/run_self_healing.py
```
*Tự động phát hiện vi phạm Great Expectations hoặc Freshness SLA trên luồng dữ liệu bất kỳ và tự động kích hoạt logic Repair khôi phục 100% dữ liệu sạch mà không cần can thiệp thủ công.*

### 5. Chạy Toàn Bộ Test Suite Pytest (Bonus B3)
```bash
pytest tests/ -v
```
*Chạy 9 unit tests tự động bao phủ từ Ingestion, Cleaning, GX Suite, Freshness, ChromaDB Search, LLM Factory đến Self-Healing (100% passed).*

### 6. Xem Interactive Observability Dashboard (Bonus B1)
Mở file `report/observability_dashboard.html` trên trình duyệt để theo dõi trực quan bảng điều khiển thời gian thực với thiết kế Dark Mode Glassmorphism hiện đại.

---

## 🏗️ Cấu Trúc Dự Án (Project Structure)

```text
K4-L3B-DAY10-Team03-DataPipelineDataObservability/
├── .github/
│   └── workflows/ci.yml       ← GitHub Actions CI pipeline (Bonus B3)
├── data/
│   ├── raw/                   ← crossref_response.json, crossref_records.json (Data Lineage)
│   ├── clean/                 ← papers_clean.csv, papers_clean.json
│   ├── chroma/                ← ChromaDB local collections (baseline, corrupted, repaired)
│   ├── eval/                  ← test_set.json (10 câu benchmark qua 4 domains)
│   ├── quality/               ← GX 1.x reports & Freshness SLA logs
│   ├── results/               ← baseline/corrupted/repaired_metrics.json, corruption_log.json
│   └── reports/               ← phase1_report.md, corruption_report.md
├── docs/
│   ├── CHECKPOINTS.md         ← Lộ trình 240 phút
│   ├── RUBRIC.md              ← Tiêu chí chấm điểm (100 chuẩn + 10 bonus)
│   ├── SUBMISSION.md          ← Quy định nộp bài & bảo mật
│   └── TEAM.md                ← Thông tin nhóm & phân công chi tiết 3 thành viên
├── report/
│   ├── group_report.md        ← Báo cáo tổng hợp nhóm hoàn chỉnh (13 phần)
│   ├── 2A202602888_NguyenDucAnh.md  ← Báo cáo cá nhân Nguyễn Đức Anh
│   ├── 2A202602740_DangThaiAnh.md   ← Báo cáo cá nhân Đặng Thái Anh
│   ├── 2A202602427_DoTrungTuyen.md  ← Báo cáo cá nhân Đỗ Trung Tuyến
│   ├── 2A202602403_NguyenKhanhDuy.md ← Báo cáo cá nhân Nguyễn Khánh Duy
│   └── observability_dashboard.html ← Interactive Web Dashboard (Bonus B1)
├── script/
│   ├── run_phase1.py          ← Entrypoint Pha 1 Baseline
│   ├── run_corruption_flow.py ← Entrypoint Pha 2 & 3 Corruption & Repair
│   └── run_self_healing.py    ← Entrypoint Demo Auto Self-Healing (Bonus B2)
├── src/
│   ├── core/                  ← config.py, utils.py (quản lý đường dẫn & I/O)
│   ├── ingestion/             ← crossref.py (fallback), cleaning.py (5-part embedding), corruption.py (6 lỗi)
│   ├── retrieval/             ← embeddings.py (MiniLM), index.py (ChromaDB), llm.py, qa.py, agent.py
│   ├── evaluation/            ← testset.py (10 câu benchmark), metrics.py (Hit Rate, Token F1, Judge)
│   ├── observability/         ← quality.py (GX 1.x ephemeral), reporting.py, self_healing.py
│   └── pipelines/             ← phase1.py, corruption_flow.py
├── tests/
│   └── test_pipeline.py       ← Bộ kiểm thử toàn diện 9 test cases
├── pyproject.toml
└── README.md
```

---

## 🌟 Điểm Thưởng Đã Hoàn Thành (Bonus Items - Đạt Tối Đa 10/10)

1. **B1: Interactive Observability Dashboard (+5 điểm):**
   - File: `report/observability_dashboard.html`
   - Giao diện web trực quan theo dõi KPI card, biểu đồ thanh trực quan mức độ suy giảm, bảng so sánh 3 trạng thái và chi tiết 6 kịch bản lỗi.
2. **B2: Automated Self-Healing Pipeline (+5 điểm):**
   - File: `src/observability/self_healing.py` & `script/run_self_healing.py`
   - Tự động phát hiện vi phạm Great Expectations hoặc Freshness SLA trên luồng dữ liệu bất kỳ và tự động kích hoạt logic Repair khôi phục 100% dữ liệu sạch mà không cần can thiệp thủ công.
3. **B3: End-to-End Automated Test Suite & CI (+5 điểm):**
   - File: `tests/test_pipeline.py` & `.github/workflows/ci.yml`
   - 9 test cases tự động kiểm thử toàn diện mọi tầng kiến trúc, cấu hình GitHub Actions CI chạy tự động khi push mã nguồn lên nhánh `main`.

---

## ✅ Checklist Nghiệm Thu Hoàn Thành (100%)

- [x] `python script/run_phase1.py` chạy exit code 0.
- [x] `python script/run_corruption_flow.py` chạy exit code 0.
- [x] `python script/run_self_healing.py` chạy exit code 0.
- [x] `pytest tests/ -v` pass 9/9 tests (100%).
- [x] `data/reports/corruption_report.md` có đầy đủ bảng đối chiếu 3 trạng thái.
- [x] Tồn tại đủ các file metrics JSON (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`).
- [x] `docs/TEAM.md` và `report/group_report.md` điền đầy đủ 100% thông tin.
- [x] Có đầy đủ 4 báo cáo cá nhân: `2A202602888_NguyenDucAnh.md`, `2A202602740_DangThaiAnh.md`, `2A202602427_DoTrungTuyen.md`, `2A202602403_NguyenKhanhDuy.md`
- [x] Không commit file `.env` lên GitHub (đã cấu hình trong `.gitignore`).
