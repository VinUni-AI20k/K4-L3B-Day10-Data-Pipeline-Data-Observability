from __future__ import annotations

from typing import Any

from core.utils import write_text


def _number(value: Any, digits: int = 4) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}" if isinstance(value, float) else str(value)
    return str(value)


def _status(value: Any) -> str:
    return "PASS" if bool(value) else "FAIL"


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline source, evaluation and observability evidence."""
    expectation_rows = []
    for result in quality.get("results", []):
        details = result.get("result", {}) or {}
        observed = details.get("observed_value", details.get("element_count", "N/A"))
        unexpected = details.get("unexpected_count", 0)
        expectation_rows.append(
            f"| `{result.get('expectation_type', 'unknown')}` | "
            f"{_status(result.get('success'))} | {_number(observed)} | {_number(unexpected)} |"
        )
    if not expectation_rows:
        expectation_rows.append("| N/A | FAIL | N/A | N/A |")

    ragas = metrics.get("ragas", {})
    if isinstance(ragas, dict) and "skipped" in ragas:
        ragas_status = str(ragas["skipped"])
    elif isinstance(ragas, dict) and "error" in ragas:
        ragas_status = str(ragas["error"])
    else:
        ragas_status = "Completed"

    artifact_rows = []
    for name, path in source_summary.get("artifacts", {}).items():
        artifact_rows.append(f"| {name} | `{path}` |")
    if not artifact_rows:
        artifact_rows.append("| N/A | N/A |")

    report = f"""# Phase 1 — Baseline Pipeline Report

Generated at: {source_summary.get('generated_at', 'N/A')}

## Data source and corpus

| Signal | Value |
| --- | --- |
| Source | {source_summary.get('source_api', 'N/A')} |
| Query | {source_summary.get('source_query', 'N/A')} |
| Filter | {source_summary.get('source_filter', 'N/A')} |
| Raw records | {_number(source_summary.get('raw_records', 0))} |
| Clean records | {_number(source_summary.get('clean_records', 0))} |
| Chroma collection | `{source_summary.get('collection_name', 'N/A')}` |
| Embedding model | `{source_summary.get('embedding_model', 'N/A')}` |
| Benchmark questions | {_number(source_summary.get('test_questions', 0))} |

## Baseline RAG evaluation

| Metric | Value |
| --- | ---: |
| Samples | {_number(metrics.get('samples', 0))} |
| Retrieval hit rate | {_number(metrics.get('retrieval_hit_rate', 0.0))} |
| Mean token F1 | {_number(metrics.get('mean_token_f1', 0.0))} |
| Judge accuracy | {_number(metrics.get('judge_accuracy', 0.0))} |
| Mean judge score | {_number(metrics.get('mean_judge_score', 0.0))} |
| Ragas | {ragas_status} |

## Data quality gate

| Signal | Value |
| --- | --- |
| Overall gate | {_status(quality.get('success'))} |
| Great Expectations | {_status(quality.get('gx_success'))} |
| Expectations evaluated | {_number(quality.get('expectations_count', 0))} |

### Expectation details

| Expectation | Status | Observed/element count | Unexpected count |
| --- | --- | ---: | ---: |
{chr(10).join(expectation_rows)}

## Freshness monitoring

| Signal | Value |
| --- | ---: |
| Status | {_status(freshness.get('is_fresh'))} |
| Latest published | {freshness.get('latest_published', 'N/A')} |
| Oldest published | {freshness.get('oldest_published', 'N/A')} |
| Stale threshold (days) | {_number(freshness.get('threshold_days', 0))} |
| Stale rows | {_number(freshness.get('stale_rows', 0))} |
| Total rows | {_number(freshness.get('total_rows', 0))} |
| Stale ratio | {_number(freshness.get('stale_ratio', 0.0))} |

## Artifacts

| Artifact | Path |
| --- | --- |
{chr(10).join(artifact_rows)}

## Baseline conclusion

The baseline corpus passed the data quality gate and freshness SLA: **{_status(quality.get('success'))}**.
Retrieval hit rate is **{_number(metrics.get('retrieval_hit_rate', 0.0))}** and mean token F1 is **{_number(metrics.get('mean_token_f1', 0.0))}** across **{_number(metrics.get('samples', 0))}** benchmark questions.
"""
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
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
