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
    """Fetch từ API khi refresh_source bật, ngược lại dùng snapshot local."""
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        return fetch_source_records(settings)

    return load_raw_records(settings.paths.raw_records_json)


def _load_or_build_test_set(
    settings: Settings,
    df,
) -> list[dict[str, Any]]:
    """
    Giữ test set cố định giữa các lần chạy để metrics
    có thể so sánh được.
    """
    test_set_path = settings.paths.eval_testset

    if test_set_path.exists() and not settings.refresh_test_set:
        return read_json(test_set_path)

    return build_test_set(df, test_set_path)


def _run_agent_demo(
    settings: Settings,
    index: LocalEmbeddingIndex,
    test_set: list[dict[str, Any]],
) -> None:
    """
    Demo agent trên một vài câu hỏi mẫu.

    Nếu thiếu LLM credentials thì bỏ qua demo thay vì
    làm fail toàn bộ Phase 1 pipeline.
    """
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
                    "agent_answer": run_agent_question(
                        agent,
                        item["question"],
                    ),
                }
            )

        write_json(settings.paths.demo_answers, demo)

        print(
            f" -> Agent demo: {len(demo)} answers "
            f"được lưu tại {settings.paths.demo_answers}"
        )

    except Exception as exc:
        print(f" -> Bỏ qua Agent Demo: {exc}")


def main() -> None:
    """Xây dựng baseline pipeline end-to-end cho Phase 1."""

    print("=" * 60)
    print("BẮT ĐẦU CHẠY PHASE 1: BASELINE DATA PIPELINE & OBSERVABILITY")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Load settings
    # ---------------------------------------------------------
    settings = load_settings()
    paths = settings.paths
    run_date = now_utc()

    # ---------------------------------------------------------
    # 2. Ingestion raw records
    # ---------------------------------------------------------
    print("\n[Step 1/7] Thu thập / đọc dữ liệu thô từ Crossref...")

    records = _load_or_fetch_records(settings)

    print(f" -> Đã tải / đọc {len(records)} bản ghi thô.")

    # ---------------------------------------------------------
    # 3. Data Cleaning
    # ---------------------------------------------------------
    print("\n[Step 2/7] Tiền xử lý & làm sạch dữ liệu...")

    df = build_clean_dataframe(records, run_date)

    if df.empty:
        raise RuntimeError(
            "Clean dataframe is empty; check raw source data."
        )

    write_csv(df, paths.clean_csv)
    write_json(
        paths.clean_json,
        df.to_dict(orient="records"),
    )

    print(
        f" -> Đã lưu dữ liệu sạch: {len(df)} dòng "
        "vào CSV và JSON."
    )

    # ---------------------------------------------------------
    # 4. Data Quality Gate & Freshness
    # ---------------------------------------------------------
    print(
        "\n[Step 3/7] Chạy Data Quality Gate "
        "& Freshness SLA..."
    )

    quality_result = run_data_quality_checks(
        df,
        settings,
        report_name="baseline",
    )

    freshness_result = build_freshness_report(
        df,
        settings,
        paths.freshness_report,
    )

    print(
        f" -> Quality Gate Status: "
        f"{quality_result.get('success')}"
    )

    print(
        f" -> Freshness SLA Status: "
        f"is_fresh={freshness_result.get('is_fresh')} "
        f"(stale: {freshness_result.get('stale_rows', 0)}/"
        f"{freshness_result.get('total_rows', len(df))})"
    )

    # ---------------------------------------------------------
    # 5. ChromaDB Vector Store Indexing
    # ---------------------------------------------------------
    print(
        "\n[Step 4/7] Indexing vector embeddings "
        "vào ChromaDB..."
    )

    index = LocalEmbeddingIndex.build(
        df,
        settings,
        embeddings_output_path=paths.embeddings_json,
    )

    print(
        f" -> Đã index {len(index.documents)} documents "
        f"vào collection '{index.collection_name}'."
    )

    # ---------------------------------------------------------
    # 6. Benchmark Test Set
    # ---------------------------------------------------------
    print(
        "\n[Step 5/7] Chuẩn bị Benchmark Test Set..."
    )

    test_set = _load_or_build_test_set(
        settings,
        df,
    )

    print(
        f" -> Test set sẵn sàng với "
        f"{len(test_set)} câu hỏi."
    )

    # ---------------------------------------------------------
    # 7. Evaluation
    # ---------------------------------------------------------
    print(
        "\n[Step 6/7] Đánh giá hiệu năng RAG "
        "trên baseline..."
    )

    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )

    metrics = evaluation.summary

    print(
        f" -> Retrieval Hit Rate: "
        f"{metrics['retrieval_hit_rate'] * 100:.1f}%"
    )

    print(
        f" -> Mean Token F1: "
        f"{metrics['mean_token_f1']:.4f}"
    )

    if "judge_accuracy" in metrics:
        print(
            f" -> Judge Accuracy: "
            f"{metrics['judge_accuracy'] * 100:.1f}%"
        )

    # ---------------------------------------------------------
    # 8. Markdown Report
    # ---------------------------------------------------------
    print(
        "\n[Step 7/7] Sinh báo cáo Phase 1 Markdown..."
    )

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

    generate_phase1_report(
        report_path=paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality_result,
        freshness=freshness_result,
    )

    print(
        f" -> Đã xuất báo cáo: "
        f"{paths.baseline_report}"
    )

    # ---------------------------------------------------------
    # 9. Agent Demo
    # ---------------------------------------------------------
    print("\n[Agent Demo] Thử nghiệm câu hỏi mẫu...")

    _run_agent_demo(
        settings,
        index,
        test_set,
    )

    print("\n" + "=" * 60)
    print("HOÀN THÀNH PHASE 1 THÀNH CÔNG!")
    print("=" * 60)


if __name__ == "__main__":
    main()