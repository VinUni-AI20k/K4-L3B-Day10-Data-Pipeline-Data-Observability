from __future__ import annotations

from datetime import datetime, timezone

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from evaluation.testset import build_test_set
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline


def main() -> None:
    """Baseline pipeline end-to-end:
    1. Load settings
    2. Load or fetch raw records
    3. Clean data
    4. Save clean CSV/JSON
    5. Build ChromaDB index
    6. Create or load evaluation set
    7. Evaluate (retrieval + answer quality)
    8. Run quality checks & freshness report
    9. Generate markdown report
    """
    print("=" * 60)
    print("PHASE 1 — Baseline Pipeline")
    print("=" * 60)

    # 1. Settings
    settings = load_settings()
    run_date: datetime = now_utc()

    # 2. Load raw records (fallback to local snapshot)
    print("\n[1/8] Loading raw records...")
    raw_records_path = settings.paths.raw_records_json
    if raw_records_path.exists():
        records = load_raw_records(raw_records_path)
    else:
        records = fetch_source_records(settings)
    print(f"      Loaded {len(records)} raw records.")

    # 3. Clean
    print("\n[2/8] Cleaning data...")
    df = build_clean_dataframe(records, run_date)
    print(f"      Clean dataframe: {len(df)} rows.")

    # 4. Save clean artifacts
    print("\n[3/8] Saving clean artifacts...")
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(df, settings.paths.clean_csv)
    df.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=True)
    print(f"      Saved: {settings.paths.clean_csv}")
    print(f"      Saved: {settings.paths.clean_json}")

    # 5. Build ChromaDB index
    print("\n[4/8] Building ChromaDB index (baseline)...")
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"      Indexed {len(index.documents)} documents into '{settings.baseline_collection_name}'.")

    # 6. Evaluation test set
    print("\n[5/8] Building evaluation test set...")
    eval_path = settings.paths.eval_testset
    if eval_path.exists() and not settings.refresh_test_set:
        print(f"      Reusing existing test set: {eval_path}")
    else:
        test_items = build_test_set(df, eval_path)
        print(f"      Generated {len(test_items)} test questions → {eval_path}")

    # 7. Evaluate baseline
    print("\n[6/8] Running baseline evaluation...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=eval_path,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    m = bundle.summary
    print(f"      retrieval_hit_rate : {m['retrieval_hit_rate']:.3f}")
    print(f"      mean_token_f1      : {m['mean_token_f1']:.3f}")
    print(f"      judge_accuracy     : {m['judge_accuracy']:.3f}")
    print(f"      Saved: {settings.paths.baseline_metrics}")

    # 8. Quality & freshness
    print("\n[7/8] Running data quality checks...")
    quality_result = run_data_quality_checks(df, settings, "baseline_quality_report")
    freshness_result = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f"      Quality gate passed: {quality_result.get('success', False)}")
    print(f"      Freshness is_fresh : {freshness_result.get('is_fresh', False)}")

    # 9. Phase 1 markdown report
    print("\n[8/8] Generating phase 1 report...")
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "total_records": len(records),
        "clean_records": len(df),
        "run_date": run_date.isoformat(),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=m,
        quality=quality_result,
        freshness=freshness_result,
    )
    print(f"      Report saved: {settings.paths.baseline_report}")

    print("\n" + "=" * 60)
    print("Phase 1 complete.")
    print(f"  baseline_metrics  : {settings.paths.baseline_metrics}")
    print(f"  phase1_report     : {settings.paths.baseline_report}")
    print("=" * 60)
