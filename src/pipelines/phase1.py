from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from core.config import load_settings
from core.utils import now_utc, write_csv
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Execute Phase 1 Baseline Pipeline end-to-end:
    Ingestion -> Cleaning -> Vector Indexing -> Test Set -> Evaluation -> Data Quality & Freshness -> Report.
    """
    print("=== STARTING PHASE 1 BASELINE PIPELINE ===")
    settings = load_settings()

    # 1. Fetch raw records
    print("[1/7] Fetching raw records from Crossref (with local fallback)...")
    records = fetch_source_records(settings)
    print(f"      Fetched {len(records)} raw paper records.")

    # 2. Clean records
    print("[2/7] Cleaning records and creating embedding text...")
    df_clean = build_clean_dataframe(records, now_utc())
    settings.paths.clean_json.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_json(settings.paths.clean_json, orient="records", indent=2)
    write_csv(df_clean, settings.paths.clean_csv)
    print(f"      Cleaned {len(df_clean)} records saved to {settings.paths.clean_json.name}.")

    # 3. Build ChromaDB Vector Index
    print(f"[3/7] Building ChromaDB collection '{settings.baseline_collection_name}' with MiniLM embeddings...")
    index = LocalEmbeddingIndex.build(df_clean, settings, settings.paths.embeddings_json)
    print(f"      Indexed {len(index.documents)} documents into ChromaDB.")

    # 4. Build Evaluation Test Set
    print("[4/7] Generating evaluation test set (10 questions across 4 domains)...")
    test_set = build_test_set(df_clean, settings.paths.eval_testset)
    print(f"      Generated {len(test_set)} test questions in {settings.paths.eval_testset.name}.")

    # 5. Evaluate Retrieval & QA Pipeline
    print("[5/7] Evaluating baseline RAG pipeline metrics...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    hit_rate = eval_bundle.summary.get("retrieval_hit_rate", 0.0)
    token_f1 = eval_bundle.summary.get("mean_token_f1", 0.0)
    print(f"      Baseline Hit Rate: {hit_rate * 100:.1f}%, Mean Token F1: {token_f1 * 100:.1f}%.")

    # 6. Data Observability (GX 1.x & Freshness SLA)
    print("[6/7] Running Great Expectations 1.x quality checks and Freshness SLA...")
    quality = run_data_quality_checks(df_clean, settings, "baseline")
    freshness = build_freshness_report(df_clean, settings, settings.paths.freshness_report)
    print(f"      Quality Gate Success: {quality.get('success', False)}, Is Fresh: {freshness.get('is_fresh', False)}.")

    # 7. Generate Phase 1 Report
    print("[7/7] Generating Phase 1 markdown report...")
    source_summary = {
        "source_api": settings.source_api,
        "raw_count": len(records),
        "clean_count": len(df_clean),
        "collection_name": settings.baseline_collection_name,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=eval_bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"      Report generated at {settings.paths.baseline_report.name}.")
    print("=== PHASE 1 BASELINE PIPELINE COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
