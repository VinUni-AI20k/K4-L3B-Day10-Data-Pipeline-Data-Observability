from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.config import Settings, load_settings, normalized_provider
from core.utils import write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(settings: Settings) -> dict[str, Any]:
    """Build one offline baseline from the saved Crossref snapshot."""
    if normalized_provider(settings) != "mock":
        raise RuntimeError("Set LLM_PROVIDER=mock for the offline baseline run.")

    paths = settings.paths
    outputs = (
        paths.clean_csv,
        paths.clean_json,
        paths.baseline_quality_report,
        paths.freshness_report,
        paths.eval_testset,
        paths.embeddings_json,
        paths.baseline_metrics,
        paths.baseline_answers,
        paths.baseline_report,
    )
    existing = [str(path) for path in outputs if path.exists()]
    if paths.chroma_dir.exists():
        existing.extend(
            str(path) for path in paths.chroma_dir.iterdir() if path.name != ".gitkeep"
        )
    if existing:
        raise FileExistsError("Baseline would replace existing data: " + ", ".join(existing))

    snapshot_path = paths.raw_records_json if paths.raw_records_json.is_file() else paths.raw_api_response
    if not snapshot_path.is_file():
        raise FileNotFoundError("Neither Crossref raw snapshot is available.")
    run_at = datetime.now(UTC)
    raw_records = load_raw_records(snapshot_path)
    clean_df = build_clean_dataframe(raw_records, run_at)
    if clean_df.empty:
        raise ValueError("The raw snapshot produced no clean papers.")

    write_csv(clean_df, paths.clean_csv)
    write_json(paths.clean_json, clean_df.to_dict(orient="records"))

    quality = run_data_quality_checks(clean_df, settings, report_name="baseline")
    freshness = build_freshness_report(clean_df, settings, paths.freshness_report)
    if not quality["success"]:
        statistics = quality["statistics"]
        raise RuntimeError(
            "Baseline quality gate failed: "
            f"{statistics['successful_expectations']}/{statistics['evaluated_expectations']} "
            "GX expectations passed; "
            f"freshness passed={freshness['is_fresh']}. "
            f"See {paths.baseline_quality_report} and {paths.freshness_report}."
        )

    test_set = build_test_set(clean_df, paths.eval_testset)
    if len(test_set) != 10:
        raise RuntimeError(f"Expected 10 baseline questions, generated {len(test_set)}.")
    index = LocalEmbeddingIndex.build(clean_df, settings, paths.embeddings_json)
    indexed_documents = index.collection.count()
    if indexed_documents != len(clean_df):
        raise RuntimeError(f"Indexed {indexed_documents} of {len(clean_df)} clean papers.")

    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    if evaluation.summary.get("samples") != len(test_set) or len(evaluation.answers) != len(test_set):
        raise RuntimeError(
            f"Evaluated {evaluation.summary.get('samples')} questions, "
            f"saved {len(evaluation.answers)} answers, expected {len(test_set)}."
        )
    for metric in ("retrieval_hit_rate", "mean_token_f1"):
        value = evaluation.summary.get(metric)
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise RuntimeError(f"Baseline evaluation produced an invalid {metric}: {value!r}.")
    source_summary = {
        "source_api": settings.source_api,
        "ingestion_mode": "local snapshot",
        "snapshot_path": str(snapshot_path),
        "run_at_utc": run_at.isoformat(),
        "input_records": len(raw_records),
        "clean_records": len(clean_df),
        "dropped_records": len(raw_records) - len(clean_df),
        "collection_name": index.collection_name,
        "indexed_documents": indexed_documents,
        "test_questions": len(test_set),
    }
    generate_phase1_report(
        paths.baseline_report, source_summary, evaluation.summary, quality, freshness
    )
    return {"source": source_summary, "metrics": evaluation.summary, "quality": quality}


def main() -> None:
    """Run the baseline entrypoint and print results only after it succeeds."""
    settings = load_settings()
    result = run_phase1_pipeline(settings)
    source = result["source"]
    print(
        f"Raw: {source['input_records']} | Clean: {source['clean_records']} "
        f"| Test questions: {source['test_questions']}"
    )
    print(f"Collection {source['collection_name']}: {source['indexed_documents']} documents")
    print(f"Baseline metrics: {result['metrics']}")
    print(f"Phase 1 report: {settings.paths.baseline_report}")
