from __future__ import annotations

from typing import Any

from core.utils import ensure_parent, now_utc


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_num(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "N/A"


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase (Checkpoint 3)."""
    lines: list[str] = []
    lines.append("# Phase 1 Report - Baseline Pipeline")
    lines.append("")
    lines.append(f"_Generated at: {now_utc().isoformat()}_")
    lines.append("")

    lines.append("## 1. Source Summary")
    lines.append("")
    for key, value in source_summary.items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")

    lines.append("## 2. Retrieval / Evaluation Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| :--- | ---: |")
    lines.append(f"| Samples | {metrics.get('samples', 'N/A')} |")
    lines.append(f"| Retrieval Hit Rate | {_fmt_pct(metrics.get('retrieval_hit_rate'))} |")
    lines.append(f"| Mean Token F1 | {_fmt_num(metrics.get('mean_token_f1'))} |")
    lines.append(f"| Judge Accuracy | {_fmt_pct(metrics.get('judge_accuracy'))} |")
    lines.append(f"| Mean Judge Score | {_fmt_num(metrics.get('mean_judge_score'))} |")
    lines.append("")

    lines.append("## 3. Data Quality Gate")
    lines.append("")
    lines.append(f"- **Status (success)**: `{quality.get('success')}`")
    if quality.get("expectations"):
        lines.append("- **Expectations**:")
        for item in quality["expectations"]:
            lines.append(f"  - {item}")
    lines.append("")

    lines.append("## 4. Freshness SLA")
    lines.append("")
    lines.append(f"- **is_fresh**: `{freshness.get('is_fresh')}`")
    lines.append(f"- **latest_published**: {freshness.get('latest_published')}")
    lines.append(f"- **oldest_published**: {freshness.get('oldest_published')}")
    lines.append(
        f"- **stale_rows / total_rows**: {freshness.get('stale_rows')} / {freshness.get('total_rows')}"
    )
    lines.append("")

    ensure_parent(report_path)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    """Viet markdown report so sanh Baseline vs Corrupted vs Repaired (Checkpoint 5)."""
    lines: list[str] = []
    lines.append("# Corruption & Repair Comparison Report")
    lines.append("")
    lines.append(f"_Generated at: {now_utc().isoformat()}_")
    lines.append("")

    lines.append("## 1. Metrics Comparison: Baseline vs Corrupted vs Repaired")
    lines.append("")
    lines.append("| Metric | Baseline | Corrupted | Repaired |")
    lines.append("| :--- | ---: | ---: | ---: |")
    lines.append(
        "| Retrieval Hit Rate | "
        f"{_fmt_pct(baseline_metrics.get('retrieval_hit_rate'))} | "
        f"{_fmt_pct(corrupted_metrics.get('retrieval_hit_rate'))} | "
        f"{_fmt_pct(repaired_metrics.get('retrieval_hit_rate'))} |"
    )
    lines.append(
        "| Mean Token F1 | "
        f"{_fmt_num(baseline_metrics.get('mean_token_f1'))} | "
        f"{_fmt_num(corrupted_metrics.get('mean_token_f1'))} | "
        f"{_fmt_num(repaired_metrics.get('mean_token_f1'))} |"
    )
    lines.append(
        "| Judge Accuracy | "
        f"{_fmt_pct(baseline_metrics.get('judge_accuracy'))} | "
        f"{_fmt_pct(corrupted_metrics.get('judge_accuracy'))} | "
        f"{_fmt_pct(repaired_metrics.get('judge_accuracy'))} |"
    )
    lines.append(
        "| Mean Judge Score | "
        f"{_fmt_num(baseline_metrics.get('mean_judge_score'))} | "
        f"{_fmt_num(corrupted_metrics.get('mean_judge_score'))} | "
        f"{_fmt_num(repaired_metrics.get('mean_judge_score'))} |"
    )
    lines.append("")

    lines.append("## 2. Data Quality Gate")
    lines.append("")
    lines.append("| Stage | Quality Status | is_fresh |")
    lines.append("| :--- | :---: | :---: |")
    lines.append(
        f"| Corrupted | `{corrupted_quality.get('success')}` | `{corrupted_freshness.get('is_fresh')}` |"
    )
    lines.append(
        f"| Repaired | `{repaired_quality.get('success')}` | `{repaired_freshness.get('is_fresh')}` |"
    )
    lines.append("")

    lines.append("## 3. Nhan xet")
    lines.append("")
    hit_drop = None
    hit_recover = None
    try:
        hit_drop = float(baseline_metrics.get("retrieval_hit_rate", 0)) - float(
            corrupted_metrics.get("retrieval_hit_rate", 0)
        )
        hit_recover = float(repaired_metrics.get("retrieval_hit_rate", 0)) - float(
            corrupted_metrics.get("retrieval_hit_rate", 0)
        )
    except (TypeError, ValueError):
        pass
    if hit_drop is not None:
        lines.append(
            f"- Sau khi bi tiem loi, Retrieval Hit Rate giam **{_fmt_pct(hit_drop)}** so voi baseline "
            "(hien tuong Silent Failure)."
        )
    if hit_recover is not None:
        lines.append(
            f"- Sau khi Repair tu raw snapshot, Retrieval Hit Rate phuc hoi them **{_fmt_pct(hit_recover)}** "
            "so voi trang thai corrupted."
        )
    lines.append("")

    ensure_parent(report_path)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
