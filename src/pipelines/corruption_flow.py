from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json, write_csv, write_text
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.embeddings import build_embeddings
from retrieval.index import LocalEmbeddingIndex


def repair_from_raw_snapshot(settings: Settings) -> pd.DataFrame:
    """Rebuild the clean dataset from the immutable raw snapshot.

    This is idempotent: every invocation overwrites the repaired artifacts with
    the same transformation of the trusted source data.
    """
    records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(records, run_date=datetime.now(UTC))
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    settings.paths.repaired_clean_json.parent.mkdir(parents=True, exist_ok=True)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    return repaired_df


def _load_clean_dataframe(settings: Settings) -> pd.DataFrame:
    if settings.paths.clean_csv.exists():
        return pd.read_csv(settings.paths.clean_csv)
    if settings.paths.clean_json.exists():
        return pd.read_json(settings.paths.clean_json)
    raise FileNotFoundError(
        "Missing clean baseline data. Run `python script/run_phase1.py` before the corruption flow."
    )


def _write_comparison_report(
    report_path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write a standalone three-state report from metrics generated this run."""
    states = (baseline_metrics, corrupted_metrics, repaired_metrics)
    metric_rows = (
        ("Retrieval Hit Rate", "retrieval_hit_rate", ".4f"),
        ("Mean Token F1", "mean_token_f1", ".4f"),
        ("Judge Accuracy", "judge_accuracy", ".4f"),
        ("Mean Judge Score", "mean_judge_score", ".2f"),
    )
    lines = [
        "# Data Corruption, Repair & Recovery Report",
        "",
        "## Performance Comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "| :--- | ---: | ---: | ---: |",
    ]
    for label, key, format_spec in metric_rows:
        values = [float(metrics.get(key, 0.0)) for metrics in states]
        lines.append(f"| {label} | " + " | ".join(format(value, format_spec) for value in values) + " |")
    lines.extend(
        [
            "",
            "## Data Quality and Freshness",
            "",
            "| Check | Corrupted | Repaired |",
            "| :--- | :--- | :--- |",
            f"| Quality Gate | {'PASS' if corrupted_quality.get('success') else 'FAIL'} | {'PASS' if repaired_quality.get('success') else 'FAIL'} |",
            f"| Freshness SLA | {'FRESH' if corrupted_freshness.get('is_fresh') else 'STALE'} | {'FRESH' if repaired_freshness.get('is_fresh') else 'STALE'} |",
            f"| Stale rows | {corrupted_freshness.get('stale_rows', 0)}/{corrupted_freshness.get('total_rows', 0)} | {repaired_freshness.get('stale_rows', 0)}/{repaired_freshness.get('total_rows', 0)} |",
            "",
            "## Recovery Evidence",
            "",
            "The repaired dataset was regenerated from `data/raw/crossref_records.json`, then re-indexed in a separate ChromaDB collection.",
        ]
    )
    write_text(report_path, "\n".join(lines) + "\n")


def _print_comparison(baseline: dict[str, Any], corrupted: dict[str, Any], repaired: dict[str, Any]) -> None:
    print("\n" + "=" * 72)
    print("PERFORMANCE COMPARISON: BASELINE vs CORRUPTED vs REPAIRED")
    print("=" * 72)
    print(f"{'Metric':<24} {'Baseline':>14} {'Corrupted':>14} {'Repaired':>14}")
    print("-" * 72)
    for label, key in (
        ("Retrieval Hit Rate", "retrieval_hit_rate"),
        ("Mean Token F1", "mean_token_f1"),
        ("Judge Accuracy", "judge_accuracy"),
        ("Mean Judge Score", "mean_judge_score"),
    ):
        print(
            f"{label:<24} {float(baseline.get(key, 0.0)):>14.4f} "
            f"{float(corrupted.get(key, 0.0)):>14.4f} {float(repaired.get(key, 0.0)):>14.4f}"
        )
    print("=" * 72)


def run_corruption_flow_pipeline(settings: Settings) -> dict[str, Any]:
    """Evaluate baseline, corrupted, and repaired RAG states end to end."""
    if not settings.paths.baseline_metrics.exists():
        raise FileNotFoundError("Missing baseline metrics. Run `python script/run_phase1.py` first.")
    if not settings.paths.eval_testset.exists():
        raise FileNotFoundError("Missing evaluation test set. Run `python script/run_phase1.py` first.")

    print("=" * 72)
    print("STARTING DATA CORRUPTION -> REPAIR -> RECOVERY FLOW")
    print("=" * 72)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = _load_clean_dataframe(settings)

    print("\n[1/5] Injecting synthetic corruption into the clean dataset...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    settings.paths.corrupted_clean_json.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    print(f"  Corrupted dataset saved: {len(corrupted_df)} rows")

    print("\n[2/5] Indexing and evaluating corrupted data (Silent Failure measurement)...")
    embedder = build_embeddings(settings)
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
        embedding_model=embedder,
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name="corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, report_path=settings.paths.quality_dir / "corrupted_freshness_report.json"
    )

    print("\n[3/5] Repairing from the trusted raw snapshot...")
    repaired_df = repair_from_raw_snapshot(settings)
    print(f"  Repaired dataset saved: {len(repaired_df)} rows")

    print("\n[4/5] Re-indexing and re-evaluating repaired data...")
    repaired_index = LocalEmbeddingIndex.build(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
        embedding_model=embedder,
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name="repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, report_path=settings.paths.quality_dir / "repaired_freshness_report.json"
    )

    print("\n[5/5] Writing the three-state comparison report...")
    _write_comparison_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    _print_comparison(baseline_metrics, corrupted_bundle.summary, repaired_bundle.summary)
    print(f"Report written to: {settings.paths.comparison_report}")

    return {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_bundle.summary,
        "repaired_metrics": repaired_bundle.summary,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
        "report_path": str(settings.paths.comparison_report),
    }


def main() -> None:
    run_corruption_flow_pipeline(load_settings())
