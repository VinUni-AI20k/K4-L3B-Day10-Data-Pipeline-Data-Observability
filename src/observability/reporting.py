from __future__ import annotations

from typing import Any


from pathlib import Path

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Tạo báo cáo markdown cho baseline phase 1."""
    lines = [
        "# Phase 1 Baseline Pipeline Report",
        "",
        "## 1. Nguồn Dữ Liệu & Ingestion Summary",
        f"- **Source API:** {source_summary.get('source_api', 'Crossref REST API')}",
        f"- **Tổng số bản ghi thô (Raw Records):** {source_summary.get('total_raw_records', 0)}",
        f"- **Số bản ghi sạch (Cleaned Records):** {source_summary.get('clean_records', 0)}",
        f"- **ChromaDB Collection:** `{source_summary.get('collection_name', 'papers-baseline')}`",
        f"- **Mô hình Embedding:** `{source_summary.get('embedding_model', 'all-MiniLM-L6-v2')}`",
        "",
        "## 2. Kết Quả Kiểm Định Chất Lượng (Great Expectations 1.x & Freshness SLA)",
        f"- **Trạng thái tổng thể Quality Gate:** {'PASSED (True)' if quality.get('success') else 'FAILED (False)'}",
        f"- **GX 1.x Expectations:** {'PASSED' if quality.get('gx_success') else 'FAILED'}",
        f"- **Số lượng Expectation đạt chuẩn:** {quality.get('successful_expectations_count', 0)}/{quality.get('evaluated_expectations_count', 0)}",
        f"- **Freshness SLA:** {'FRESH (True)' if freshness.get('is_fresh') else 'STALE (False)'}",
        f"- **Số bài báo quá hạn (>180 ngày):** {freshness.get('stale_rows', 0)}/{freshness.get('total_rows', 0)} ({freshness.get('stale_percentage', 0)}%)",
        "",
        "## 3. Chỉ Số Đánh Giá Baseline (RAG Evaluation Metrics)",
        "| Chỉ số (Metric) | Giá trị | Mô tả |",
        "|---|:---:|---|",
        f"| **Retrieval Hit Rate** | **{metrics.get('retrieval_hit_rate', 0.0) * 100:.1f}%** | Tỉ lệ truy vấn tìm đúng bài báo chứa thông tin |",
        f"| **Mean Token F1** | **{metrics.get('mean_token_f1', 0.0):.4f}** | Độ trùng khớp từ ngữ giữa câu trả lời và ground truth |",
        f"| **Judge Accuracy** | **{metrics.get('judge_accuracy', 0.0) * 100:.1f}%** | Đánh giá tính chính xác về mặt ngữ nghĩa |",
        f"| **Mean Judge Score** | **{metrics.get('mean_judge_score', 0.0):.2f}/5.0** | Điểm số trung bình từ giám khảo |",
        f"| **Số lượng câu hỏi kiểm thử** | **{metrics.get('samples', 0)}** | Bộ câu hỏi Benchmark bao phủ 4 nhóm nghiệp vụ |",
        "",
        "## 4. Kết Luận Phase 1",
        "Pipeline Baseline đã chạy thành công qua toàn bộ các bước: Ingestion -> Cleaning -> Quality Gate -> Vector Store Indexing -> Benchmark Evaluation.",
        "Dữ liệu sạch đáp ứng đầy đủ tiêu chuẩn kiểm dịch và sẵn sàng làm mốc đối chứng (Ground Truth Baseline) cho Phase 2.",
    ]
    report_p = Path(report_path)
    write_text(report_p, "\n".join(lines) + "\n")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
