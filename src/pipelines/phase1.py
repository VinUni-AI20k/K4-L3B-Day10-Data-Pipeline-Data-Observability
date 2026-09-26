from __future__ import annotations

from typing import Any

from core.config import Settings, load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(settings: Settings) -> dict[str, Any]:
    """Run ingestion, cleaning, indexing, evaluation, and observability checks."""
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    clean_df = build_clean_dataframe(records, now_utc())
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(clean_df, settings.paths.eval_testset)
    metrics_bundle = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    source_summary = {
        "source_api": settings.source_api,
        "records": len(records),
        "clean_rows": len(clean_df),
        "embedding_model": settings.embedding_model,
        "collection_name": index.collection_name,
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        metrics_bundle.summary,
        quality,
        freshness,
    )
    return {
        "source": source_summary,
        "metrics": metrics_bundle.summary,
        "quality": quality,
        "freshness": freshness,
        "report_path": str(settings.paths.baseline_report),
    }


def main() -> None:
    """Run the Phase 1 baseline pipeline from project configuration."""
    result = run_phase1_pipeline(load_settings())
    print(f"Phase 1 completed: {result['source']['clean_rows']} clean rows")
    print(f"Baseline retrieval hit rate: {result['metrics']['retrieval_hit_rate']}")
    print(f"Baseline mean token F1: {result['metrics']['mean_token_f1']}")
    print(f"Report: {result['report_path']}")
