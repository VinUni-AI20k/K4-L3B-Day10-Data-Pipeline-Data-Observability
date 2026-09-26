from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

from core.config import load_settings
from core.utils import read_json, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Điều phối toàn bộ chu trình Phase 1 (Baseline Pipeline End-to-End).
    
    Các bước thực hiện:
    1. Tải cấu hình và đường dẫn qua load_settings().
    2. Thu thập dữ liệu thô từ Crossref API (hoặc snapshot fallback).
    3. Tiền xử lý, làm sạch văn bản, tính age_days và tạo text_for_embedding.
    4. Lưu trữ dataset sạch ra CSV và JSON.
    5. Xây dựng ChromaDB vector store collection 'papers-baseline'.
    6. Tạo hoặc tải bộ Benchmark Test Set 10 câu qua 4 nhóm nghiệp vụ.
    7. Chạy đánh giá RAG Baseline (Hit Rate, Token F1, LLM Judge).
    8. Thực thi chốt kiểm dịch Great Expectations 1.x và Freshness SLA.
    9. Xuất báo cáo Markdown Phase 1 hoàn chỉnh tại data/reports/phase1_report.md.
    """
    print("\n" + "=" * 70)
    print("🚀 [START] KHOI CHAY BASELINE PIPELINE (PHASE 1) — TEAM VN")
    print("=" * 70)

    # 1. Load Cấu hình
    settings = load_settings()
    print(f"[*] Project root: {settings.paths.project_dir}")
    print(f"[*] Embedding model: {settings.embedding_model}")
    print(f"[*] LLM Provider: {settings.llm_provider} (Model: {settings.model_name})")

    # 2. Ingestion: Thu thập dữ liệu thô
    print("\n[Step 1/7] Thu thap du lieu thô tu Crossref API / Snapshot fallback...")
    records = fetch_source_records(settings)
    source_summary = {
        "api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "count": len(records),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    print(f"  -> Da thu thap {len(records)} ban ghi thô.")

    # 3. Data Cleaning & Modeling
    print("\n[Step 2/7] Tien xu ly va lam sach du lieu (Cleaning & Modeling)...")
    run_date = datetime.now(UTC)
    clean_df = build_clean_dataframe(records, run_date=run_date)
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(settings.paths.clean_csv, index=False)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))
    print(f"  -> Da lam sach {len(clean_df)} dong du lieu.")
    print(f"  -> Luu tru: {settings.paths.clean_csv.name} & {settings.paths.clean_json.name}")

    # 4. ChromaDB Vector Store Indexing
    print("\n[Step 3/7] Xay dung ChromaDB Vector Index ('papers-baseline')...")
    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"  -> Da nhung va luu tru {len(index.documents)} documents vao collection '{index.collection_name}'.")

    # 5. Benchmark Test Set
    print("\n[Step 4/7] Khoi tao bo Benchmark Test Set (10 cau hoi)...")
    if settings.refresh_test_set or not settings.paths.eval_testset.is_file():
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
        print(f"  -> Da tao moi bo benchmark gom {len(test_set)} cau hoi.")
    else:
        test_set = read_json(settings.paths.eval_testset)
        print(f"  -> Da nap bo benchmark co san gom {len(test_set)} cau hoi tu {settings.paths.eval_testset.name}.")

    # 6. Evaluation RAG Baseline
    print("\n[Step 5/7] Danh gia hieu nang RAG Baseline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = bundle.summary
    print(f"  -> Retrieval Hit Rate : {metrics.get('retrieval_hit_rate', 0.0):.2%}")
    print(f"  -> Mean Token F1       : {metrics.get('mean_token_f1', 0.0):.4f}")
    print(f"  -> Judge Accuracy      : {metrics.get('judge_accuracy', 0.0):.2%}")
    print(f"  -> Mean Judge Score    : {metrics.get('mean_judge_score', 0.0):.2f} / 5.0")

    # 7. Data Observability (GX 1.x + Freshness)
    print("\n[Step 6/7] Chay Data Observability (Great Expectations 1.x & Freshness SLA)...")
    quality_report = run_data_quality_checks(clean_df, settings=settings, report_name="baseline")
    freshness_report = build_freshness_report(clean_df, settings=settings, report_path=settings.paths.freshness_report)
    gx_status = "PASS" if quality_report.get("gx_success", False) else "FAIL"
    fresh_status = "FRESH" if freshness_report.get("is_fresh", False) else "STALE"
    print(f"  -> GX 1.x Quality Gate : {gx_status}")
    print(f"  -> Freshness SLA       : {fresh_status} (Stale ratio: {freshness_report.get('stale_ratio', 0.0):.2%})")

    # 8. Sinh Báo Cáo Pha 1
    print("\n[Step 7/7] Xuat bao cao markdown Phase 1...")
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality_report,
        freshness=freshness_report,
    )
    print(f"  -> Báo cáo da luu tai: {settings.paths.baseline_report}")

    print("\n" + "=" * 70)
    print("✅ [HOAN THANH PHA 1] BASELINE PIPELINE DA SAN SANG!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
