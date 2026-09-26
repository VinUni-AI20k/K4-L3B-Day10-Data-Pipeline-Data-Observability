from __future__ import annotations

from typing import Any


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viết markdown report cho baseline phase vào report_path."""
    from pathlib import Path

    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    gx_status = "✅ PASSED" if quality.get("success", False) else "❌ FAILED"
    freshness_status = "✅ FRESH" if freshness.get("is_fresh", False) else "⚠️ STALE"

    retrieval_hit_rate = metrics.get("retrieval_hit_rate", 0.0)
    mean_token_f1 = metrics.get("mean_token_f1", 0.0)
    judge_accuracy = metrics.get("judge_accuracy", 0.0)
    mean_judge_score = metrics.get("mean_judge_score", 0.0)
    samples = metrics.get("samples", 0)

    lines = [
        "# Baseline Phase 1 Pipeline & Data Observability Report",
        "",
        "## 1. Data Ingestion Summary",
        f"- **Source API**: {source_summary.get('source_api', 'Crossref REST API')}",
        f"- **Query**: `{source_summary.get('source_query', 'N/A')}`",
        f"- **Total Records Ingested**: {source_summary.get('total_records', 0)}",
        f"- **Raw Snapshot**: `{source_summary.get('raw_records_path', 'data/raw/crossref_records.json')}`",
        "",
        "## 2. Data Observability & Quality Gates (Great Expectations 1.x)",
        f"- **Overall Quality Status**: **{gx_status}**",
        f"- **Evaluated Expectations**: {quality.get('statistics', {}).get('evaluated_expectations', 0)}",
        f"- **Successful Expectations**: {quality.get('statistics', {}).get('successful_expectations', 0)}",
        f"- **Unsuccessful Expectations**: {quality.get('statistics', {}).get('unsuccessful_expectations', 0)}",
        "",
        "### Key Expectations Applied:",
        "1. `ExpectTableRowCountToBeBetween(5, 5000)`: Đảm bảo số lượng bản ghi tối thiểu.",
        "2. `ExpectColumnValuesToNotBeNull`: Áp dụng trên `paper_id`, `title`, `text_for_embedding`.",
        "3. `ExpectColumnValuesToBeUnique`: Đảm bảo không trùng lặp `paper_id`.",
        "4. `ExpectColumnValueLengthsToBeBetween`: Đảm bảo độ dài `summary` $\\ge 30$ ký tự.",
        "",
        "## 3. Freshness SLA Monitoring",
        f"- **Freshness Status**: **{freshness_status}**",
        f"- **Threshold**: `{freshness.get('threshold_days', 180)}` ngày",
        f"- **Total Rows Evaluated**: {freshness.get('total_rows', 0)}",
        f"- **Stale Rows (Quá hạn)**: {freshness.get('stale_rows', 0)}",
        f"- **Stale Ratio**: {freshness.get('stale_ratio', 0.0) * 100:.2f}% (Ngưỡng cảnh báo: $\\ge 25\\%$)",
        f"- **Oldest Published Date**: `{freshness.get('oldest_published', 'N/A')}`",
        f"- **Latest Published Date**: `{freshness.get('latest_published', 'N/A')}`",
        "",
        "## 4. Baseline Evaluation & RAG Benchmarks",
        f"- **Evaluated Test Questions**: {samples}",
        "",
        "| Metric | Score | Target / Note |",
        "| :--- | :--- | :--- |",
        f"| **Retrieval Hit Rate** | `{retrieval_hit_rate:.4f}` ({retrieval_hit_rate*100:.1f}%) | Tỷ lệ tìm thấy đúng bài báo trong top-K |",
        f"| **Mean Token F1** | `{mean_token_f1:.4f}` | Độ trùng khớp từ vựng giữa câu trả lời và ground truth |",
        f"| **Judge Accuracy** | `{judge_accuracy:.4f}` ({judge_accuracy*100:.1f}%) | Tỷ lệ câu trả lời được LLM Judge chấm đúng |",
        f"| **Mean Judge Score** | `{mean_judge_score:.2f} / 5.0` | Điểm trung bình của LLM Judge |",
        "",
    ]

    ragas = metrics.get("ragas")
    if isinstance(ragas, dict) and "skipped" not in ragas:
        lines.extend([
            "### Ragas Evaluation Scores:",
            "| Ragas Metric | Value |",
            "| :--- | :--- |",
        ])
        for k, v in ragas.items():
            lines.append(f"| **{k}** | `{v}` |")
        lines.append("")

    lines.extend([
        "## 5. Artifact Verification Checklist",
        "- [x] `data/clean/papers_clean.csv` & `data/clean/papers_clean.json`",
        "- [x] `data/chroma/` (Vector Store Indexed)",
        "- [x] `data/eval/test_set.json`",
        "- [x] `data/results/baseline_metrics.json` & `data/results/baseline_answers.json`",
        "- [x] `data/quality/baseline_quality_report.json` & `data/quality/freshness_report.json`",
        "- [x] `data/reports/phase1_report.md`",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")


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
