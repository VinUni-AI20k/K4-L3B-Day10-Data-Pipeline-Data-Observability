from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the source, benchmark, quality, and freshness results."""
    source_rows = "\n".join(f"| {key} | {value} |" for key, value in source_summary.items())
    expectation_rows = "\n".join(
        f"| {item['type']} | {item['column'] or '—'} | {'Đạt' if item['success'] else 'Không đạt'} |"
        for item in quality["expectations"]
    )
    type_rows = "\n".join(
        f"| {name} | {values['samples']} | {values['retrieval_hit_rate']:.2%} | {values['mean_token_f1']:.4f} |"
        for name, values in metrics.get("question_type_metrics", {}).items()
    )
    lines = [
        "# Báo cáo Phase 1 — Baseline",
        "",
        "## Dữ liệu đầu vào",
        "",
        "| Mục | Giá trị |",
        "| --- | --- |",
        source_rows,
        "",
        "## Chỉ số đánh giá RAG",
        "",
        "| Chỉ số | Giá trị |",
        "| --- | ---: |",
        f"| Số câu hỏi | {metrics['samples']} |",
        f"| Retrieval Hit Rate | {metrics['retrieval_hit_rate']:.2%} |",
        f"| Mean Token F1 | {metrics['mean_token_f1']:.4f} |",
        f"| Judge accuracy | {metrics['judge_accuracy']:.2%} |",
        f"| Mean judge score | {metrics['mean_judge_score']:.2f}/5 |",
        f"| Số câu dùng heuristic judge | {metrics.get('fallback_judge_count', 0)} |",
        "",
        "| Loại câu hỏi | Số câu | Hit Rate | Token F1 |",
        "| --- | ---: | ---: | ---: |",
        type_rows,
        "",
        "## Kiểm định chất lượng GX 1.x",
        "",
        f"**Kết quả gate:** {'Đạt' if quality['success'] else 'Không đạt'} ({quality['row_count']} bản ghi).",
        "",
        "| Expectation | Cột | Kết quả |",
        "| --- | --- | --- |",
        expectation_rows,
        "",
        "## Độ tươi dữ liệu",
        "",
        "| Chỉ số | Giá trị |",
        "| --- | ---: |",
        f"| Ngưỡng tuổi | {freshness['threshold_days']} ngày |",
        f"| Bài báo quá hạn | {freshness['stale_rows']}/{freshness['total_rows']} |",
        f"| Tỷ lệ quá hạn | {freshness['stale_ratio']:.2%} |",
        f"| Ngưỡng cảnh báo | {freshness['max_stale_ratio']:.0%} |",
        f"| Freshness SLA | {'Đạt' if freshness['is_fresh'] else 'Cảnh báo'} |",
        f"| Mới nhất | {freshness['latest_published'] or 'Không có'} |",
        f"| Cũ nhất | {freshness['oldest_published'] or 'Không có'} |",
        "",
    ]
    if metrics.get("fallback_judge_count"):
        lines.extend((
            "Judge dùng heuristic khi nhà cung cấp LLM không khả dụng; Retrieval Hit Rate và Token F1 vẫn được tính từ câu trả lời truy xuất.",
            "",
        ))
    category_stats = metrics.get("question_type_metrics", {}).get("categories")
    if source_summary.get("Papers with categories") == 0 and category_stats:
        lines.extend((
            f"Crossref không cung cấp subject cho các bài trong snapshot này. {category_stats['samples']} câu hỏi categories kiểm tra khả năng xử lý metadata thiếu; Token F1 của nhóm là {category_stats['mean_token_f1']:.4f}.",
            "",
        ))
    lines.extend((
        "Các câu hỏi benchmark chứa đúng tiêu đề bài báo; bước QA ưu tiên tra cứu tiêu đề chính xác trước khi tính Hit Rate.",
        "",
    ))
    write_text(report_path, "\n".join(lines))


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
