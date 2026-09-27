from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import os
from pathlib import Path

from core.config import Settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline, evaluate_abstention_challenges
from evaluation.testset import build_test_set, validate_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from pipelines.runs import RunStore, cli_run, digest
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(
    settings: Settings, *, run_at: datetime | None = None, test_set: list[dict] | None = None
) -> dict[str, Any]:
    """Build a baseline in a new attempt; quality must pass before publishing clean/index data."""
    paths = settings.paths
    if settings.refresh_source:
        raise ValueError("Baseline uses immutable offline raw snapshots; source refresh is not allowed here")
    if any(path.exists() for path in (paths.clean_json, paths.embeddings_json, paths.baseline_metrics)):
        raise FileExistsError("Baseline output already exists; use the managed CLI with a run ID")
    snapshot = paths.raw_records_json if paths.raw_records_json.is_file() else paths.raw_api_response
    run_at = run_at or datetime.now(UTC)
    print("[1/6] Read immutable raw snapshot", flush=True)
    raw_records = load_raw_records(snapshot)
    print("[2/6] Clean data in memory", flush=True)
    clean_df = build_clean_dataframe(raw_records, run_at)

    print("[3/6] Validate GX and freshness before indexing", flush=True)
    quality = run_data_quality_checks(clean_df, settings, report_name="baseline")
    freshness = build_freshness_report(clean_df, settings, paths.freshness_report)
    if not quality["success"]:
        raise RuntimeError(
            "Baseline quality gate failed before indexing: "
            f"{quality['statistics']['successful_expectations']}/"
            f"{quality['statistics']['evaluated_expectations']} GX checks; "
            f"freshness={freshness['is_fresh']}. See {paths.baseline_quality_report}"
        )
    test_set = build_test_set(clean_df) if test_set is None else test_set
    validate_test_set(test_set, clean_df)
    write_csv(clean_df, paths.clean_csv)
    write_json(paths.clean_json, clean_df.to_dict(orient="records"))
    write_json(paths.eval_testset, test_set)
    print("[4/6] Build and validate a new Chroma collection", flush=True)
    index = LocalEmbeddingIndex.build(clean_df, settings, paths.embeddings_json)
    try:
        indexed_documents = index.collection.count()
        print("[5/6] Evaluate the frozen benchmark", flush=True)
        evaluation = evaluate_pipeline(
            settings=settings, index=index, test_set_path=paths.eval_testset,
            metrics_output_path=paths.baseline_metrics, answers_output_path=paths.baseline_answers,
        )
        if evaluation.summary["samples"] != 10 or len(evaluation.answers) != 10:
            raise RuntimeError("Baseline evaluation did not score all ten questions")
        evaluate_abstention_challenges(
            settings, index, paths.baseline_answers.with_name("baseline_challenges.json"))
        source = {
            "source_api": settings.source_api,
            "ingestion_mode": "immutable local snapshot",
            "snapshot_path": Path(os.path.relpath(snapshot, paths.baseline_report.parent)).as_posix(),
            "raw_sha256": digest(snapshot),
            "llm_provider": settings.llm_provider,
            "model_name": settings.model_name,
            "run_at_utc": run_at.isoformat(),
            "input_records": len(raw_records), "clean_records": len(clean_df),
            "dropped_records": len(raw_records) - len(clean_df),
            "collection_name": index.collection_name, "indexed_documents": indexed_documents,
            "test_questions": len(test_set), "test_set_sha256": digest(paths.eval_testset),
        }
        print("[6/6] Generate baseline report", flush=True)
        generate_phase1_report(paths.baseline_report, source, evaluation.summary, quality, freshness)
        return {"source": source, "metrics": evaluation.summary, "quality": quality}
    finally:
        index.close()


def main() -> None:
    settings, root = cli_run("Build or reuse a verified offline baseline")
    with RunStore(settings, root).locked() as run:
        def operation(output_settings):
            benchmark = run.root / "inputs/test_set.json"
            return run_phase1_pipeline(
                output_settings,
                run_at=datetime.fromisoformat(run.manifest["created_at_utc"]),
                test_set=read_json(benchmark) if benchmark.is_file() else None,
            )
        result = run.execute("baseline", operation)
        print(f"Baseline metrics: {result['metrics']}")
        print(f"Run manifest: {run.path}")
