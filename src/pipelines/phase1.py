from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(settings) -> dict:
    # 1. Ingest raw records (fetch or reuse existing raw snapshot).
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    # 2. Clean data.
    run_date = now_utc()
    df = build_clean_dataframe(records, run_date)
    if df.empty:
        raise RuntimeError("Cleaning pipeline produced an empty dataset; check source records.")

    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))

    # 3. Build Chroma index.
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=settings.paths.embeddings_json)

    # 4. Build or load evaluation set.
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(df, settings.paths.eval_testset)

    # 5. Evaluate baseline RAG performance.
    evaluation_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    # 6. Data quality gate + freshness monitoring.
    quality_report = run_data_quality_checks(df, settings, "baseline")
    freshness_report = build_freshness_report(df, settings, settings.paths.freshness_report)

    # 7. Generate markdown report.
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "records_fetched": len(records),
        "clean_rows": len(df),
        "run_date": run_date.isoformat(),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation_bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )

    return {
        "records": records,
        "clean_df": df,
        "index": index,
        "metrics": evaluation_bundle.summary,
        "quality": quality_report,
        "freshness": freshness_report,
    }


def main() -> None:
    settings = load_settings()
    result = run_phase1_pipeline(settings)
    print(f"Phase 1 complete. Rows={len(result['clean_df'])} metrics={result['metrics']}")


if __name__ == "__main__":
    main()
