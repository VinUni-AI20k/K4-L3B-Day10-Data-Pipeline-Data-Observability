from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv

from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set

from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import (
    fetch_source_records,
    load_raw_records,
)

from observability.quality import (
    build_freshness_report,
    run_data_quality_checks,
)

from observability.reporting import generate_phase1_report

from retrieval.index import LocalEmbeddingIndex


def _save_dataframe(df, csv_path, json_path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    write_csv(df, csv_path)

    df.to_json(
        json_path,
        orient="records",
        indent=2,
        force_ascii=False,
        date_format="iso",
    )


def main() -> None:
    settings = load_settings()

    print("=== DAY10 PHASE 1: BASELINE PIPELINE ===")

    # ---------------------------------------------------------
    # 1. Load / fetch raw records
    # ---------------------------------------------------------
    if (
        settings.refresh_source
        or not settings.paths.raw_records_json.exists()
    ):
        print("[1/8] Fetching Crossref source...")
        records = fetch_source_records(settings)
    else:
        print("[1/8] Loading existing raw records...")
        records = load_raw_records(
            settings.paths.raw_records_json
        )

    print(f"Raw records: {len(records)}")

    # ---------------------------------------------------------
    # 2. Cleaning
    # ---------------------------------------------------------
    print("[2/8] Cleaning data...")

    clean_df = build_clean_dataframe(
        records,
        now_utc(),
    )

    _save_dataframe(
        clean_df,
        settings.paths.clean_csv,
        settings.paths.clean_json,
    )

    print(f"Clean records: {len(clean_df)}")

    # ---------------------------------------------------------
    # 3. Build baseline Chroma index
    # ---------------------------------------------------------
    print("[3/8] Building baseline Chroma index...")

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings,
        settings.paths.embeddings_json,
    )

    print(
        f"Collection: {index.collection_name}, "
        f"documents={len(index.documents)}"
    )

    # ---------------------------------------------------------
    # 4. Evaluation test set
    # ---------------------------------------------------------
    print("[4/8] Preparing evaluation set...")

    if (
        settings.refresh_test_set
        or not settings.paths.eval_testset.exists()
    ):
        test_set = build_test_set(
            clean_df,
            settings.paths.eval_testset,
        )
        print(f"Generated test questions: {len(test_set)}")
    else:
        print(
            f"Using existing test set: "
            f"{settings.paths.eval_testset}"
        )

    # ---------------------------------------------------------
    # 5. Baseline evaluation
    # ---------------------------------------------------------
    print("[5/8] Evaluating baseline...")

    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    # ---------------------------------------------------------
    # 6. Quality checks
    # ---------------------------------------------------------
    print("[6/8] Running data quality checks...")

    quality = run_data_quality_checks(
        clean_df,
        settings,
        "baseline",
    )

    # ---------------------------------------------------------
    # 7. Freshness
    # ---------------------------------------------------------
    print("[7/8] Building freshness report...")

    freshness = build_freshness_report(
        clean_df,
        settings,
        settings.paths.freshness_report,
    )

    # ---------------------------------------------------------
    # 8. Markdown report
    # ---------------------------------------------------------
    print("[8/8] Generating baseline report...")

    source_summary = {
        "source": settings.source_api,
        "query": settings.source_query,
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "embedding_model": settings.embedding_model,
        "collection": settings.baseline_collection_name,
    }

    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )

    print()
    print("=== BASELINE COMPLETE ===")
    print(
        f"retrieval_hit_rate = "
        f"{evaluation.summary['retrieval_hit_rate']:.4f}"
    )
    print(
        f"mean_token_f1      = "
        f"{evaluation.summary['mean_token_f1']:.4f}"
    )
    print(
        f"Report: {settings.paths.baseline_report}"
    )


if __name__ == "__main__":
    main()