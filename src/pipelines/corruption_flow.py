from __future__ import annotations

from pathlib import Path
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
from retrieval.index import LocalEmbeddingIndex


def _require(path: Path, hint: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. {hint}")


def _load_baseline(settings: Settings) -> tuple[dict[str, Any], pd.DataFrame]:
    """Load baseline metrics va clean dataset do phase 1 tao ra."""
    paths = settings.paths
    hint = "Run phase 1 first (python script/run_phase1.py)."
    for path in (paths.baseline_metrics, paths.clean_json, paths.eval_testset, paths.raw_records_json):
        _require(path, hint)
    baseline_metrics = read_json(paths.baseline_metrics)
    clean_df = pd.DataFrame(read_json(paths.clean_json))
    if clean_df.empty:
        raise RuntimeError("Baseline clean dataset is empty; re-run phase 1.")
    return baseline_metrics, clean_df


def _save_dataset(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def _evaluate(settings: Settings, df: pd.DataFrame, embeddings_path: Path, metrics_path: Path, answers_path: Path, label: str) -> dict[str, Any]:
    """Rebuild Chroma collection cho dataset va evaluate tren test set co dinh."""
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=embeddings_path)
    print(f"[corruption] {label}: indexed {len(index.documents)} documents into '{index.collection_name}'")
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=metrics_path,
        answers_output_path=answers_path,
    )
    metrics = evaluation.summary
    print(
        f"[corruption] {label}: hit_rate={metrics['retrieval_hit_rate']:.3f} "
        f"token_f1={metrics['mean_token_f1']:.3f}"
    )
    return metrics


def _observe(settings: Settings, df: pd.DataFrame, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Chay quality checks + freshness report cho mot dataset."""
    quality = run_data_quality_checks(df, settings, report_name=label)
    freshness_path = settings.paths.quality_dir / f"{label}_freshness_report.json"
    freshness = build_freshness_report(df, settings, freshness_path)
    print(f"[corruption] {label}: quality success={quality.get('success')} | fresh={freshness.get('is_fresh')}")
    return quality, freshness


def main() -> None:
    settings = load_settings()
    paths = settings.paths
    run_date = now_utc()

    # 1. Load baseline metrics va clean dataset.
    baseline_metrics, clean_df = _load_baseline(settings)
    print(f"[corruption] Baseline rows: {len(clean_df)}")

    # 2. Tao corrupted dataframe.
    corrupted_df = corrupt_clean_dataframe(clean_df.copy(), paths.corruption_log)
    print(f"[corruption] Corrupted rows: {len(corrupted_df)} (log -> {paths.corruption_log})")

    # 3. Save corrupted artifacts.
    _save_dataset(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)

    # 4. Rebuild index va evaluate tren corrupted data.
    corrupted_metrics = _evaluate(
        settings,
        corrupted_df,
        paths.corrupted_embeddings_json,
        paths.corrupted_metrics,
        paths.corrupted_answers,
        label="corrupted",
    )

    # 5. Run quality checks/freshness tren corrupted data.
    corrupted_quality, corrupted_freshness = _observe(settings, corrupted_df, "corrupted")

    # 6. Repair lai tu raw records (chay lai cleaning pipeline tu snapshot raw).
    records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(records, run_date)
    if repaired_df.empty:
        raise RuntimeError("Repaired dataframe is empty; check raw source data.")
    _save_dataset(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    print(f"[corruption] Repaired rows: {len(repaired_df)} from {len(records)} raw records")

    # 7. Evaluate repaired dataset.
    repaired_metrics = _evaluate(
        settings,
        repaired_df,
        paths.repaired_embeddings_json,
        paths.repaired_metrics,
        paths.repaired_answers,
        label="repaired",
    )
    repaired_quality, repaired_freshness = _observe(settings, repaired_df, "repaired")

    # 8. Tao comparison report.
    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_metrics,
        repaired_metrics,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    print(f"[corruption] Report -> {paths.comparison_report}")
