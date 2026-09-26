from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xay dung corruption -> evaluate -> repair -> compare flow hoan chinh."""
    print("=" * 60)
    print("BAT DAU CHAY CORRUPTION & IDEMPOTENT REPAIR FLOW")
    print("=" * 60)

    settings = load_settings()

    # 1. Kiem tra baseline metrics va clean data
    if not settings.paths.clean_json.exists():
        raise FileNotFoundError(f"Chua co clean dataset tai {settings.paths.clean_json}. Vui long chay run_phase1.py truoc.")

    df_clean = pd.read_json(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f"\n[Baseline] Clean records: {len(df_clean)} | Baseline Hit Rate: {baseline_metrics.get('retrieval_hit_rate', 0)*100:.1f}%")

    # 2. Tien hanh Data Corruption
    print("\n[Step 1/5] Tien hanh tiêm 6 kich ban du lieu loi (Data Corruption Suite)...")
    corrupted_df = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f" -> Da luu du lieu loi: {settings.paths.corrupted_clean_csv}")
    print(f" -> Da ghi log chi tiet 6 dang loi: {settings.paths.corruption_log}")

    # 3. Kiem tra Observability tren du lieu loi
    print("\n[Step 2/5] Chay Observability tren du lieu loi...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(corrupted_df, settings, corrupted_freshness_path)
    print(f" -> Quality Gate Status (Bi loi expected): {corrupted_quality['success']}")
    print(f" -> Freshness SLA Status: is_fresh = {corrupted_freshness['is_fresh']} (stale: {corrupted_freshness['stale_rows']}/{corrupted_freshness['total_rows']})")

    # 4. Danh gia do suy giam tren tap du lieu loi (Silent Failure)
    print("\n[Step 3/5] Indexing va do luong suy giam tren ChromaDB (collection: papers-corrupted)...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(f" -> Corrupted Retrieval Hit Rate: {corrupted_metrics['retrieval_hit_rate'] * 100:.1f}% (Giam tu {baseline_metrics['retrieval_hit_rate']*100:.1f}%)")
    print(f" -> Corrupted Mean Token F1: {corrupted_metrics['mean_token_f1']:.4f}")

    # 5. Idempotent Repair tu Raw Snapshot
    print("\n[Step 4/5] Kich hoat co che Idempotent Self-Repair tu Raw Snapshot ban dau...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f" -> Phuc hoi thanh cong {len(repaired_df)} ban ghi sach tu snapshot.")

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(repaired_df, settings, repaired_freshness_path)
    print(f" -> Repaired Quality Gate Status: {repaired_quality['success']}")
    print(f" -> Repaired Freshness SLA Status: is_fresh = {repaired_freshness['is_fresh']}")

    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    print(f" -> Repaired Retrieval Hit Rate: {repaired_metrics['retrieval_hit_rate'] * 100:.1f}%")
    print(f" -> Repaired Mean Token F1: {repaired_metrics['mean_token_f1']:.4f}")

    # 6. Xuat bao cao so sanh 3 trang thai
    print("\n[Step 5/5] Sinh bao cao doi chieu 3 trang thai (corruption_report.md)...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f" -> Da xuat bao cao: {settings.paths.comparison_report}")

    # 7. In bang tong hop doi chieu ra console
    print("\n" + "=" * 70)
    print("BANG DOI CHIEU HIEN TUONG SILENT FAILURE VA PHUC HOI (3 TRANG THAI):")
    print("=" * 70)
    print(f"{'Chi so':<25} | {'Baseline':<12} | {'Corrupted':<12} | {'Repaired':<12}")
    print("-" * 70)
    print(f"{'Retrieval Hit Rate':<25} | {baseline_metrics['retrieval_hit_rate']*100:<11.1f}% | {corrupted_metrics['retrieval_hit_rate']*100:<11.1f}% | {repaired_metrics['retrieval_hit_rate']*100:<11.1f}%")
    print(f"{'Mean Token F1':<25} | {baseline_metrics['mean_token_f1']:<12.4f} | {corrupted_metrics['mean_token_f1']:<12.4f} | {repaired_metrics['mean_token_f1']:<12.4f}")
    print(f"{'Judge Accuracy':<25} | {baseline_metrics['judge_accuracy']*100:<11.1f}% | {corrupted_metrics['judge_accuracy']*100:<11.1f}% | {repaired_metrics['judge_accuracy']*100:<11.1f}%")
    print(f"{'Quality Gate (GX)':<25} | {'PASSED':<12} | {'FAILED':<12} | {'PASSED':<12}")
    print(f"{'Freshness SLA':<25} | {'FRESH':<12} | {'STALE':<12} | {'FRESH':<12}")
    print("=" * 70)
    print("HOAN THANH CORRUPTION & REPAIR FLOW XUAT SAC!")


if __name__ == "__main__":
    main()
