from __future__ import annotations

from typing import Any

from core.utils import write_text


def _metric(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return "n/a"
    return str(value)


def _quality_line(quality: dict[str, Any]) -> str:
    success = quality.get("success")
    row_count = quality.get("row_count", "n/a")
    return f"success={success}, rows={row_count}"


def _freshness_line(freshness: dict[str, Any]) -> str:
    return (
        f"is_fresh={freshness.get('is_fresh')}, "
        f"stale_rows={freshness.get('stale_rows')}/{freshness.get('total_rows')}, "
        f"latest={freshness.get('latest_published')}, oldest={freshness.get('oldest_published')}"
    )


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline markdown report from pipeline artifacts."""
    lines = [
        "# Phase 1 Report — Baseline Data Pipeline",
        "",
        "## Source summary",
        "",
        f"- API: {source_summary.get('source_api', 'n/a')}",
        f"- Query: `{source_summary.get('query', '')}`",
        f"- Raw records: {source_summary.get('n_raw', 'n/a')}",
        f"- Clean records: {source_summary.get('n_clean', 'n/a')}",
        f"- Run date: {source_summary.get('run_date', 'n/a')}",
        f"- Embedding model: {source_summary.get('embedding_model', 'sentence-transformers/all-MiniLM-L6-v2')}",
        f"- Collection: {source_summary.get('collection_name', 'papers-baseline')}",
        "",
        "## Baseline evaluation",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| samples | {_metric(metrics, 'samples')} |",
        f"| retrieval_hit_rate | {_metric(metrics, 'retrieval_hit_rate')} |",
        f"| mean_token_f1 | {_metric(metrics, 'mean_token_f1')} |",
        f"| judge_accuracy | {_metric(metrics, 'judge_accuracy')} |",
        f"| mean_judge_score | {_metric(metrics, 'mean_judge_score')} |",
        "",
        "## Data quality (Great Expectations 1.x)",
        "",
        f"- {_quality_line(quality)}",
        f"- Expectations: {', '.join(quality.get('expectations', []))}",
        "",
        "## Freshness SLA",
        "",
        f"- {_freshness_line(freshness)}",
        f"- Threshold: age_days > {freshness.get('threshold_days', 180)} on more than 25% of rows sets `is_fresh=False`.",
        "",
        "## Artifacts",
        "",
        "- `data/clean/papers_clean.csv` / `papers_clean.json`",
        "- `data/chroma/` collection `papers-baseline`",
        "- `data/eval/test_set.json`",
        "- `data/results/baseline_metrics.json`",
        "- `data/quality/baseline_quality_report.json`",
        "- `data/quality/freshness_report.json`",
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
    """Write the Baseline vs Corrupted vs Repaired comparison report."""
    def delta(left: dict[str, Any], right: dict[str, Any], key: str) -> str:
        try:
            return f"{float(right.get(key, 0)) - float(left.get(key, 0)):+.4f}"
        except (TypeError, ValueError):
            return "n/a"

    lines = [
        "# Corruption Flow Report — Baseline vs Corrupted vs Repaired",
        "",
        "The same evaluation set is used across all three states so the comparison is valid.",
        "",
        "## Performance comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Corrupted − Baseline | Repaired − Corrupted |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score", "samples"):
        lines.append(
            "| "
            f"{key} | {_metric(baseline_metrics, key)} | {_metric(corrupted_metrics, key)} | "
            f"{_metric(repaired_metrics, key)} | {delta(baseline_metrics, corrupted_metrics, key)} | "
            f"{delta(corrupted_metrics, repaired_metrics, key)} |"
        )

    lines.extend(
        [
            "",
            "## Data quality and freshness",
            "",
            "| Signal | Corrupted | Repaired |",
            "|---|---|---|",
            f"| GX success | {corrupted_quality.get('success')} | {repaired_quality.get('success')} |",
            f"| row_count | {corrupted_quality.get('row_count')} | {repaired_quality.get('row_count')} |",
            f"| is_fresh | {corrupted_freshness.get('is_fresh')} | {repaired_freshness.get('is_fresh')} |",
            f"| stale_rows | {corrupted_freshness.get('stale_rows')}/{corrupted_freshness.get('total_rows')} | {repaired_freshness.get('stale_rows')}/{repaired_freshness.get('total_rows')} |",
            "",
            "## Interpretation",
            "",
            "- Corrupted data trips the Great Expectations gate (duplicate IDs, blank/short summaries, truncated titles) and the freshness SLA.",
            "- Retrieval hit rate and token F1 drop because documents are missing, titles no longer match, and summaries are blank or noisy. That is silent failure: the agent still answers, but the answers are worse.",
            "- Repair rebuilds the clean dataframe from the raw Crossref snapshot, so the quality gate and retrieval metrics recover.",
            "",
            "## Artifacts",
            "",
            "- `data/results/corruption_log.json`",
            "- `data/results/corrupted_metrics.json`",
            "- `data/results/repaired_metrics.json`",
            "- `data/quality/corrupted_quality_report.json`",
            "- `data/clean/papers_clean_corrupted.json`",
            "- `data/clean/papers_clean_repaired.json`",
            "",
        ]
    )
    write_text(report_path, "\n".join(lines))
