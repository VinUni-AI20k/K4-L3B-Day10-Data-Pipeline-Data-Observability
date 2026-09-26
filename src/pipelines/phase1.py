from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xay dung baseline pipeline end-to-end: Ingest -> Clean -> Index -> Eval -> Report."""
    settings = load_settings()

    # 1-2. Load settings + load hoac fetch raw records.
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)
    print(f"[Phase1] Da tai {len(records)} ban ghi raw.")

    # 3. Clean data.
    run_date = now_utc()
    df = build_clean_dataframe(records, run_date)
    print(f"[Phase1] Clean thanh cong {len(df)} dong.")

    # 4. Save clean CSV/JSON.
    write_csv(df, settings.paths.clean_csv)
    df.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=False)

    # 5. Build Chroma index (baseline collection).
    index = LocalEmbeddingIndex.build(
        df, settings, embeddings_output_path=settings.paths.embeddings_json
    )
    print(f"[Phase1] Da index {len(df)} tai lieu vao collection '{index.collection_name}'.")

    # 6. Tao hoac load evaluation set.
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)
    print(f"[Phase1] Bo test set san sang: {len(test_set)} cau hoi.")

    # 7. Evaluate.
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print(
        "[Phase1] Baseline metrics -> "
        f"hit_rate={bundle.summary['retrieval_hit_rate']:.2f}, "
        f"token_f1={bundle.summary['mean_token_f1']:.2f}"
    )

    # 8. Quality checks va freshness report.
    quality = run_data_quality_checks(df, settings, report_name="baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(
        f"[Phase1] Quality check status = {quality.get('success')}, "
        f"is_fresh = {freshness.get('is_fresh')}"
    )

    # 9. Tao markdown report.
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "max_results": settings.max_results,
        "records_fetched": len(records),
        "records_clean": len(df),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"[Phase1] Da ghi report tai {settings.paths.baseline_report}")

    # 10. (Optional) Demo agent tren mot sample question.
    try:
        from retrieval.agent import build_agent, run_agent_question

        if test_set:
            agent = build_agent(settings, index)
            sample_question = test_set[0]["question"]
            demo_answer = run_agent_question(agent, sample_question)
            write_json(
                settings.paths.demo_answers,
                {"question": sample_question, "answer": demo_answer},
            )
            print(f"[Phase1] Da luu demo agent answer tai {settings.paths.demo_answers}")
    except Exception as exc:  # pragma: no cover - demo la optional, khong lam fail pipeline
        print(f"[Phase1] Bo qua demo agent ({exc}).")


if __name__ == "__main__":
    main()
