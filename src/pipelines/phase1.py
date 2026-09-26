from __future__ import annotations

from typing import Any

from core.config import Settings, load_settings, require_llm_credentials
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def _load_or_fetch_records(settings: Settings) -> list[PaperRecord]:
    """Fetch tu API khi REFRESH_SOURCE bat, nguoc lai dung snapshot local."""
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        return fetch_source_records(settings)
    return load_raw_records(settings.paths.raw_records_json)


def _load_or_build_test_set(settings: Settings, df) -> list[dict[str, Any]]:
    """Giu test set co dinh giua cac lan chay de metrics so sanh duoc."""
    test_set_path = settings.paths.eval_testset
    if test_set_path.exists() and not settings.refresh_test_set:
        return read_json(test_set_path)
    return build_test_set(df, test_set_path)


def _run_agent_demo(settings: Settings, index: LocalEmbeddingIndex, test_set: list[dict[str, Any]]) -> None:
    """Demo agent tren vai cau hoi mau; bo qua neu thieu LLM credentials."""
    try:
        require_llm_credentials(settings)
        from retrieval.agent import build_agent, run_agent_question

        agent = build_agent(settings, index)
        demo = []
        for item in test_set[:3]:
            demo.append(
                {
                    "question": item["question"],
                    "ground_truth": item["ground_truth"],
                    "agent_answer": run_agent_question(agent, item["question"]),
                }
            )
        write_json(settings.paths.demo_answers, demo)
        print(f"[phase1] Agent demo: {len(demo)} answers -> {settings.paths.demo_answers}")
    except Exception as exc:
        print(f"[phase1] Skip agent demo: {exc}")


def main() -> None:
    # 1. Load settings.
    settings = load_settings()
    paths = settings.paths
    run_date = now_utc()

    # 2. Load hoac fetch raw records.
    records = _load_or_fetch_records(settings)
    print(f"[phase1] Raw records: {len(records)}")

    # 3. Clean data.
    df = build_clean_dataframe(records, run_date)
    if df.empty:
        raise RuntimeError("Clean dataframe is empty; check raw source data.")
    print(f"[phase1] Clean rows: {len(df)}")

    # 4. Save clean CSV/JSON.
    write_csv(df, paths.clean_csv)
    write_json(paths.clean_json, df.to_dict(orient="records"))

    # 5. Build Chroma index.
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=paths.embeddings_json)
    print(f"[phase1] Indexed {len(index.documents)} documents into '{index.collection_name}'")

    # 6. Tao hoac load evaluation set.
    test_set = _load_or_build_test_set(settings, df)
    print(f"[phase1] Test set: {len(test_set)} questions")

    # 7. Evaluate.
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    metrics = evaluation.summary
    print(
        f"[phase1] Baseline hit_rate={metrics['retrieval_hit_rate']:.3f} "
        f"token_f1={metrics['mean_token_f1']:.3f}"
    )

    # 8. Run quality checks va freshness report.
    quality = run_data_quality_checks(df, settings, report_name="baseline")
    freshness = build_freshness_report(df, settings, paths.freshness_report)
    print(f"[phase1] Quality success={quality.get('success')} | fresh={freshness.get('is_fresh')}")

    # 9. Tao markdown report.
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "refresh_source": settings.refresh_source,
        "run_date": run_date.isoformat(),
        "raw_records": len(records),
        "clean_rows": len(df),
        "embedding_model": settings.embedding_model,
        "collection_name": index.collection_name,
        "test_set_size": len(test_set),
    }
    generate_phase1_report(paths.baseline_report, source_summary, metrics, quality, freshness)
    print(f"[phase1] Report -> {paths.baseline_report}")

    # 10. Demo agent tren vai sample question.
    _run_agent_demo(settings, index, test_set)
