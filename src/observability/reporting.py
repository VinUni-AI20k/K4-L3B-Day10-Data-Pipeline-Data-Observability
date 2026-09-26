from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils import write_text


def _fmt(value: float | None, pct: bool = False) -> str:
    if value is None:
        return "N/A"
    if pct:
        return f"{value * 100:.1f}%"
    return f"{value:.3f}"


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Generate markdown report for the baseline phase (Phase 1)."""
    report_path = Path(report_path)
    run_date = source_summary.get("run_date", datetime.now(timezone.utc).isoformat())

    lines: list[str] = [
        "# Phase 1 Baseline Report",
        "",
        f"> Generated: {run_date}",
        "",
        "---",
        "",
        "## 1. Data Source Summary",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| Source API | {source_summary.get('source_api', 'N/A')} |",
        f"| Query | `{source_summary.get('source_query', 'N/A')}` |",
        f"| Raw records fetched | {source_summary.get('total_records', 'N/A')} |",
        f"| Clean records | {source_summary.get('clean_records', 'N/A')} |",
        "",
        "---",
        "",
        "## 2. Baseline Evaluation Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Retrieval Hit Rate | {_fmt(metrics.get('retrieval_hit_rate'), pct=True)} |",
        f"| Mean Token F1 | {_fmt(metrics.get('mean_token_f1'), pct=True)} |",
        f"| Judge Accuracy | {_fmt(metrics.get('judge_accuracy'), pct=True)} |",
        f"| Mean Judge Score | {_fmt(metrics.get('mean_judge_score'))} / 5 |",
        f"| Samples evaluated | {metrics.get('samples', 'N/A')} |",
        "",
        "---",
        "",
        "## 3. Data Quality Gate (Great Expectations)",
        "",
        f"**Overall status:** {'✅ PASSED' if quality.get('success') else '❌ FAILED'}",
        "",
    ]

    # Quality expectation results
    results = quality.get("results", [])
    if results:
        lines += [
            "| Expectation | Success | Details |",
            "|---|---|---|",
        ]
        for r in results:
            exp_type = r.get("expectation_type", r.get("type", "unknown"))
            success = "✅" if r.get("success") else "❌"
            details = str(r.get("result", ""))[:80]
            lines.append(f"| `{exp_type}` | {success} | {details} |")
        lines.append("")
    else:
        lines += [f"```json\n{quality}\n```", ""]

    lines += [
        "---",
        "",
        "## 4. Freshness SLA",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| Is Fresh | {'✅ Yes' if freshness.get('is_fresh') else '⚠️ No'} |",
        f"| Latest Published | {freshness.get('latest_published', 'N/A')} |",
        f"| Oldest Published | {freshness.get('oldest_published', 'N/A')} |",
        f"| Stale Rows (>180 days) | {freshness.get('stale_rows', 'N/A')} / {freshness.get('total_rows', 'N/A')} |",
        f"| Stale Ratio | {_fmt(freshness.get('stale_ratio'), pct=True)} |",
        "",
        "---",
        "",
        "_End of Phase 1 Report_",
    ]

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
    """Generate markdown comparison report: Baseline vs Corrupted vs Repaired."""
    report_path = Path(report_path)
    run_date = datetime.now(timezone.utc).isoformat()

    def delta(base: float, current: float) -> str:
        diff = current - base
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff * 100:.1f}%"

    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0)
    c_hit = corrupted_metrics.get("retrieval_hit_rate", 0.0)
    r_hit = repaired_metrics.get("retrieval_hit_rate", 0.0)

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    c_f1 = corrupted_metrics.get("mean_token_f1", 0.0)
    r_f1 = repaired_metrics.get("mean_token_f1", 0.0)

    b_judge = baseline_metrics.get("judge_accuracy", 0.0)
    c_judge = corrupted_metrics.get("judge_accuracy", 0.0)
    r_judge = repaired_metrics.get("judge_accuracy", 0.0)

    lines: list[str] = [
        "# Data Corruption & Repair Report",
        "",
        f"> Generated: {run_date}",
        "",
        "---",
        "",
        "## Overview",
        "",
        "This report demonstrates the impact of synthetic data corruption on a RAG pipeline",
        "and validates that idempotent repair restores performance to the original baseline.",
        "",
        "---",
        "",
        "## 1. Metrics Comparison: Baseline vs Corrupted vs Repaired",
        "",
        "| Metric | Baseline | Corrupted | Δ Corrupted | Repaired | Δ Repaired |",
        "|---|---|---|---|---|---|",
        f"| Retrieval Hit Rate | {_fmt(b_hit, pct=True)} | {_fmt(c_hit, pct=True)} | {delta(b_hit, c_hit)} | {_fmt(r_hit, pct=True)} | {delta(b_hit, r_hit)} |",
        f"| Mean Token F1      | {_fmt(b_f1, pct=True)}  | {_fmt(c_f1, pct=True)}  | {delta(b_f1, c_f1)}  | {_fmt(r_f1, pct=True)}  | {delta(b_f1, r_f1)} |",
        f"| Judge Accuracy     | {_fmt(b_judge, pct=True)} | {_fmt(c_judge, pct=True)} | {delta(b_judge, c_judge)} | {_fmt(r_judge, pct=True)} | {delta(b_judge, r_judge)} |",
        "",
        "> **Δ** = difference relative to Baseline (negative = degradation, near 0 = recovery).",
        "",
        "---",
        "",
        "## 2. Data Quality Gate Results",
        "",
        "| State | Quality Gate Passed | Freshness OK |",
        "|---|---|---|",
        f"| Baseline  | ✅ (reference) | ✅ (reference) |",
        f"| Corrupted | {'✅' if corrupted_quality.get('success') else '❌'} | {'✅' if corrupted_freshness.get('is_fresh') else '⚠️'} |",
        f"| Repaired  | {'✅' if repaired_quality.get('success') else '❌'} | {'✅' if repaired_freshness.get('is_fresh') else '⚠️'} |",
        "",
        "---",
        "",
        "## 3. Degradation Analysis (Silent Failure)",
        "",
        "When the data corruption is injected, the RAG pipeline continues to serve requests",
        "without runtime errors — this is the **Silent Failure** pattern. The Quality Gate",
        "detects the anomalies *before* they propagate to end users.",
        "",
        "**Corrupted state observations:**",
        "",
    ]

    # Degradation observations
    if c_hit < b_hit:
        lines.append(f"- Retrieval Hit Rate dropped by {abs(c_hit - b_hit) * 100:.1f}pp "
                     f"({_fmt(b_hit, pct=True)} → {_fmt(c_hit, pct=True)})")
    if c_f1 < b_f1:
        lines.append(f"- Mean Token F1 dropped by {abs(c_f1 - b_f1) * 100:.1f}pp "
                     f"({_fmt(b_f1, pct=True)} → {_fmt(c_f1, pct=True)})")
    if not corrupted_quality.get("success"):
        lines.append("- Great Expectations quality gate **FAILED** on corrupted data (expected behaviour).")
    if not corrupted_freshness.get("is_fresh"):
        lines.append("- Freshness SLA **VIOLATED** — stale date injection detected.")

    lines += [
        "",
        "---",
        "",
        "## 4. Recovery Analysis (Idempotent Repair)",
        "",
        "The repair step re-builds the clean dataset **from the original raw records** "
        "(not from the corrupted state), guaranteeing idempotency.",
        "",
        "**Repaired state observations:**",
        "",
    ]

    # Recovery observations
    if r_hit >= b_hit * 0.95:
        lines.append(f"- ✅ Retrieval Hit Rate recovered to {_fmt(r_hit, pct=True)} "
                     f"(baseline: {_fmt(b_hit, pct=True)})")
    else:
        lines.append(f"- ⚠️ Retrieval Hit Rate partially recovered to {_fmt(r_hit, pct=True)} "
                     f"(baseline: {_fmt(b_hit, pct=True)})")
    if r_f1 >= b_f1 * 0.95:
        lines.append(f"- ✅ Mean Token F1 recovered to {_fmt(r_f1, pct=True)} "
                     f"(baseline: {_fmt(b_f1, pct=True)})")
    else:
        lines.append(f"- ⚠️ Mean Token F1 partially recovered to {_fmt(r_f1, pct=True)} "
                     f"(baseline: {_fmt(b_f1, pct=True)})")
    if repaired_quality.get("success"):
        lines.append("- ✅ Great Expectations quality gate **PASSED** after repair.")
    if repaired_freshness.get("is_fresh"):
        lines.append("- ✅ Freshness SLA restored after repair.")

    lines += [
        "",
        "---",
        "",
        "## 5. Freshness SLA Details",
        "",
        "| Field | Corrupted | Repaired |",
        "|---|---|---|",
        f"| Is Fresh | {'✅' if corrupted_freshness.get('is_fresh') else '⚠️ No'} | {'✅' if repaired_freshness.get('is_fresh') else '⚠️ No'} |",
        f"| Latest Published | {corrupted_freshness.get('latest_published', 'N/A')} | {repaired_freshness.get('latest_published', 'N/A')} |",
        f"| Stale Rows | {corrupted_freshness.get('stale_rows', 'N/A')} | {repaired_freshness.get('stale_rows', 'N/A')} |",
        "",
        "---",
        "",
        "_End of Corruption & Repair Report_",
    ]

    write_text(report_path, "\n".join(lines) + "\n")
