from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


_METRICS = (
    ("retrieval_hit_rate", "Retrieval Hit Rate"),
    ("mean_token_f1", "Mean Token F1"),
    ("judge_accuracy", "Judge Accuracy"),
    ("mean_judge_score", "Mean Judge Score"),
)


def _display(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value) or "N/A"
    if isinstance(value, dict):
        if "skipped" in value:
            return str(value["skipped"])
        if "error" in value:
            return str(value["error"])
        return ", ".join(f"{key}={_display(item)}" for key, item in value.items()) or "N/A"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _metric_delta(current: Any, reference: Any) -> str:
    if not isinstance(current, (int, float)) or not isinstance(reference, (int, float)):
        return "N/A"
    return f"{current - reference:+.4f}"


def _quality_rows(quality: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for item in quality.get("expectations", []):
        name = item.get("expectation_type", "Unknown")
        column = item.get("column") or "—"
        rows.append(f"| {_display(name)} | {_display(column)} | {_display(item.get('success'))} |")
    if not rows:
        rows.append("| No expectation results | — | N/A |")
    return rows

def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline source, evaluation, quality, and freshness report."""
    source_rows = [
        f"| {_display(key)} | {_display(value)} |" for key, value in source_summary.items()
    ] or ["| status | No source summary provided |"]
    metric_rows = [
        f"| {label} | {_display(metrics.get(key))} |" for key, label in _METRICS
    ]
    metric_rows.append(f"| Samples | {_display(metrics.get('samples'))} |")
    metric_rows.append(f"| Ragas | {_display(metrics.get('ragas'))} |")

    lines = [
        "# Phase 1 — Baseline Data Pipeline Report",
        "",
        "## Source summary",
        "",
        "| Field | Value |",
        "|---|---|",
        *source_rows,
        "",
        "## Evaluation metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        *metric_rows,
        "",
        "## Data quality",
        "",
        f"**Overall status:** {_display(quality.get('success'))}",
        "",
        "| Expectation | Column | Status |",
        "|---|---|---|",
        *_quality_rows(quality),
        "",
        "## Freshness SLA",
        "",
        "| Signal | Value |",
        "|---|---:|",
        f"| Status | {_display(freshness.get('is_fresh'))} |",
        f"| Latest published | {_display(freshness.get('latest_published'))} |",
        f"| Oldest published | {_display(freshness.get('oldest_published'))} |",
        f"| Stale rows | {_display(freshness.get('stale_rows'))} / {_display(freshness.get('total_rows'))} |",
        f"| Stale ratio | {_display(freshness.get('stale_ratio'))} |",
        f"| Threshold | {_display(freshness.get('threshold_days'))} days |",
        "",
        "> This report is generated from pipeline artifacts; values must not be edited manually.",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))


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
    """Write a three-state metrics comparison plus quality recovery signals."""
    metric_rows = []
    for key, label in _METRICS:
        baseline = baseline_metrics.get(key)
        corrupted = corrupted_metrics.get(key)
        repaired = repaired_metrics.get(key)
        metric_rows.append(
            f"| {label} | {_display(baseline)} | {_display(corrupted)} | "
            f"{_display(repaired)} | {_metric_delta(corrupted, baseline)} | "
            f"{_metric_delta(repaired, corrupted)} |"
        )

    quality_rows = [
        "| Quality Gate | "
        f"{_display(corrupted_quality.get('success'))} | {_display(repaired_quality.get('success'))} |",
        "| Failed expectations | "
        f"{sum(not bool(item.get('success')) for item in corrupted_quality.get('expectations', []))} | "
        f"{sum(not bool(item.get('success')) for item in repaired_quality.get('expectations', []))} |",
        "| Freshness SLA | "
        f"{_display(corrupted_freshness.get('is_fresh'))} | "
        f"{_display(repaired_freshness.get('is_fresh'))} |",
        "| Stale rows | "
        f"{_display(corrupted_freshness.get('stale_rows'))} | "
        f"{_display(repaired_freshness.get('stale_rows'))} |",
    ]

    lines = [
        "# Corruption Impact and Repair Report",
        "",
        "## Baseline vs Corrupted vs Repaired",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Corruption delta | Repair delta |",
        "|---|---:|---:|---:|---:|---:|",
        *metric_rows,
        "",
        "## Quality and freshness recovery",
        "",
        "Baseline quality and freshness are recorded in `phase1_report.md`. The table below compares the failure and repair stages supplied to this report.",
        "",
        "| Signal | Corrupted | Repaired |",
        "|---|---:|---:|",
        *quality_rows,
        "",
        "## Interpretation",
        "",
        "- A negative corruption delta indicates degradation relative to the baseline.",
        "- A positive repair delta indicates recovery after rebuilding from the trusted raw snapshot.",
        "- Conclusions should only be made when the generated values show a measurable change.",
        "",
        "> This report is generated from pipeline artifacts; values must not be edited manually.",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))
