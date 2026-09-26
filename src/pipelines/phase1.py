from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.config import Settings, load_settings
from core.utils import write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(settings: Settings) -> dict[str, Any]:
    """Build and evaluate the clean baseline from preserved Crossref records."""
    if settings.refresh_source or not settings.paths.raw_records_json.is_file():
        records = fetch_source_records(settings)
        source_mode = "Crossref API (offline snapshot fallback)"
    else:
        records = load_raw_records(settings.paths.raw_records_json)
        source_mode = "Raw records snapshot"

    df = build_clean_dataframe(records, datetime.now(UTC))
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))

    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    if not quality["success"]:
        raise RuntimeError("Baseline data failed the quality or freshness gate; see data/quality/baseline_quality_report.json")

    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    test_set = build_test_set(df, settings.paths.eval_testset)
    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    source_summary = {
        "Nguồn": settings.source_api,
        "Chế độ": source_mode,
        "Raw records": len(records),
        "Clean records": len(df),
        "Papers with categories": int(df["categories_joined"].ne("").sum()),
        "Câu hỏi benchmark": len(test_set),
        "Embedding model": settings.embedding_model,
        "Embedding runtime": type(index.embedding_model.model).__name__,
        "Chroma collection": index.collection_name,
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        evaluation.summary,
        quality,
        freshness,
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
    print(f"Baseline: {result['source']['Clean records']} papers, "
          f"Hit Rate {result['metrics']['retrieval_hit_rate']:.2%}, "
          f"Token F1 {result['metrics']['mean_token_f1']:.4f}")
    print(f"Report: {result['report_path']}")
