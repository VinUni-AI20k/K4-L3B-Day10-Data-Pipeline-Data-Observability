from __future__ import annotations

import json
from typing import Any

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def _load_or_fetch_records(settings):
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        return fetch_source_records(settings), "crossref_api_or_fallback"
    return load_raw_records(settings.paths.raw_records_json), "local_raw_snapshot"


def _build_or_load_test_set(df, settings) -> list[dict[str, Any]]:
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        return build_test_set(df, settings.paths.eval_testset)
    payload = read_json(settings.paths.eval_testset)
    if not isinstance(payload, list) or not payload:
        raise ValueError("The evaluation set must be a non-empty JSON list.")
    return payload


def _build_demo_answers(test_set, settings, index) -> list[dict[str, Any]]:
    demo_answers: list[dict[str, Any]] = []
    for item in test_set[: min(3, len(test_set))]:
        result = answer_question(item["question"], settings=settings, index=index)
        demo_answers.append(
            {
                "id": item["id"],
                "question": result.question,
                "answer": result.answer,
                "retrieved_doc_ids": result.retrieved_doc_ids,
                "retrieved_titles": result.retrieved_titles,
            }
        )
    return demo_answers


def _dataframe_records(df) -> list[dict[str, Any]]:
    """Convert a dataframe into JSON-safe records with stable date-only fields."""
    records = json.loads(df.to_json(orient="records", date_format="iso"))
    for record in records:
        for field in ("published", "updated"):
            value = record.get(field)
            if isinstance(value, str) and len(value) >= 10:
                record[field] = value[:10]
    return records


def main() -> None:
    """Run the reproducible baseline pipeline and write all phase-one artifacts."""
    settings = load_settings()
    run_date = now_utc()

    records, source_mode = _load_or_fetch_records(settings)
    if not records:
        raise RuntimeError("No source records are available for the baseline pipeline.")

    clean_df = build_clean_dataframe(records, run_date)
    if clean_df.empty:
        raise RuntimeError("Cleaning produced an empty dataframe; baseline indexing was stopped.")
    write_csv(clean_df, settings.paths.clean_csv)
    clean_records = _dataframe_records(clean_df)
    write_json(settings.paths.clean_json, clean_records)

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    if not quality.get("success", False):
        raise RuntimeError(
            "Baseline data failed the quality gate. Inspect "
            f"{settings.paths.baseline_quality_report}."
        )

    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    test_set = _build_or_load_test_set(clean_df, settings)
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    demo_answers = _build_demo_answers(test_set, settings, index)
    write_json(settings.paths.demo_answers, demo_answers)

    source_summary = {
        "source": settings.source_api,
        "mode": source_mode,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "run_at_utc": run_date.isoformat(),
        "raw_response_path": str(
            settings.paths.raw_api_response.relative_to(settings.paths.project_dir)
        ),
        "raw_records_path": str(
            settings.paths.raw_records_json.relative_to(settings.paths.project_dir)
        ),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        evaluation.summary,
        quality,
        freshness,
    )

    print(
        "Baseline pipeline completed: "
        f"records={len(clean_df)}, "
        f"retrieval_hit_rate={evaluation.summary['retrieval_hit_rate']:.3f}, "
        f"report={settings.paths.baseline_report}"
    )
