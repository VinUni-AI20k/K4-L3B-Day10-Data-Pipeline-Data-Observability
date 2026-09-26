from __future__ import annotations

from datetime import UTC, datetime
import logging

from core.config import Settings, load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


logger = logging.getLogger(__name__)


def run_phase1_pipeline(settings: Settings) -> dict:
    """Run ingestion, cleaning, indexing, evaluation, and quality reporting."""
    raw_path = settings.paths.raw_records_json
    if settings.refresh_source or not raw_path.exists():
        records = fetch_source_records(settings)
        source_mode = "Crossref API or offline snapshot fallback"
    else:
        records = load_raw_records(raw_path)
        source_mode = "saved raw records"
    logger.info("Loaded %s raw papers from %s", len(records), source_mode)

    df = build_clean_dataframe(records, datetime.now(UTC))
    if df.empty:
        raise RuntimeError("No clean papers are available for the baseline pipeline")
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    logger.info("Saved %s clean papers", len(df))

    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    logger.info("Indexed %s papers in ChromaDB", len(df))

    testset_path = settings.paths.eval_testset
    if settings.refresh_test_set or not testset_path.exists():
        test_set = build_test_set(df, testset_path)
    else:
        test_set = read_json(testset_path)
    if not test_set:
        raise RuntimeError("The benchmark test set is empty")

    evaluation = evaluate_pipeline(
        settings,
        index,
        testset_path,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = quality["freshness"]
    source_summary = {
        "source_api": settings.source_api,
        "source_mode": source_mode,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_records": len(records),
        "clean_records": len(df),
        "benchmark_questions": len(test_set),
        "chroma_collection": index.collection_name,
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        evaluation.summary,
        quality,
        freshness,
    )
    return {"source": source_summary, "metrics": evaluation.summary, "quality": quality}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    settings = load_settings()
    result = run_phase1_pipeline(settings)
    metrics = result["metrics"]
    print(f"Clean papers: {result['source']['clean_records']}")
    print(f"Retrieval hit rate: {metrics['retrieval_hit_rate']:.3f}")
    print(f"Mean token F1: {metrics['mean_token_f1']:.3f}")
    print(f"Quality gate passed: {result['quality']['success']}")
    print(f"Report: {settings.paths.baseline_report}")
