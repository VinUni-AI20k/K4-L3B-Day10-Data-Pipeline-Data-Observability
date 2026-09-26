Main responsibility:
- Evaluation Dataset
- Embedding
- ChromaDB
- RAG Agent
- Baseline Evaluation
- Corrupted Evaluation
- Repaired Evaluation
- Metrics
- Reports / Integration

Main files:
- src/evaluation/testset.py
- src/retrieval/*
- src/pipelines/phase1.py
- script/run_phase1.py
- script/run_corruption_flow.py
- report/*

Main artifacts:
- data/eval/*
- data/chroma/*
- data/results/baseline_metrics.json
- data/results/corrupted_metrics.json
- data/results/repaired_metrics.json
- data/reports/*


# CHECKLIST
## Data Corruption + Repair + Comparison + Final Demo

### 1. Chuẩn bị
- [ ] Pull/merge code từ Member 1
- [ ] Chạy baseline thành công
- [ ] Kiểm tra `baseline_metrics.json`
- [ ] Kiểm tra `data/raw/crossref_records.json`

### 2. Synthetic Data Corruption
- [ ] Hoàn thiện `src/ingestion/corruption.py`
- [ ] Implement Drop latest records
- [ ] Implement Blank summary
- [ ] Implement Inject noise
- [ ] Implement Truncate title
- [ ] Implement Stale date
- [ ] Implement Duplicate rows
- [ ] Ghi log vào `data/results/corruption_log.json`
- [ ] Kiểm tra đủ 6 loại corruption

### 3. Corrupted Evaluation
- [ ] Chạy pipeline trên corrupted data
- [ ] Chạy lại cùng evaluation set
- [ ] Đo `retrieval_hit_rate`
- [ ] Đo `mean_token_f1`
- [ ] Xuất `data/results/corrupted_metrics.json`
- [ ] Xác nhận metrics thay đổi so với baseline

### 4. Repair
- [ ] Kiểm tra `script/run_corruption_flow.py`
- [ ] Implement/hoàn thiện logic repair
- [ ] Khôi phục dữ liệu từ raw artifact
- [ ] Không lấy corrupted data làm nguồn repair
- [ ] Đảm bảo repair có tính idempotent
- [ ] Chạy lại Data Quality Gate
- [ ] Chạy lại pipeline sau repair
- [ ] Tạo `data/results/repaired_metrics.json`

### 5. So sánh 3 trạng thái
- [ ] So sánh Baseline
- [ ] So sánh Corrupted
- [ ] So sánh Repaired
- [ ] So sánh `retrieval_hit_rate`
- [ ] So sánh `mean_token_f1`
- [ ] Tạo `data/reports/corruption_report.md`
- [ ] Bảng có đủ 3 trạng thái
- [ ] Thể hiện được degradation khi data bị lỗi
- [ ] Thể hiện được recovery sau repair

### 6. Final Validation
- [ ] Chạy `python script/run_phase1.py`
- [ ] Chạy `python script/run_corruption_flow.py`
- [ ] Kiểm tra toàn bộ artifacts
- [ ] Không còn TODO quan trọng
- [ ] Không lỗi import
- [ ] Không commit `.env` / API key

### 7. Live Demo
- [ ] Chuẩn bị baseline
- [ ] Demo corrupted data
- [ ] Cho thấy Quality Gate phát hiện lỗi
- [ ] Cho thấy RAG metrics giảm
- [ ] Chạy repair
- [ ] Cho thấy metrics phục hồi
- [ ] Chuẩn bị bảng Baseline vs Corrupted vs Repaired
- [ ] Chuẩn bị giải thích Freshness SLA
- [ ] Chuẩn bị giải thích Great Expectations
- [ ] Chuẩn bị giải thích Embedding
- [ ] Chuẩn bị giải thích Idempotent Repair

### 8. Final Submission
- [ ] Merge code 2 members vào `main`
- [ ] Kiểm tra `git status`
- [ ] Kiểm tra toàn bộ artifact
- [ ] Kiểm tra `TEAM.md`
- [ ] Kiểm tra `SUBMISSION.md`
- [ ] Push `main`
- [ ] Submit repository lên VLearn LMS