from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _load_dataframe(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing baseline clean dataset: {path}. Run script/run_phase1.py first."
        )

    try:
        payload = read_json(path)
        if isinstance(payload, list):
            frame = pd.DataFrame(payload)
        else:
            frame = pd.read_json(path)
    except (TypeError, ValueError):
        frame = pd.read_json(path)
    if frame.empty:
        raise ValueError(f"Clean dataset is empty: {path}")
    return frame


def _write_dataframe(frame: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)
    frame.to_json(json_path, orient="records", force_ascii=False, indent=2)


def _freshness_path(settings, state: str) -> Path:
    return settings.paths.quality_dir / f"{state}_freshness_report.json"


def _metric_value(metrics: dict[str, Any], name: str) -> str:
    value = metrics.get(name, "n/a")
    if isinstance(value, (int, float)):
        return f"{value:.4f}"
    return str(value)


def _print_comparison(
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    rows = [
        ("retrieval_hit_rate", baseline_metrics, corrupted_metrics, repaired_metrics),
        ("mean_token_f1", baseline_metrics, corrupted_metrics, repaired_metrics),
        ("judge_accuracy", baseline_metrics, corrupted_metrics, repaired_metrics),
        ("mean_judge_score", baseline_metrics, corrupted_metrics, repaired_metrics),
        (
            "quality_success",
            {"quality_success": "n/a"},
            {"quality_success": corrupted_quality.get("success", "n/a")},
            {"quality_success": repaired_quality.get("success", "n/a")},
        ),
        (
            "freshness_is_fresh",
            {"freshness_is_fresh": "n/a"},
            {"freshness_is_fresh": corrupted_freshness.get("is_fresh", "n/a")},
            {"freshness_is_fresh": repaired_freshness.get("is_fresh", "n/a")},
        ),
    ]
    print("\nBaseline vs Corrupted vs Repaired")
    print(f"{'Metric':<24} {'Baseline':>12} {'Corrupted':>12} {'Repaired':>12}")
    print("-" * 64)
    for name, baseline, corrupted, repaired in rows:
        print(
            f"{name:<24} "
            f"{_metric_value(baseline, name):>12} "
            f"{_metric_value(corrupted, name):>12} "
            f"{_metric_value(repaired, name):>12}"
        )


def repair_from_raw_snapshot(settings: Settings) -> pd.DataFrame:
    """Rebuild the serving dataframe from the immutable raw snapshot.

    Repair deliberately does not try to reverse individual mutations in the
    corrupted dataframe. Re-parsing the raw records and running the normal
    cleaning contract makes the operation safe to repeat and preserves the
    corrupted artifacts for the three-state comparison.
    """

    raw_path = settings.paths.raw_records_json
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing raw snapshot for repair: {raw_path}")

    raw_records = load_raw_records(raw_path)
    repaired_df = build_clean_dataframe(raw_records, datetime.now(UTC))
    if repaired_df.empty:
        raise ValueError("Repair produced an empty dataframe from the raw snapshot.")

    _write_dataframe(
        repaired_df,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
    )
    return repaired_df


def run_corruption_flow_pipeline(settings: Settings) -> dict[str, Any]:
    """Run Phase 2: corrupt, measure, repair from raw, and compare.

    Baseline artifacts and the evaluation set are treated as immutable inputs.
    Repair always rebuilds the clean dataframe from the raw snapshot instead
    of attempting to reverse mutations in the corrupted dataframe.
    """

    paths = settings.paths

    baseline_df = _load_dataframe(paths.clean_json)
    if not paths.baseline_metrics.exists():
        raise FileNotFoundError(
            f"Missing baseline metrics: {paths.baseline_metrics}. Run script/run_phase1.py first."
        )
    baseline_metrics = read_json(paths.baseline_metrics)
    if not isinstance(baseline_metrics, dict):
        raise ValueError(f"Baseline metrics must be a JSON object: {paths.baseline_metrics}")

    corrupted_df = corrupt_clean_dataframe(baseline_df, paths.corruption_log)
    _write_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        _freshness_path(settings, "corrupted"),
    )
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        paths.corrupted_embeddings_json,
    )
    corrupted_bundle = evaluate_pipeline(
        settings,
        corrupted_index,
        paths.eval_testset,
        paths.corrupted_metrics,
        paths.corrupted_answers,
    )

    repaired_df = repair_from_raw_snapshot(settings)
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        _freshness_path(settings, "repaired"),
    )
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings,
        repaired_index,
        paths.eval_testset,
        paths.repaired_metrics,
        paths.repaired_answers,
    )

    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    if not paths.comparison_report.exists():
        raise RuntimeError(
            f"Corruption comparison report was not created: {paths.comparison_report}"
        )
    _print_comparison(
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    return {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_bundle.summary,
        "repaired_metrics": repaired_bundle.summary,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
        "corrupted_freshness": corrupted_freshness,
        "repaired_freshness": repaired_freshness,
        "comparison_report": str(paths.comparison_report),
    }


def main() -> None:
    """CLI entrypoint for ``python script/run_corruption_flow.py``."""

    run_corruption_flow_pipeline(load_settings())
