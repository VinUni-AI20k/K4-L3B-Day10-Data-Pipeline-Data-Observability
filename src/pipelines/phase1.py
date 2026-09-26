from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xay dung baseline pipeline end-to-end cho Pha 1."""
    print("=" * 60)
    print("BAT DAU CHAY PHASE 1: BASELINE DATA PIPELINE & OBSERVABILITY")
    print("=" * 60)

    # 1. Load settings
    settings = load_settings()

    # 2. Ingestion raw records
    print("\n[Step 1/7] Thu thap & doc du lieu tho tu Crossref...")
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        records = load_raw_records(settings.paths.raw_records_json)
    else:
        records = fetch_source_records(settings)
    print(f" -> Da tai / doc {len(records)} ban ghi tho.")

    # 3. Data Cleaning
    print("\n[Step 2/7] Tien xu ly & lam sach du lieu...")
    df = build_clean_dataframe(records, now_utc())
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    print(f" -> Da luu du lieu sach {len(df)} dong vao CSV va JSON.")

    # 4. Data Quality Gate (GX 1.x) & Freshness SLA
    print("\n[Step 3/7] Chay Data Quality Gate (Great Expectations 1.x) & Freshness SLA...")
    quality_result = run_data_quality_checks(df, settings, "baseline")
    freshness_result = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f" -> Quality Gate Status: {quality_result['success']}")
    print(f" -> Freshness SLA Status: is_fresh = {freshness_result['is_fresh']} (stale: {freshness_result['stale_rows']}/{freshness_result['total_rows']})")

    # 5. ChromaDB Vector Store Indexing
    print("\n[Step 4/7] Indexing vector embeddings vao ChromaDB (collection: papers-baseline)...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f" -> Da index {len(df)} tai lieu vao ChromaDB.")

    # 6. Benchmark Test Set
    print("\n[Step 5/7] Tao bo Benchmark Test Set (10 cau hoi qua 4 nhom nghiep vu)...")
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        test_set = read_json(settings.paths.eval_testset)
    else:
        test_set = build_test_set(df, settings.paths.eval_testset)
    print(f" -> Bo test set san sang voi {len(test_set)} cau hoi.")

    # 7. Evaluation
    print("\n[Step 6/7] Danh gia hieu nang RAG tren tap du lieu sach (Baseline Benchmarks)...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = bundle.summary
    print(f" -> Retrieval Hit Rate: {metrics['retrieval_hit_rate'] * 100:.1f}%")
    print(f" -> Mean Token F1: {metrics['mean_token_f1']:.4f}")
    print(f" -> Judge Accuracy: {metrics['judge_accuracy'] * 100:.1f}%")

    # 8. Markdown Report
    print("\n[Step 7/7] Sinh bao cao Phase 1 Markdown...")
    source_summary = {
        "source_api": settings.source_api,
        "total_records": len(records),
        "clean_rows": len(df),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality_result,
        freshness=freshness_result,
    )
    print(f" -> Da xuat bao cao: {settings.paths.baseline_report}")

    # Demo agent
    print("\n[Agent Demo] Thu nghiem tra loi cau hoi mau:")
    agent = build_agent(settings, index)
    demo_q = test_set[0]["question"]
    demo_ans = run_agent_question(agent, demo_q)
    print(f" Question: {demo_q}")
    print(f" Agent Answer: {demo_ans}")

    print("\n" + "=" * 60)
    print("HOAN THANH PHASE 1 THANH CONG!")
    print("=" * 60)


if __name__ == "__main__":
    main()
