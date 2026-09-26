from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xay dung corruption -> evaluate -> repair -> compare flow."""
    print("=== [CORRUPTION FLOW] Khoi chay Pipeline So Sanh 3 Trang Thai ===")
    settings = load_settings()

    # 1. Load baseline metrics va clean dataset
    print("1. Doc baseline metrics va du lieu sach...")
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_json.exists():
        print("   -> Chua co baseline metrics, vui long chay run_phase1.py truoc.")
        from pipelines.phase1 import main as phase1_main
        phase1_main()

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)

    # 2. Tao corrupted dataframe bang 6 kich ban loi
    print("2. Tien hanh tiem 6 kich ban data corruption...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    print(f"   -> Da tao corrupted dataset ({len(corrupted_df)} dong), ghi log vao {settings.paths.corruption_log}")

    # 3. Rebuild index va evaluate tren corrupted data
    print("3. Index collection 'papers-corrupted' va danh gia su suy giam...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(f"   -> Corrupted Hit Rate: {corrupted_bundle.summary.get('retrieval_hit_rate', 0.0):.1%}")

    # 4. Run quality checks & freshness tren corrupted data
    print("4. Chay Quality Gate kiem tra du lieu bi loi...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness_report.json"
    )
    print(f"   -> Corrupted GX Success: {corrupted_quality['gx_success']}, Is Fresh: {corrupted_freshness['is_fresh']}")

    # 5. Idempotent Repair lai tu raw records
    print("5. Kich hoat co che Idempotent Repair tu raw snapshot...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    print(f"   -> Da phuc hoi du lieu sach ({len(repaired_df)} dong).")

    # 6. Rebuild repaired index va evaluate
    print("6. Index collection 'papers-repaired' va danh gia lai hieu nang...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    print(f"   -> Repaired Hit Rate: {repaired_bundle.summary.get('retrieval_hit_rate', 0.0):.1%}")

    # 7. Quality checks & freshness tren repaired data
    print("7. Chay Quality Gate tren du lieu da duoc phuc hoi...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness_report.json"
    )
    print(f"   -> Repaired GX Success: {repaired_quality['gx_success']}, Is Fresh: {repaired_freshness['is_fresh']}")

    # 8. Tao comparison report
    print("8. Xuat bao cao doi chieu 3 trang thai Markdown...")
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"   -> Da xuat file: {settings.paths.comparison_report}")

    # 9. In bang tong hop ra console
    print("\n" + "=" * 70)
    print(f"{'TIEU CHI':<25} | {'BASELINE':<12} | {'CORRUPTED':<12} | {'REPAIRED':<12}")
    print("-" * 70)
    print(f"{'Retrieval Hit Rate':<25} | {baseline_metrics.get('retrieval_hit_rate', 0.0):<12.1%} | {corrupted_bundle.summary.get('retrieval_hit_rate', 0.0):<12.1%} | {repaired_bundle.summary.get('retrieval_hit_rate', 0.0):<12.1%}")
    print(f"{'Mean Token F1':<25} | {baseline_metrics.get('mean_token_f1', 0.0):<12.3f} | {corrupted_bundle.summary.get('mean_token_f1', 0.0):<12.3f} | {repaired_bundle.summary.get('mean_token_f1', 0.0):<12.3f}")
    print(f"{'Quality Gate (GX 1.x)':<25} | {'PASSED':<12} | {'FAILED' if not corrupted_quality['gx_success'] else 'PASSED':<12} | {'PASSED' if repaired_quality['gx_success'] else 'FAILED':<12}")
    print(f"{'Freshness SLA':<25} | {'FRESH':<12} | {'STALE' if not corrupted_freshness['is_fresh'] else 'FRESH':<12} | {'FRESH' if repaired_freshness['is_fresh'] else 'STALE':<12}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

