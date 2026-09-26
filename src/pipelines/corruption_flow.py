from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline


def main() -> None:
    """Corruption → evaluate → repair → compare flow:
    1.  Load baseline metrics + clean dataset
    2.  Corrupt the clean dataframe
    3.  Save corrupted artifacts & build corrupted index
    4.  Run quality checks on corrupted data
    5.  Evaluate corrupted pipeline
    6.  Repair from raw records (idempotent)
    7.  Save repaired artifacts & build repaired index
    8.  Run quality checks on repaired data
    9.  Evaluate repaired pipeline
    10. Generate comparison report
    """
    print("=" * 60)
    print("CORRUPTION FLOW — Corrupt → Evaluate → Repair → Compare")
    print("=" * 60)

    settings = load_settings()
    run_date = now_utc()
    eval_path = settings.paths.eval_testset

    # ── 1. Load baseline ────────────────────────────────────────────
    print("\n[1/10] Loading baseline artifacts...")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    df_clean = pd.read_json(settings.paths.clean_json)
    print(f"       Baseline rows: {len(df_clean)}")
    print(f"       Baseline hit_rate : {baseline_metrics['retrieval_hit_rate']:.3f}")

    # ── 2. Corrupt ──────────────────────────────────────────────────
    print("\n[2/10] Injecting synthetic corruption...")
    df_corrupted = corrupt_clean_dataframe(df_clean.copy(), settings.paths.corruption_log)
    print(f"       Corrupted rows: {len(df_corrupted)}")

    # ── 3. Save corrupted artifacts ─────────────────────────────────
    print("\n[3/10] Saving corrupted artifacts...")
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    df_corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2, force_ascii=True)

    print("       Building corrupted ChromaDB index...")
    corrupted_index = LocalEmbeddingIndex.build(
        df=df_corrupted,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    print(f"       Indexed {len(corrupted_index.documents)} corrupted docs into '{settings.corrupted_collection_name}'.")

    # ── 4. Quality checks on corrupted data ─────────────────────────
    print("\n[4/10] Running quality checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted_quality_report")
    corrupted_freshness = build_freshness_report(df_corrupted, settings, settings.paths.corrupted_quality_report)
    print(f"       Quality gate passed: {corrupted_quality.get('success', False)}")
    print(f"       Freshness is_fresh : {corrupted_freshness.get('is_fresh', False)}")

    # ── 5. Evaluate corrupted ────────────────────────────────────────
    print("\n[5/10] Evaluating corrupted pipeline...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=eval_path,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    cm = corrupted_bundle.summary
    print(f"       retrieval_hit_rate : {cm['retrieval_hit_rate']:.3f}  (baseline: {baseline_metrics['retrieval_hit_rate']:.3f})")
    print(f"       mean_token_f1      : {cm['mean_token_f1']:.3f}  (baseline: {baseline_metrics['mean_token_f1']:.3f})")

    # ── 6. Repair from raw records (idempotent) ──────────────────────
    print("\n[6/10] Repairing from raw records (idempotent)...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, run_date)
    print(f"       Repaired rows: {len(df_repaired)}")

    # ── 7. Save repaired artifacts ───────────────────────────────────
    print("\n[7/10] Saving repaired artifacts...")
    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=True)

    print("       Building repaired ChromaDB index...")
    repaired_index = LocalEmbeddingIndex.build(
        df=df_repaired,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    print(f"       Indexed {len(repaired_index.documents)} repaired docs into '{settings.repaired_collection_name}'.")

    # ── 8. Quality checks on repaired data ──────────────────────────
    print("\n[8/10] Running quality checks on repaired data...")
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired_quality_report")
    repaired_freshness = build_freshness_report(df_repaired, settings, settings.paths.freshness_report)
    print(f"       Quality gate passed: {repaired_quality.get('success', False)}")
    print(f"       Freshness is_fresh : {repaired_freshness.get('is_fresh', False)}")

    # ── 9. Evaluate repaired ─────────────────────────────────────────
    print("\n[9/10] Evaluating repaired pipeline...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=eval_path,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    rm = repaired_bundle.summary
    print(f"       retrieval_hit_rate : {rm['retrieval_hit_rate']:.3f}  (baseline: {baseline_metrics['retrieval_hit_rate']:.3f})")
    print(f"       mean_token_f1      : {rm['mean_token_f1']:.3f}  (baseline: {baseline_metrics['mean_token_f1']:.3f})")

    # ── 10. Comparison report ────────────────────────────────────────
    print("\n[10/10] Generating comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=cm,
        repaired_metrics=rm,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"        Report saved: {settings.paths.comparison_report}")

    # ── Summary table ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("COMPARISON: Baseline vs Corrupted vs Repaired")
    print("=" * 60)
    print(f"{'Metric':<25} {'Baseline':>10} {'Corrupted':>10} {'Repaired':>10}")
    print("-" * 60)
    print(f"{'retrieval_hit_rate':<25} {baseline_metrics['retrieval_hit_rate']:>10.3f} {cm['retrieval_hit_rate']:>10.3f} {rm['retrieval_hit_rate']:>10.3f}")
    print(f"{'mean_token_f1':<25} {baseline_metrics['mean_token_f1']:>10.3f} {cm['mean_token_f1']:>10.3f} {rm['mean_token_f1']:>10.3f}")
    print(f"{'judge_accuracy':<25} {baseline_metrics['judge_accuracy']:>10.3f} {cm['judge_accuracy']:>10.3f} {rm['judge_accuracy']:>10.3f}")
    print("=" * 60)
    print(f"\nAll artifacts saved to: {settings.paths.comparison_report.parent}")
