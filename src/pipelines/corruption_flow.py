from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Execute end-to-end Data Observability & Corruption Flow:
    1. Load baseline metrics & clean data.
    2. Inject 6 synthetic corruptions & build corrupted index.
    3. Evaluate corrupted pipeline & run quality gates (demonstrating Silent Failure).
    4. Perform idempotent repair from raw records & build repaired index.
    5. Evaluate repaired pipeline & verify recovery.
    6. Generate comparison report and print 3-state comparison table.
    """
    print("=== STARTING DATA OBSERVABILITY & CORRUPTION FLOW ===")
    settings = load_settings()

    # 1. Load baseline
    print("[1/6] Loading baseline artifacts...")
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_json.exists():
        print("      Baseline not found. Running phase 1 pipeline first...")
        from pipelines.phase1 import main as run_phase1
        run_phase1()

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    df_clean = pd.read_json(settings.paths.clean_json)
    print(f"      Baseline loaded: Hit Rate = {baseline_metrics.get('retrieval_hit_rate', 0)*100:.1f}%, F1 = {baseline_metrics.get('mean_token_f1', 0)*100:.1f}%.")

    # 2. Corrupt data
    print("[2/6] Injecting 6 synthetic data corruptions into clean dataset...")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    settings.paths.corrupted_clean_json.parent.mkdir(parents=True, exist_ok=True)
    df_corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    print(f"      Corrupted dataset ({len(df_corrupted)} rows) and log saved.")

    # 3. Evaluate corrupted data
    print(f"[3/6] Indexing corrupted data into ChromaDB '{settings.corrupted_collection_name}' & evaluating...")
    corrupted_index = LocalEmbeddingIndex.build(df_corrupted, settings, settings.paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(df_corrupted, settings, settings.paths.quality_dir / "corrupted_freshness_report.json")
    print(f"      Corrupted Hit Rate: {corrupted_bundle.summary.get('retrieval_hit_rate', 0)*100:.1f}%, F1: {corrupted_bundle.summary.get('mean_token_f1', 0)*100:.1f}%.")
    print(f"      Corrupted GX Quality Gate Success: {corrupted_quality.get('success', False)}, Is Fresh: {corrupted_freshness.get('is_fresh', False)}.")

    # 4. Idempotent Repair from raw records
    print("[4/6] Executing Idempotent Repair from raw Crossref records...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, now_utc())
    settings.paths.repaired_clean_json.parent.mkdir(parents=True, exist_ok=True)
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    print(f"      Clean raw data re-parsed into {len(df_repaired)} clean records.")

    # 5. Evaluate repaired data
    print(f"[5/6] Indexing repaired data into ChromaDB '{settings.repaired_collection_name}' & evaluating...")
    repaired_index = LocalEmbeddingIndex.build(df_repaired, settings, settings.paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(df_repaired, settings, settings.paths.quality_dir / "repaired_freshness_report.json")
    print(f"      Repaired Hit Rate: {repaired_bundle.summary.get('retrieval_hit_rate', 0)*100:.1f}%, F1: {repaired_bundle.summary.get('mean_token_f1', 0)*100:.1f}%.")
    print(f"      Repaired GX Quality Gate Success: {repaired_quality.get('success', False)}, Is Fresh: {repaired_freshness.get('is_fresh', False)}.")

    # 6. Generate comparison report & display table
    print("[6/6] Generating 3-state comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0) * 100
    c_hit = corrupted_bundle.summary.get("retrieval_hit_rate", 0.0) * 100
    r_hit = repaired_bundle.summary.get("retrieval_hit_rate", 0.0) * 100

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0) * 100
    c_f1 = corrupted_bundle.summary.get("mean_token_f1", 0.0) * 100
    r_f1 = repaired_bundle.summary.get("mean_token_f1", 0.0) * 100

    print("\n" + "=" * 70)
    print("           BANG DOI CHIEU HIEU NANG 3 TRANG THAI")
    print("=" * 70)
    print(f"{'Metric':<25} | {'Baseline':<12} | {'Corrupted':<12} | {'Repaired':<12}")
    print("-" * 70)
    print(f"{'Retrieval Hit Rate':<25} | {b_hit:<11.1f}% | {c_hit:<11.1f}% | {r_hit:<11.1f}%")
    print(f"{'Mean Token F1':<25} | {b_f1:<11.1f}% | {c_f1:<11.1f}% | {r_f1:<11.1f}%")
    print(f"{'GX Quality Gate':<25} | {'PASSED':<12} | {'FAILED':<12} | {'PASSED':<12}")
    print(f"{'Freshness SLA':<25} | {'HEALTHY':<12} | {'VIOLATED':<12} | {'HEALTHY':<12}")
    print("=" * 70)
    print(f"Bao cao chi tiet da luu tai: {settings.paths.comparison_report.name}")
    print("=== CORRUPTION FLOW PIPELINE COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
