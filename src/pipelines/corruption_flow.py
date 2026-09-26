from __future__ import annotations

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def repair_from_raw_snapshot(settings: Settings) -> pd.DataFrame:
    """Idempotent repair: rebuild lai dataframe sach truc tiep tu raw snapshot dang tin cay.

    Vi ham nay luon doc lai tu `data/raw/crossref_records.json` (khong dua tren
    ban corrupted), goi lai nhieu lan cho ket qua giong het nhau -> idempotent.
    """
    records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(records, now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    repaired_df.to_json(
        settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=False
    )
    return repaired_df


def main() -> None:
    """Corruption -> Evaluate -> Repair -> Compare flow."""
    settings = load_settings()

    # 1. Load baseline metrics va clean dataset.
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_json.exists():
        raise RuntimeError(
            "Khong tim thay baseline artifacts. Hay chay `python script/run_phase1.py` truoc."
        )
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_df = pd.read_json(settings.paths.clean_json)
    print(f"[CorruptionFlow] Da load baseline: {len(baseline_df)} dong.")

    # 2-3. Tao corrupted dataframe va luu artifacts.
    corrupted_df = corrupt_clean_dataframe(baseline_df.copy(), settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    corrupted_df.to_json(
        settings.paths.corrupted_clean_json, orient="records", indent=2, force_ascii=False
    )
    print(f"[CorruptionFlow] Da luu corrupted dataset: {len(corrupted_df)} dong.")

    # 4. Rebuild index va evaluate tren du lieu bi loi.
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, embeddings_output_path=settings.paths.corrupted_embeddings_json
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(
        "[CorruptionFlow] Corrupted metrics -> "
        f"hit_rate={corrupted_bundle.summary['retrieval_hit_rate']:.2f}, "
        f"token_f1={corrupted_bundle.summary['mean_token_f1']:.2f}"
    )

    # 5. Quality checks / freshness tren corrupted data.
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name="corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.freshness_report
    )
    print(f"[CorruptionFlow] Corrupted quality status = {corrupted_quality.get('success')}")

    # 6. Repair lai tu raw records (idempotent).
    repaired_df = repair_from_raw_snapshot(settings)
    print(f"[CorruptionFlow] Da phuc hoi dataset: {len(repaired_df)} dong.")

    # 7. Evaluate repaired dataset.
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, embeddings_output_path=settings.paths.repaired_embeddings_json
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name="repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.freshness_report
    )
    print(
        "[CorruptionFlow] Repaired metrics -> "
        f"hit_rate={repaired_bundle.summary['retrieval_hit_rate']:.2f}, "
        f"token_f1={repaired_bundle.summary['mean_token_f1']:.2f}"
    )

    # 8. Tao comparison report (Baseline vs Corrupted vs Repaired).
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
    print(f"[CorruptionFlow] Da ghi comparison report tai {settings.paths.comparison_report}")


if __name__ == "__main__":
    main()
