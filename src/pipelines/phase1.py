from __future__ import annotations

import json

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def _save_dataframe(df, csv_path, json_path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, json.loads(df.to_json(orient="records")))


def main() -> None:
    settings = load_settings()
    run_date = now_utc()

    records = fetch_source_records(settings)
    if not records and settings.paths.raw_records_json.exists():
        records = load_raw_records(settings.paths.raw_records_json)

    df = build_clean_dataframe(records, run_date)
    _save_dataframe(df, settings.paths.clean_csv, settings.paths.clean_json)

    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)

    test_set = build_test_set(df, settings.paths.eval_testset)

    bundle = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary={
            "source_api": settings.source_api,
            "query": settings.source_query,
            "n_raw": len(records),
            "n_clean": int(len(df)),
            "run_date": run_date.isoformat(),
            "embedding_model": settings.embedding_model,
            "collection_name": settings.baseline_collection_name,
        },
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )

    demo_answers = []
    for item in test_set[:3]:
        result = answer_question(item["question"], settings=settings, index=index)
        demo_answers.append(
            {
                "question": item["question"],
                "answer": result.answer,
                "retrieved_doc_ids": result.retrieved_doc_ids,
            }
        )
    write_json(settings.paths.demo_answers, demo_answers)

    print("Phase 1 complete")
    print(f"Clean rows: {len(df)}")
    print(f"Test questions: {len(test_set)}")
    print(f"Quality success: {quality['success']}")
    print(f"Freshness is_fresh: {freshness['is_fresh']}")
    print(
        "Baseline metrics: "
        f"hit_rate={bundle.summary['retrieval_hit_rate']:.4f} "
        f"token_f1={bundle.summary['mean_token_f1']:.4f}"
    )
    print(f"Report: {settings.paths.baseline_report}")
