from __future__ import annotations

from typing import Any

from core.utils import write_text


def _cell(value: Any) -> str:
    """Make a scalar safe to display inside a Markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline results from measured pipeline outputs."""
    lines = [
        "# Phase 1 baseline report",
        "",
        "## Source and processing",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    for key, value in source_summary.items():
        lines.append(f"| {_cell(key)} | {_cell(value)} |")

    lines.extend(["", "## Baseline evaluation", "", "| Metric | Value |", "| --- | ---: |"])
    for key in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        value = metrics.get(key, "N/A")
        display = f"{value:.3f}" if isinstance(value, float) else _cell(value)
        lines.append(f"| {key} | {display} |")

    lines.extend([
        "",
        "## Data quality and freshness",
        "",
        "| Check | Result |",
        "| --- | --- |",
        f"| Overall quality gate | {_cell(quality.get('success'))} |",
        f"| Great Expectations | {_cell(quality.get('gx_success'))} |",
        f"| Freshness SLA | {_cell(freshness.get('is_fresh'))} |",
        f"| Clean rows checked | {_cell(quality.get('row_count'))} |",
        f"| Stale rows | {_cell(freshness.get('stale_rows'))} |",
        f"| Stale ratio | {freshness.get('stale_ratio', 0):.3f} |",
        f"| Freshness threshold (days) | {_cell(freshness.get('freshness_threshold_days'))} |",
        f"| Latest publication | {_cell(freshness.get('latest_published'))} |",
        f"| Oldest publication | {_cell(freshness.get('oldest_published'))} |",
        "",
        "### Great Expectations checks",
        "",
        "| Expectation | Column | Passed | Observed | Unexpected |",
        "| --- | --- | --- | ---: | ---: |",
    ])
    for check in quality.get("expectations", []):
        lines.append(
            "| {expectation_type} | {column} | {success} | {observed_value} | {unexpected_count} |".format(
                **{key: _cell(check.get(key, "")) for key in (
                    "expectation_type", "column", "success", "observed_value", "unexpected_count"
                )}
            )
        )
    write_text(report_path, "\n".join(lines) + "\n")


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
