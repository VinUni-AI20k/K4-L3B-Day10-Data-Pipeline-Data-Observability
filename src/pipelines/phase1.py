from __future__ import annotations

import sys

from core.config import Settings, load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(settings: Settings) -> None:
    """Execute end-to-end Phase 1 baseline data pipeline, indexing, evaluation, and observability reporting."""
    if getattr(sys.stdout, "encoding", None) and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print("🚀 Running Phase 1 Baseline Pipeline...")

    print("📥 1. Ingest: Fetching raw records from Crossref API / Snapshot...")
    records = fetch_source_records(settings)
    print(f"   -> Loaded {len(records)} raw paper records.")

    print("🧹 2. Clean: Building clean dataframe...")
    df_clean = build_clean_dataframe(records, now_utc())
    write_csv(df_clean, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df_clean.to_dict(orient="records"))
    print(f"   -> Cleaned dataframe saved to {settings.paths.clean_csv} ({len(df_clean)} rows).")

    print("🔍 3. Index ChromaDB: Building Vector Store Index...")
    index = LocalEmbeddingIndex.build(df_clean, settings, settings.paths.embeddings_json)
    print(f"   -> Collection '{index.collection_name}' built with {len(index.documents)} documents.")

    print("🧪 4. Sinh Testset: Generating benchmark evaluation set...")
    test_set = build_test_set(df_clean, settings.paths.eval_testset)
    print(f"   -> Generated {len(test_set)} test questions at {settings.paths.eval_testset}.")

    print("📊 5. Đánh giá Baseline RAG: Measuring Hit Rate & Token F1...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    hit_rate = eval_bundle.summary["retrieval_hit_rate"]
    token_f1 = eval_bundle.summary["mean_token_f1"]
    print(f"   -> Hit Rate: {hit_rate:.2%}, Mean Token F1: {token_f1:.4f}")
    print(f"   -> Baseline metrics saved to {settings.paths.baseline_metrics}")

    print("🛡️ 6. Observability Gate: Great Expectations Quality Gate & Freshness SLA...")
    quality_res = run_data_quality_checks(df_clean, settings, "baseline")
    freshness_res = build_freshness_report(df_clean, settings, settings.paths.freshness_report)
    print(f"   -> Quality Gate Status: {quality_res['success']}, Freshness SLA Status: {freshness_res['is_fresh']}")

    print("📝 Xuất báo cáo Phase 1 Report...")
    source_summary = {"source_api": settings.source_api, "total_records": len(records)}
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=eval_bundle.summary,
        quality=quality_res,
        freshness=freshness_res,
    )
    print(f"   -> Report generated at: {settings.paths.baseline_report}")
    print("✅ Phase 1 Baseline Pipeline completed successfully!")


def main() -> None:
    settings = load_settings()
    run_phase1_pipeline(settings)


if __name__ == "__main__":
    main()
