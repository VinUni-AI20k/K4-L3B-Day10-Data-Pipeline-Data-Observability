from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import run_phase1_pipeline
from retrieval.index import LocalEmbeddingIndex


def repair_from_raw_snapshot(settings: Settings, run_date: datetime | None = None) -> pd.DataFrame:
    """Khôi phục dữ liệu sạch an toàn và có tính Idempotent từ snapshot thô ban đầu."""
    if run_date is None:
        run_date = now_utc()
    raw_path = settings.paths.raw_records_json
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw snapshot not found at {raw_path}")

    raw_records = load_raw_records(raw_path)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    return repaired_df


def run_corruption_flow_pipeline(settings: Settings) -> dict[str, Any]:
    """Toàn tuyến Phase 2:
    1. Đo lường hiện tượng Silent Failure trên tập dữ liệu bị làm bẩn (Corrupted).
    2. Kích hoạt cơ chế Idempotent Repair từ snapshot thô ban đầu.
    3. Tái đánh giá hệ thống và xuất báo cáo đối chiếu 3 trạng thái.
    """
    # 1. Đảm bảo đã có dữ liệu Baseline (hoặc tự động chạy Phase 1 nếu chưa có)
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_json.exists():
        print("--> Chạy thiết lập Baseline Phase 1...")
        run_phase1_pipeline(settings)

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)

    # 2. Tiêm lỗi dữ liệu và lưu artifacts corrupted
    print("--> 1. Tiêm 6 sự cố dữ liệu thực nghiệm (Corrupting clean data)...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    # Chạy Observability Quality Gate trên dữ liệu bẩn
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness_report.json"
    )

    # Nạp dữ liệu bẩn vào ChromaDB collection 'papers-corrupted'
    print("--> Nạp vector index cho tập dữ liệu bẩn (Chroma collection: papers-corrupted)...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    # Đánh giá sự suy giảm hiệu năng của AI (Silent Failure)
    print("--> Đo lường suy giảm RAG trên dữ liệu bẩn...")
    corrupted_eval = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_eval.summary

    # 3. Kích hoạt cơ chế tự phục hồi Idempotent Repair từ raw snapshot
    print("--> 2. Kích hoạt cơ chế tự phục hồi (Idempotent Repair từ raw snapshot)...")
    repaired_df = repair_from_raw_snapshot(settings)

    # Chạy Observability Quality Gate trên dữ liệu đã phục hồi
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness_report.json"
    )

    # Nạp dữ liệu phục hồi vào ChromaDB collection 'papers-repaired'
    print("--> Nạp vector index cho tập phục hồi (Chroma collection: papers-repaired)...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    # Tái đánh giá hệ thống sau phục hồi
    print("--> Tái đánh giá hiệu năng RAG sau phục hồi...")
    repaired_eval = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_eval.summary

    # 4. Xuất báo cáo so sánh 3 trạng thái
    print(f"--> 3. Xuất báo cáo đối chiếu 3 trạng thái tại {settings.paths.comparison_report}...")
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

    # 5. In bảng đối chiếu 3 cột rõ ràng trên Console
    _print_comparison_table(
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    return {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_metrics,
        "repaired_metrics": repaired_metrics,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
        "corrupted_freshness": corrupted_freshness,
        "repaired_freshness": repaired_freshness,
        "report_path": str(settings.paths.comparison_report),
    }


def _print_comparison_table(
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0)
    c_hit = corrupted_metrics.get("retrieval_hit_rate", 0.0)
    r_hit = repaired_metrics.get("retrieval_hit_rate", 0.0)

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    c_f1 = corrupted_metrics.get("mean_token_f1", 0.0)
    r_f1 = repaired_metrics.get("mean_token_f1", 0.0)

    b_acc = baseline_metrics.get("judge_accuracy", 0.0)
    c_acc = corrupted_metrics.get("judge_accuracy", 0.0)
    r_acc = repaired_metrics.get("judge_accuracy", 0.0)

    b_score = baseline_metrics.get("mean_judge_score", 0.0)
    c_score = corrupted_metrics.get("mean_judge_score", 0.0)
    r_score = repaired_metrics.get("mean_judge_score", 0.0)

    c_gate = "PASS" if corrupted_quality.get("success", False) else "FAIL"
    r_gate = "PASS" if repaired_quality.get("success", True) else "FAIL"

    c_fresh = "Fresh" if corrupted_freshness.get("is_fresh", False) else "Stale Alert"
    r_fresh = "Fresh" if repaired_freshness.get("is_fresh", True) else "Stale Alert"

    print("\n" + "=" * 80)
    print("                     3-STATE OBSERVABILITY COMPARISON TABLE")
    print("=" * 80)
    print(f"{'Metric / Signal':<26} {'1. Baseline':<16} {'2. Corrupted':<18} {'3. Repaired':<16}")
    print("-" * 80)
    print(f"{'Retrieval Hit Rate':<26} {f'{b_hit * 100:.1f}%':<16} {f'{c_hit * 100:.1f}%':<18} {f'{r_hit * 100:.1f}%':<16}")
    print(f"{'Mean Token F1':<26} {f'{b_f1:.4f}':<16} {f'{c_f1:.4f}':<18} {f'{r_f1:.4f}':<16}")
    print(f"{'Judge Accuracy':<26} {f'{b_acc * 100:.1f}%':<16} {f'{c_acc * 100:.1f}%':<18} {f'{r_acc * 100:.1f}%':<16}")
    print(f"{'Mean Judge Score':<26} {f'{b_score:.2f}':<16} {f'{c_score:.2f}':<18} {f'{r_score:.2f}':<16}")
    print(f"{'Data Quality Gate':<26} {'PASS':<16} {c_gate:<18} {r_gate:<16}")
    print(f"{'Freshness SLA':<26} {'Fresh':<16} {c_fresh:<18} {r_fresh:<16}")
    print("=" * 80)
    print("Tín hiệu hoàn thành: Đã xuất báo cáo đối chiếu tại data/reports/corruption_report.md\n")


def main() -> None:
    settings = load_settings()
    run_corruption_flow_pipeline(settings)
