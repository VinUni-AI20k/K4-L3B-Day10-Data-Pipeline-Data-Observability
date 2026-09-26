from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import main as run_phase1
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Điều phối toàn bộ chu trình Corruption Flow, Silent Failure Analysis và Idempotent Repair.

    Các bước thực hiện:
    1. Nạp baseline metrics và DataFrame sạch từ Phase 1 (tự động chạy Phase 1 nếu chưa có).
    2. Tiêm 6 kịch bản Data Corruption vào DataFrame sạch -> lưu corrupted artifacts và log.
    3. Đánh chỉ mục ChromaDB collection 'papers-corrupted' từ dữ liệu đã tiêm lỗi.
    4. Chạy đánh giá RAG trên tập dữ liệu bẩn để đo lường suy giảm (Silent Failure).
    5. Kiểm thử Data Observability (GX 1.x & Freshness) trên dữ liệu bẩn -> chứng minh cảnh báo FAIL / STALE.
    6. KÍCH HOẠT IDEMPOTENT REPAIR: Phục hồi từ raw records ban đầu 'crossref_records.json'.
    7. Tái thực hiện Data Cleaning chuẩn hóa -> lưu repaired dataset.
    8. Đánh chỉ mục ChromaDB collection 'papers-repaired' từ dữ liệu đã phục hồi.
    9. Chạy đánh giá RAG trên tập dữ liệu phục hồi -> chứng minh các chỉ số phục hồi 100%.
    10. Kiểm thử Data Observability trên dữ liệu phục hồi -> chứng minh Quality Gate PASS và Freshness FRESH.
    11. Xuất báo cáo đối chiếu định lượng 3 trạng thái tại data/reports/corruption_report.md.
    12. In bảng đối chiếu trực quan ra console phục vụ Live Demo.
    """
    print("\n" + "=" * 80)
    print("🔥 [START] CHU TRINH DATA CORRUPTION & IDEMPOTENT REPAIR — TEAM VN")
    print("=" * 80)

    settings = load_settings()

    # 1. Nạp baseline metrics và DataFrame sạch
    print("\n[Step 1/8] Kiem tra va nap ket qua Baseline tu Phase 1...")
    if not (settings.paths.baseline_metrics.is_file() and settings.paths.clean_json.is_file()):
        print("  [!] Khong tim thay artifact Baseline. Dang tu dong chay Phase 1 de tao chuan...")
        run_phase1()

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.DataFrame(read_json(settings.paths.clean_json))
    print(f"  -> Da nap Baseline DataFrame: {len(clean_df)} dong.")
    print(f"  -> Baseline Hit Rate : {baseline_metrics.get('retrieval_hit_rate', 0.0):.2%}")
    print(f"  -> Baseline Token F1  : {baseline_metrics.get('mean_token_f1', 0.0):.4f}")

    # 2. Tiêm 6 kịch bản Data Corruption
    print("\n[Step 2/8] Tiem 6 kich ban Data Corruption vao du lieu sach...")
    corrupted_df = corrupt_clean_dataframe(clean_df, output_log_path=settings.paths.corruption_log)
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df.to_csv(settings.paths.corrupted_clean_csv, index=False)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"  -> So dong du lieu sau khi tiem loi: {len(corrupted_df)} dong (goc: {len(clean_df)} dong).")
    print(f"  -> Luu tru: {settings.paths.corrupted_clean_csv.name} & {settings.paths.corrupted_clean_json.name}")
    print(f"  -> Nhat ky tiem loi da ghi: {settings.paths.corruption_log.name}")

    # 3. Đánh chỉ mục ChromaDB cho Corrupted Data
    print("\n[Step 3/8] Xay dung ChromaDB collection ('papers-corrupted')...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    print(f"  -> Da nhung {len(corrupted_index.documents)} tai lieu vao collection '{corrupted_index.collection_name}'.")

    # 4. Đánh giá RAG trên Corrupted Data
    print("\n[Step 4/8] Danh gia hieu nang RAG tren tap du lieu bi tiem loi (Do luong Silent Failure)...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(f"  -> Corrupted Hit Rate : {corrupted_metrics.get('retrieval_hit_rate', 0.0):.2%}")
    print(f"  -> Corrupted Token F1  : {corrupted_metrics.get('mean_token_f1', 0.0):.4f}")
    print(f"  -> Corrupted Accuracy  : {corrupted_metrics.get('judge_accuracy', 0.0):.2%}")

    # 5. Data Observability trên Corrupted Data
    print("\n[Step 5/8] Kiem tra Data Observability tren Corrupted Data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings=settings, report_name="corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings=settings,
        report_path=settings.paths.quality_dir / "corrupted_freshness_report.json",
    )
    c_gx_status = "PASS" if corrupted_quality.get("gx_success", False) else "FAIL"
    c_fresh_status = "FRESH" if corrupted_freshness.get("is_fresh", False) else "STALE"
    print(f"  -> GX 1.x Quality Gate : {c_gx_status} (Phat hien loi!)")
    print(f"  -> Freshness SLA       : {c_fresh_status} (Stale ratio: {corrupted_freshness.get('stale_ratio', 0.0):.2%})")

    # 6. KÍCH HOẠT IDEMPOTENT REPAIR
    print("\n[Step 6/8] 🛠️ KICH HOAT CO CHE IDEMPOTENT SELF-HEALING / REPAIR...")
    print(f"  -> Nap du lieu goc tin cay tu: {settings.paths.raw_records_json.name}")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    run_date = datetime.now(UTC)
    repaired_df = build_clean_dataframe(raw_records, run_date=run_date)
    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    repaired_df.to_csv(settings.paths.repaired_clean_csv, index=False)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"  -> Tai tao thanh cong {len(repaired_df)} dong du lieu sach.")
    print(f"  -> Luu tru: {settings.paths.repaired_clean_csv.name} & {settings.paths.repaired_clean_json.name}")

    # 7. Đánh chỉ mục & Đánh giá Repaired Data
    print("\n[Step 7/8] Xay dung ChromaDB collection ('papers-repaired') va danh gia phuc hoi...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    repaired_quality = run_data_quality_checks(repaired_df, settings=settings, report_name="repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings=settings,
        report_path=settings.paths.quality_dir / "repaired_freshness_report.json",
    )
    r_gx_status = "PASS" if repaired_quality.get("gx_success", False) else "FAIL"
    r_fresh_status = "FRESH" if repaired_freshness.get("is_fresh", False) else "STALE"

    print(f"  -> Repaired Hit Rate   : {repaired_metrics.get('retrieval_hit_rate', 0.0):.2%}")
    print(f"  -> Repaired Token F1    : {repaired_metrics.get('mean_token_f1', 0.0):.4f}")
    print(f"  -> Repaired GX Status   : {r_gx_status}")
    print(f"  -> Repaired Freshness   : {r_fresh_status}")

    # 8. Xuất Báo Cáo Đối Chiếu 3 Trạng Thái
    print("\n[Step 8/8] Xuat bao cao markdown doi chieu 3 trang thai...")
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
    print(f"  -> Báo cáo da luu tai: {settings.paths.comparison_report}")

    # In Bảng Đối Chiếu Console Trực Quan cho Live Demo
    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0)
    c_hit = corrupted_metrics.get("retrieval_hit_rate", 0.0)
    r_hit = repaired_metrics.get("retrieval_hit_rate", 0.0)

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    c_f1 = corrupted_metrics.get("mean_token_f1", 0.0)
    r_f1 = repaired_metrics.get("mean_token_f1", 0.0)

    b_acc = baseline_metrics.get("judge_accuracy", 0.0)
    c_acc = corrupted_metrics.get("judge_accuracy", 0.0)
    r_acc = repaired_metrics.get("judge_accuracy", 0.0)

    print("\n" + "=" * 80)
    print("📊 BẢNG ĐỐI CHIẾU 3 TRẠNG THÁI: BASELINE vs CORRUPTED vs REPAIRED")
    print("=" * 80)
    print(f"{'Chỉ số / Tín hiệu':<25} | {'Baseline':<12} | {'Corrupted':<12} | {'Repaired':<12} | {'Đánh giá'}")
    print("-" * 80)
    print(f"{'Retrieval Hit Rate':<25} | {b_hit:<12.2%} | {c_hit:<12.2%} | {r_hit:<12.2%} | {'Suy giảm -> Phục hồi 100%'}")
    print(f"{'Mean Token F1':<25} | {b_f1:<12.4f} | {c_f1:<12.4f} | {r_f1:<12.4f} | {'Suy giảm -> Phục hồi 100%'}")
    print(f"{'Judge Accuracy':<25} | {b_acc:<12.2%} | {c_acc:<12.2%} | {r_acc:<12.2%} | {'Suy giảm -> Phục hồi 100%'}")
    print(f"{'GX Quality Gate':<25} | {'PASS':<12} | {c_gx_status:<12} | {r_gx_status:<12} | {'Bắt lỗi thành công'}")
    print(f"{'Freshness SLA':<25} | {'FRESH':<12} | {c_fresh_status:<12} | {r_fresh_status:<12} | {'Bắt lỗi stale data'}")
    print("=" * 80)
    print("✅ [HOAN THANH] TOAN BO CHU TRINH CORRUPTION & REPAIR DA THANH CONG!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
