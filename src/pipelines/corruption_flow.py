from __future__ import annotations

import sys
import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def run_corruption_flow_pipeline(settings: Settings) -> None:
    """Execute synthetic corruption testing, evaluation, idempotent repair, and 3-state reporting."""
    if getattr(sys.stdout, "encoding", None) and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print("🚀 Running Corruption & Recovery Flow...")

    print("📖 1. Loading baseline metrics and clean dataset...")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    df_clean = pd.read_json(settings.paths.clean_json)

    print("💥 2. Injecting 6 corruption scenarios into clean dataset...")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, df_corrupted.to_dict(orient="records"))
    print(f"   -> Corrupted dataframe saved: {len(df_corrupted)} rows (Log: {settings.paths.corruption_log})")

    print("🔍 3. Indexing corrupted dataset into ChromaDB...")
    corrupted_index = LocalEmbeddingIndex.build(df_corrupted, settings, settings.paths.corrupted_embeddings_json)

    print("📊 4. Evaluating corrupted RAG pipeline performance...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(f"   -> Corrupted Hit Rate: {corrupted_bundle.summary['retrieval_hit_rate']:.2%}")

    print("🛡️ 5. Running Quality Gate & Freshness SLA on corrupted dataset...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        df_corrupted, settings, settings.paths.quality_dir / "corrupted_freshness_report.json"
    )
    print(f"   -> Quality Gate Status: {corrupted_quality['success']}, Freshness SLA: {corrupted_freshness['is_fresh']}")

    print("🔧 6. Triggering Idempotent Repair from raw records snapshot...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, now_utc())
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, df_repaired.to_dict(orient="records"))
    print(f"   -> Repaired dataset restored: {len(df_repaired)} rows.")

    print("🔍 7. Indexing repaired dataset into ChromaDB...")
    repaired_index = LocalEmbeddingIndex.build(df_repaired, settings, settings.paths.repaired_embeddings_json)

    print("📊 8. Evaluating repaired RAG pipeline performance...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    print(f"   -> Repaired Hit Rate: {repaired_bundle.summary['retrieval_hit_rate']:.2%}")

    print("🛡️ 9. Running Quality Gate & Freshness SLA on repaired dataset...")
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(
        df_repaired, settings, settings.paths.quality_dir / "repaired_freshness_report.json"
    )

    print("📝 10. Generating 3-State Comparison Report (Baseline vs Corrupted vs Repaired)...")
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
    print(f"   -> Report generated at: {settings.paths.comparison_report}")
    print("✅ Corruption & Recovery Flow completed successfully!")


def main() -> None:
    settings = load_settings()
    run_corruption_flow_pipeline(settings)


if __name__ == "__main__":
    main()

