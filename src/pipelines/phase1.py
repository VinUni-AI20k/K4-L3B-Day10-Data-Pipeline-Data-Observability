from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xay dung baseline pipeline end-to-end."""
    print("=== [PHASE 1] Khoi chay Baseline Pipeline ===")
    settings = load_settings()

    # 1. Load / fetch raw records
    print("1. Thu thap raw data tu Crossref...")
    records = fetch_source_records(settings)
    print(f"   -> Da load {len(records)} raw records.")

    # 2. Clean data
    print("2. Tien xu ly va chuan hoa du lieu...")
    df = build_clean_dataframe(records, now_utc())
    write_csv(df, settings.paths.clean_csv)
    df.to_json(settings.paths.clean_json, orient="records", indent=2)
    print(f"   -> Da luu {len(df)} dong vao clean artifacts.")

    # 3. Build Chroma index
    print("3. Xay dung Vector Index (ChromaDB) cho baseline collection...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"   -> Collection '{settings.baseline_collection_name}' da duoc index thanh cong.")

    # 4. Tao hoac load evaluation set
    print("4. Sinh bo cau hoi danh gia benchmark...")
    test_set = build_test_set(df, settings.paths.eval_testset)
    print(f"   -> Da sinh {len(test_set)} cau hoi test.")

    # 5. Evaluate pipeline
    print("5. Chay danh gia hieu nang RAG baseline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print(f"   -> Retrieval Hit Rate: {bundle.summary.get('retrieval_hit_rate', 0.0):.1%}")
    print(f"   -> Mean Token F1: {bundle.summary.get('mean_token_f1', 0.0):.3f}")

    # 6. Run quality checks & freshness report
    print("6. Thuc thi Great Expectations 1.x & Freshness SLA...")
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f"   -> Quality check status: {quality['success']} (GX: {quality['gx_success']})")
    print(f"   -> Freshness SLA status: {freshness['is_fresh']}")

    # 7. Tao markdown report
    print("7. Xuat bao cao Phase 1 Markdown...")
    generate_phase1_report(
        settings.paths.baseline_report,
        {"source": settings.source_api, "records": len(df)},
        bundle.summary,
        quality,
        freshness,
    )
    print(f"   -> Da xuat file: {settings.paths.baseline_report}")

    # 8. Demo Agent
    try:
        agent = build_agent(settings, index)
        sample_q = test_set[0]["question"]
        agent_ans = run_agent_question(agent, sample_q)
        write_json(settings.paths.demo_answers, [{"question": sample_q, "answer": agent_ans}])
    except Exception as exc:
        print(f"   (Luu y: LLM Agent demo dung fallback: {exc})")

    print("=== [PHASE 1] Hoan thanh tat ca deliverables! ===")


if __name__ == "__main__":
    main()

