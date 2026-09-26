from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import (
    now_utc,
    read_json,
    write_csv,
)

from evaluation.metrics import evaluate_pipeline

from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records

from observability.quality import (
    build_freshness_report,
    run_data_quality_checks,
)

from observability.reporting import (
    generate_corruption_report,
)

from pipelines.phase1 import main as run_phase1

from retrieval.index import LocalEmbeddingIndex


def _save_dataframe(df, csv_path, json_path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    write_csv(df, csv_path)

    df.to_json(
        json_path,
        orient="records",
        indent=2,
        force_ascii=False,
        date_format="iso",
    )


def main() -> None:
    settings = load_settings()

    print("=== DAY10 CORRUPTION / REPAIR FLOW ===")

    # ---------------------------------------------------------
    # 0. Ensure baseline exists
    # ---------------------------------------------------------
    required_baseline = [
        settings.paths.clean_json,
        settings.paths.baseline_metrics,
        settings.paths.eval_testset,
    ]

    if not all(path.exists() for path in required_baseline):
        print("Baseline artifacts missing. Running Phase 1...")
        run_phase1()

    baseline_metrics = read_json(
        settings.paths.baseline_metrics
    )

    clean_df = pd.read_json(
        settings.paths.clean_json
    )

    # ---------------------------------------------------------
    # 1. Corrupt dataset
    # ---------------------------------------------------------
    print("[1/7] Injecting data corruption...")

    corrupted_df = corrupt_clean_dataframe(
        clean_df,
        settings.paths.corruption_log,
    )

    _save_dataframe(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json,
    )

    print(
        f"Clean rows={len(clean_df)}, "
        f"corrupted rows={len(corrupted_df)}"
    )

    # ---------------------------------------------------------
    # 2. Build corrupted index
    # ---------------------------------------------------------
    print("[2/7] Building corrupted Chroma index...")

    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        settings.paths.corrupted_embeddings_json,
    )

    # ---------------------------------------------------------
    # 3. Evaluate corrupted
    # ---------------------------------------------------------
    print("[3/7] Evaluating corrupted dataset...")

    corrupted_eval = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )

    corrupted_quality = run_data_quality_checks(
        corrupted_df,
        settings,
        "corrupted",
    )

    corrupted_freshness_path = (
        settings.paths.quality_dir
        / "corrupted_freshness_report.json"
    )

    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        corrupted_freshness_path,
    )

    # ---------------------------------------------------------
    # 4. Repair FROM RAW
    # ---------------------------------------------------------
    print("[4/7] Repairing dataset from trusted raw snapshot...")

    raw_records = load_raw_records(
        settings.paths.raw_records_json
    )

    repaired_df = build_clean_dataframe(
        raw_records,
        now_utc(),
    )

    _save_dataframe(
        repaired_df,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
    )

    # ---------------------------------------------------------
    # 5. Build repaired index
    # ---------------------------------------------------------
    print("[5/7] Building repaired Chroma index...")

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        settings.paths.repaired_embeddings_json,
    )

    # ---------------------------------------------------------
    # 6. Evaluate repaired
    # ---------------------------------------------------------
    print("[6/7] Evaluating repaired dataset...")

    repaired_eval = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )

    repaired_quality = run_data_quality_checks(
        repaired_df,
        settings,
        "repaired",
    )

    repaired_freshness_path = (
        settings.paths.quality_dir
        / "repaired_freshness_report.json"
    )

    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        repaired_freshness_path,
    )

    # ---------------------------------------------------------
    # 7. Comparison report
    # ---------------------------------------------------------
    print("[7/7] Generating comparison report...")

    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print()
    print("=== COMPARISON ===")

    print(
        "Baseline : "
        f"HitRate={baseline_metrics['retrieval_hit_rate']:.4f} | "
        f"F1={baseline_metrics['mean_token_f1']:.4f}"
    )

    print(
        "Corrupted: "
        f"HitRate={corrupted_eval.summary['retrieval_hit_rate']:.4f} | "
        f"F1={corrupted_eval.summary['mean_token_f1']:.4f}"
    )

    print(
        "Repaired : "
        f"HitRate={repaired_eval.summary['retrieval_hit_rate']:.4f} | "
        f"F1={repaired_eval.summary['mean_token_f1']:.4f}"
    )

    print()
    print(
        f"Report: {settings.paths.comparison_report}"
    )


if __name__ == "__main__":
    main()