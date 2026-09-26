from __future__ import annotations

import json

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _save_dataframe(df, csv_path, json_path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, json.loads(df.to_json(orient="records")))


def _print_comparison(baseline: dict, corrupted: dict, repaired: dict) -> None:
    keys = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
    print("\nBaseline vs Corrupted vs Repaired")
    print(f"{'metric':<22} {'baseline':>12} {'corrupted':>12} {'repaired':>12}")
    for key in keys:
        print(
            f"{key:<22} {float(baseline.get(key, 0)):12.4f} "
            f"{float(corrupted.get(key, 0)):12.4f} {float(repaired.get(key, 0)):12.4f}"
        )


def main() -> None:
    settings = load_settings()

    if not settings.paths.clean_json.exists() or not settings.paths.baseline_metrics.exists():
        from pipelines.phase1 import main as run_phase1

        run_phase1()

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)

    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    _save_dataframe(corrupted_df, settings.paths.corrupted_clean_csv, settings.paths.corrupted_clean_json)

    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, settings.paths.corrupted_embeddings_json
    )
    corrupted_eval = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        settings.paths.quality_dir / "corrupted_freshness_report.json",
    )

    records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(records, now_utc())
    _save_dataframe(repaired_df, settings.paths.repaired_clean_csv, settings.paths.repaired_clean_json)

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, settings.paths.repaired_embeddings_json
    )
    repaired_eval = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        settings.paths.quality_dir / "repaired_freshness_report.json",
    )

    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    _print_comparison(baseline_metrics, corrupted_eval.summary, repaired_eval.summary)
    print(f"Corrupted GX success: {corrupted_quality['success']} | is_fresh={corrupted_freshness['is_fresh']}")
    print(f"Repaired GX success: {repaired_quality['success']} | is_fresh={repaired_freshness['is_fresh']}")
    print(f"Report: {settings.paths.comparison_report}")
