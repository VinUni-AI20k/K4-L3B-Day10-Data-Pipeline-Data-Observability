from __future__ import annotations

from typing import Any


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the measured baseline results as a Markdown report."""
    from pathlib import Path

    from core.utils import write_text

    if Path(report_path).exists():
        raise FileExistsError(f"Baseline report already exists: {report_path}")

    lines = [
        "# Phase 1 baseline report",
        "",
        "## Source and indexing",
        "",
        f"- Source: {source_summary['source_api']}",
        f"- Ingestion mode: {source_summary['ingestion_mode']}",
        f"- Snapshot: `{source_summary['snapshot_path']}`",
        f"- Run time (UTC): {source_summary['run_at_utc']}",
        f"- Raw records: {source_summary['input_records']}",
        f"- Clean records: {source_summary['clean_records']}",
        f"- Removed during cleaning: {source_summary['dropped_records']}",
        f"- Chroma collection: `{source_summary['collection_name']}`",
        f"- Indexed documents: {source_summary['indexed_documents']}",
        f"- Benchmark questions: {source_summary['test_questions']}",
        "",
        "## Evaluation",
        "",
        "| Measure | Result |",
        "| --- | ---: |",
        f"| Evaluated questions | {metrics['samples']} |",
        f"| Retrieval Hit Rate | {metrics['retrieval_hit_rate']:.2%} |",
        f"| Mean Token F1 | {metrics['mean_token_f1']:.4f} |",
        f"| Judge accuracy | {metrics['judge_accuracy']:.2%} |",
        f"| Mean judge score | {metrics['mean_judge_score']:.2f}/5 |",
    ]
    ragas = metrics.get("ragas", {})
    if "skipped" in ragas:
        lines.append(f"- Ragas: skipped ({ragas['skipped']})")
    elif "error" in ragas:
        lines.append(f"- Ragas error: {ragas['error']}")
    elif ragas:
        lines.append(f"- Ragas results: `{ragas}`")

    statistics = quality["statistics"]
    lines.extend([
        "",
        "## Data quality",
        "",
        "| Check | Result |",
        "| --- | ---: |",
        f"| Quality gate passed | {quality['success']} |",
        f"| Great Expectations passed | {quality['gx_success']} |",
        f"| Expectations passed | {statistics['successful_expectations']}/{statistics['evaluated_expectations']} |",
        "",
        "## Freshness SLA",
        "",
        f"- Latest publication: {freshness['latest_published']}",
        f"- Oldest publication: {freshness['oldest_published']}",
        f"- Stale rule: age_days > {freshness['threshold_days']}",
        f"- Stale records: {freshness['stale_rows']}/{freshness['total_rows']}",
        f"- Stale share: {freshness['stale_ratio']:.2%}",
        f"- Maximum allowed stale share: {freshness['max_stale_ratio']:.2%}",
        f"- Invalid age values: {freshness['invalid_age_rows']}",
        f"- Freshness passed: {freshness['is_fresh']}",
    ])
    write_text(report_path, "\n".join(lines) + "\n")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    baseline_quality: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    baseline_freshness: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    benchmark: dict[str, Any],
) -> None:
    """Report the measured baseline, corrupted, and repaired results."""
    from pathlib import Path

    from core.utils import write_text

    if Path(report_path).exists():
        raise FileExistsError(f"Comparison report already exists: {report_path}")

    metrics = (baseline_metrics, corrupted_metrics, repaired_metrics)
    qualities = (baseline_quality, corrupted_quality, repaired_quality)
    freshness = (baseline_freshness, corrupted_freshness, repaired_freshness)

    def row(label: str, values: tuple[str, str, str]) -> str:
        return f"| {label} | {' | '.join(values)} |"

    lines = [
        "# Baseline, corrupted, and repaired comparison",
        "",
        f"All three evaluations use the saved test set `{benchmark['test_set_path']}` "
        f"with {benchmark['question_count']} questions.",
        "",
        "| Measure | Baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
        row("Documents", tuple(str(item["total_rows"]) for item in freshness)),
        row("Evaluated questions", tuple(str(item["samples"]) for item in metrics)),
        row("Retrieval Hit Rate", tuple(f"{item['retrieval_hit_rate']:.2%}" for item in metrics)),
        row("Mean Token F1", tuple(f"{item['mean_token_f1']:.4f}" for item in metrics)),
        row("Judge accuracy", tuple(f"{item['judge_accuracy']:.2%}" for item in metrics)),
        row("Mean judge score / 5", tuple(f"{item['mean_judge_score']:.2f}" for item in metrics)),
        row("Quality gate passed", tuple(str(item["success"]) for item in qualities)),
        row("GX expectations passed", tuple(
            f"{item['statistics']['successful_expectations']}/{item['statistics']['evaluated_expectations']}"
            for item in qualities
        )),
        row("Stale papers", tuple(
            f"{item['stale_rows']}/{item['total_rows']} ({item['stale_ratio']:.2%})"
            for item in freshness
        )),
        row("Freshness SLA passed", tuple(str(item["is_fresh"]) for item in freshness)),
        "",
        "## Failed quality checks",
        "",
    ]
    for name, quality in zip(("Baseline", "Corrupted", "Repaired"), qualities, strict=True):
        failed = [
            result["expectation_config"]["type"]
            + (f" ({result['expectation_config']['kwargs']['column']})"
               if "column" in result["expectation_config"]["kwargs"] else "")
            for result in quality["results"] if not result["success"]
        ]
        lines.append(f"- {name}: {', '.join(failed) if failed else 'none'}")

    lines.extend([
        "",
        "## Repair and benchmark interpretation",
        "",
        "- Repaired clean records were checked against the saved baseline records and rebuilt twice from the raw snapshot.",
        "- Repaired answers and retrieved document IDs were checked again against the same collection and questions.",
    ])
    quoted = benchmark["quoted_doi_questions"]
    if quoted:
        lines.append(
            f"- {quoted}/{benchmark['question_count']} questions quote a DOI. The QA code gives an exact DOI match "
            "priority in retrieved results, so Hit Rate can remain high even when the corrupted corpus fails quality checks."
        )
    lines.append("- The table reports observed scores; it does not assume corruption lowered them or repair raised them.")
    write_text(report_path, "\n".join(lines) + "\n")
