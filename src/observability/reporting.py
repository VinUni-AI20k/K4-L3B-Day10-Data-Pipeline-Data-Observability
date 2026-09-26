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
    """Write a reproducible Markdown report for the baseline pipeline."""
    expectation_rows = [
        f"| `{name}` | {'PASS' if result.get('success') else 'FAIL'} |"
        for name, result in quality.get("expectations", {}).items()
    ]
    metrics_rows = [
        f"| `retrieval_hit_rate` | {metrics.get('retrieval_hit_rate', 'N/A')} |",
        f"| `mean_token_f1` | {metrics.get('mean_token_f1', 'N/A')} |",
        f"| `judge_accuracy` | {metrics.get('judge_accuracy', 'N/A')} |",
        f"| `mean_judge_score` | {metrics.get('mean_judge_score', 'N/A')} |",
    ]
    report = "\n".join(
        [
            "# Phase 1 Baseline Report",
            "",
            "## Source and cleaned data",
            "",
            f"- Source: {source_summary.get('source_api', 'Crossref REST API')}",
            f"- Records: {source_summary.get('records', 'N/A')}",
            f"- Clean rows: {source_summary.get('clean_rows', 'N/A')}",
            f"- Embedding model: {source_summary.get('embedding_model', 'N/A')}",
            f"- Chroma collection: `{source_summary.get('collection_name', 'N/A')}`",
            "",
            "## Baseline metrics",
            "",
            "| Metric | Value |",
            "|---|---:|",
            *metrics_rows,
            "",
            "## Great Expectations quality gate",
            "",
            f"- Overall status: **{'PASS' if quality.get('success') else 'FAIL'}**",
            "",
            "| Expectation | Status |",
            "|---|---|",
            *expectation_rows,
            "",
            "## Freshness SLA",
            "",
            f"- Status: **{'FRESH' if freshness.get('is_fresh') else 'STALE'}**",
            f"- Stale rows: {freshness.get('stale_rows', 'N/A')} / {freshness.get('total_rows', 'N/A')}",
            f"- Stale ratio: {freshness.get('stale_ratio', 'N/A')}",
            f"- Threshold: age_days > {freshness.get('threshold_days', 'N/A')} and ratio > {freshness.get('max_stale_ratio', 'N/A')}",
            "",
            "## Conclusion",
            "",
            "The baseline pipeline completed ingestion, cleaning, indexing, evaluation, and observability checks.",
            "",
        ]
    )
    write_text(report_path, report)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
) -> None:
    """Write a reproducible comparison of baseline, corrupted, and repaired runs."""
    metric_names = sorted(
        {
            key
            for metrics in (baseline_metrics, corrupted_metrics, repaired_metrics)
            for key, value in metrics.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    )
    metric_rows = [
        f"| `{name}` | {baseline_metrics.get(name, 'N/A')} | {corrupted_metrics.get(name, 'N/A')} | {repaired_metrics.get(name, 'N/A')} |"
        for name in metric_names
    ]

    def quality_status(report: dict[str, Any]) -> str:
        value = report.get("success")
        return "PASS" if value is True else "FAIL" if value is False else "N/A"

    def freshness_status(report: dict[str, Any]) -> str:
        value = report.get("is_fresh")
        return "FRESH" if value is True else "STALE" if value is False else "N/A"

    baseline_quality = baseline_quality or {}
    baseline_freshness = baseline_freshness or {}
    report = "\n".join(
        [
            "# Corruption and Repair Report",
            "",
            "## Metric comparison",
            "",
            "| Metric | Baseline | Corrupted | Repaired |",
            "|---|---:|---:|---:|",
            *metric_rows,
            "",
            "## Quality gate comparison",
            "",
            f"| Stage | Quality gate | Freshness |",
            "|---|---|---|",
            f"| Baseline | {quality_status(baseline_quality)} | {freshness_status(baseline_freshness)} |",
            f"| Corrupted | {quality_status(corrupted_quality)} | {freshness_status(corrupted_freshness)} |",
            f"| Repaired | {quality_status(repaired_quality)} | {freshness_status(repaired_freshness)} |",
            "",
            "## Interpretation",
            "",
            "The corrupted dataset is generated from the clean baseline using the six logged scenarios. "
            "The repaired dataset is rebuilt from the trusted raw records, then indexed and evaluated again.",
            "",
        ]
    )
    write_text(report_path, report)
