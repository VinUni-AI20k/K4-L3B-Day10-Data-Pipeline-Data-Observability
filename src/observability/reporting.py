from __future__ import annotations

from typing import Any

from core.utils import now_utc, write_text


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase."""
    lines = [
        "# Phase 1 Baseline Report",
        "",
        f"_Generated at {now_utc().isoformat()}_",
        "",
        "## Source Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    for key, value in source_summary.items():
        lines.append(f"| {key} | {_fmt(value)} |")

    lines += [
        "",
        "## Evaluation Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| retrieval_hit_rate | {_fmt(metrics.get('retrieval_hit_rate'))} |",
        f"| mean_token_f1 | {_fmt(metrics.get('mean_token_f1'))} |",
        f"| judge_accuracy | {_fmt(metrics.get('judge_accuracy'))} |",
        f"| mean_judge_score | {_fmt(metrics.get('mean_judge_score'))} |",
        f"| samples | {_fmt(metrics.get('samples'))} |",
        "",
        "## Data Quality",
        "",
        f"- Overall success: **{quality.get('success')}**",
        f"- Row count: {quality.get('row_count')}",
        "",
        "## Freshness",
        "",
        f"- Total rows: {freshness.get('total_rows')}",
        f"- Stale rows: {freshness.get('stale_rows')}",
        f"- Stale ratio: {_fmt(freshness.get('stale_ratio'))}",
        f"- Freshness threshold (days): {freshness.get('freshness_threshold_days')}",
        f"- Is fresh: **{freshness.get('is_fresh')}**",
        f"- Latest published: {freshness.get('latest_published')}",
        f"- Oldest published: {freshness.get('oldest_published')}",
        "",
    ]

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
    """Viet markdown report so sanh baseline/corrupted/repaired."""
    metric_keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]

    lines = [
        "# Data Corruption & Repair Comparison Report",
        "",
        f"_Generated at {now_utc().isoformat()}_",
        "",
        "## Metrics Comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key in metric_keys:
        lines.append(
            f"| {key} | {_fmt(baseline_metrics.get(key))} | {_fmt(corrupted_metrics.get(key))} | {_fmt(repaired_metrics.get(key))} |"
        )

    lines += [
        "",
        "## Data Quality Comparison",
        "",
        "| Stage | Success | Row Count |",
        "| --- | --- | ---: |",
        f"| Corrupted | {corrupted_quality.get('success')} | {corrupted_quality.get('row_count')} |",
        f"| Repaired | {repaired_quality.get('success')} | {repaired_quality.get('row_count')} |",
        "",
        "## Freshness Comparison",
        "",
        "| Stage | Stale Rows | Total Rows | Stale Ratio | Is Fresh |",
        "| --- | ---: | ---: | ---: | --- |",
        (
            f"| Corrupted | {corrupted_freshness.get('stale_rows')} | {corrupted_freshness.get('total_rows')} | "
            f"{_fmt(corrupted_freshness.get('stale_ratio'))} | {corrupted_freshness.get('is_fresh')} |"
        ),
        (
            f"| Repaired | {repaired_freshness.get('stale_rows')} | {repaired_freshness.get('total_rows')} | "
            f"{_fmt(repaired_freshness.get('stale_ratio'))} | {repaired_freshness.get('is_fresh')} |"
        ),
        "",
    ]

    write_text(report_path, "\n".join(lines))
