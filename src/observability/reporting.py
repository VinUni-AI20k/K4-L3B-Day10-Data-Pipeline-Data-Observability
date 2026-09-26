from __future__ import annotations

from typing import Any


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    content = f"""# Phase 1: Baseline Report

## Source Summary
- Source: {source_summary.get('source', 'Unknown')}
- Total Records: {source_summary.get('total_records', 0)}

## Evaluation Metrics
- Samples: {metrics.get('samples', 0)}
- Hit Rate: {metrics.get('retrieval_hit_rate', 0.0):.4f}
- Mean Token F1: {metrics.get('mean_token_f1', 0.0):.4f}
- Mean Judge Score: {metrics.get('mean_judge_score', 0.0):.4f}
- Judge Accuracy: {metrics.get('judge_accuracy', 0.0):.4f}

## Data Quality
- Success: {quality.get('success', False)}

## Freshness
- Is Fresh: {freshness.get('is_fresh', False)}
- Stale Rows: {freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)}
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)


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
    content = f"""# Corruption & Repair Comparison Report

## Evaluation Metrics
| Metric | Baseline | Corrupted | Repaired |
|--------|----------|-----------|----------|
| Hit Rate | {baseline_metrics.get('retrieval_hit_rate', 0.0):.4f} | {corrupted_metrics.get('retrieval_hit_rate', 0.0):.4f} | {repaired_metrics.get('retrieval_hit_rate', 0.0):.4f} |
| Token F1 | {baseline_metrics.get('mean_token_f1', 0.0):.4f} | {corrupted_metrics.get('mean_token_f1', 0.0):.4f} | {repaired_metrics.get('mean_token_f1', 0.0):.4f} |
| Judge Score | {baseline_metrics.get('mean_judge_score', 0.0):.4f} | {corrupted_metrics.get('mean_judge_score', 0.0):.4f} | {repaired_metrics.get('mean_judge_score', 0.0):.4f} |

## Data Quality (Success)
- Corrupted: {corrupted_quality.get('success', False)}
- Repaired: {repaired_quality.get('success', False)}

## Freshness (Stale / Total)
- Corrupted: {corrupted_freshness.get('stale_rows', 0)} / {corrupted_freshness.get('total_rows', 0)} ({corrupted_freshness.get('is_fresh', False)})
- Repaired: {repaired_freshness.get('stale_rows', 0)} / {repaired_freshness.get('total_rows', 0)} ({repaired_freshness.get('is_fresh', False)})
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
