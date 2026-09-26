from __future__ import annotations

from typing import Any

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(settings: Settings) -> dict[str, Any]:
    """Run the clean-data baseline pipeline and return its evidence summary."""
    run_date = now_utc()

    records = fetch_source_records(settings)
    clean_df = build_clean_dataframe(records, run_date)
    if clean_df.empty:
        raise RuntimeError("Cleaning produced an empty dataframe; baseline pipeline stopped.")

    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    if not quality["success"]:
        raise RuntimeError(
            "Baseline data failed the quality/freshness gate; vector indexing was blocked. "
            f"See {settings.paths.baseline_quality_report}."
        )

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)
        if not isinstance(test_set, list) or len(test_set) != 10:
            test_set = build_test_set(clean_df, settings.paths.eval_testset)

    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    def artifact_path(path) -> str:
        return path.resolve().relative_to(settings.paths.project_dir).as_posix()

    source_summary = {
        "generated_at": run_date.isoformat(),
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "collection_name": index.collection_name,
        "embedding_model": settings.embedding_model,
        "test_questions": len(test_set),
        "artifacts": {
            "Raw API response": artifact_path(settings.paths.raw_api_response),
            "Parsed raw records": artifact_path(settings.paths.raw_records_json),
            "Clean CSV": artifact_path(settings.paths.clean_csv),
            "Clean JSON": artifact_path(settings.paths.clean_json),
            "Chroma database": artifact_path(settings.paths.chroma_dir),
            "Embedding manifest": artifact_path(settings.paths.embeddings_json),
            "Benchmark test set": artifact_path(settings.paths.eval_testset),
            "Baseline answers": artifact_path(settings.paths.baseline_answers),
            "Baseline metrics": artifact_path(settings.paths.baseline_metrics),
            "Quality report": artifact_path(settings.paths.baseline_quality_report),
            "Freshness report": artifact_path(settings.paths.freshness_report),
        },
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )

    return {
        "source": source_summary,
        "metrics": evaluation.summary,
        "quality": quality,
        "freshness": freshness,
        "report_path": str(settings.paths.baseline_report),
    }


def main() -> None:
    result = run_phase1_pipeline(load_settings())
    metrics = result["metrics"]
    print("Phase 1 baseline pipeline completed.")
    print(f"Clean records: {result['source']['clean_records']}")
    print(f"Benchmark questions: {metrics['samples']}")
    print(f"Retrieval hit rate: {metrics['retrieval_hit_rate']:.4f}")
    print(f"Mean token F1: {metrics['mean_token_f1']:.4f}")
    print(f"Quality gate: {result['quality']['success']}")
    print(f"Freshness: {result['freshness']['is_fresh']}")
    print(f"Report: {result['report_path']}")
