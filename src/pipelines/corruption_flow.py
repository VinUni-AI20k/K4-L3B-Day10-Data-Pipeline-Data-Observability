from __future__ import annotations

import json
from typing import Any

from core.config import Settings, load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _run_stage(settings: Settings, dataframe, *, stage: str, clean_path, embedding_path, metrics_path, answers_path):
    write_csv(dataframe, clean_path)
    write_json(clean_path.with_suffix(".json"), dataframe.to_dict(orient="records"))
    index = LocalEmbeddingIndex.build(dataframe, settings, embedding_path)
    metrics = evaluate_pipeline(settings, index, settings.paths.eval_testset, metrics_path, answers_path)
    quality = run_data_quality_checks(dataframe, settings, stage)
    freshness_path = settings.paths.quality_dir / f"{stage}_freshness_report.json"
    freshness = build_freshness_report(dataframe, settings, freshness_path)
    return metrics.summary, quality, freshness


def run_corruption_flow(settings: Settings) -> dict[str, Any]:
    """Corrupt the clean data, then rebuild and evaluate a repaired copy from raw data."""
    if not settings.paths.clean_csv.exists() or not settings.paths.eval_testset.exists():
        raise FileNotFoundError("Run `python script/run_phase1.py` before the corruption flow.")

    import pandas as pd

    clean_df = pd.read_csv(settings.paths.clean_csv)
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    corrupted_metrics, corrupted_quality, corrupted_freshness = _run_stage(
        settings,
        corrupted_df,
        stage="corrupted",
        clean_path=settings.paths.corrupted_clean_csv,
        embedding_path=settings.paths.corrupted_embeddings_json,
        metrics_path=settings.paths.corrupted_metrics,
        answers_path=settings.paths.corrupted_answers,
    )

    repaired_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(repaired_records, now_utc())
    repaired_metrics, repaired_quality, repaired_freshness = _run_stage(
        settings,
        repaired_df,
        stage="repaired",
        clean_path=settings.paths.repaired_clean_csv,
        embedding_path=settings.paths.repaired_embeddings_json,
        metrics_path=settings.paths.repaired_metrics,
        answers_path=settings.paths.repaired_answers,
    )

    baseline_metrics = json.loads(settings.paths.baseline_metrics.read_text(encoding="utf-8"))
    baseline_quality = json.loads(settings.paths.baseline_quality_report.read_text(encoding="utf-8"))
    baseline_freshness = json.loads(settings.paths.freshness_report.read_text(encoding="utf-8"))
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_metrics,
        repaired_metrics,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
        baseline_quality,
        baseline_freshness,
    )
    return {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_metrics,
        "repaired_metrics": repaired_metrics,
        "comparison_report": str(settings.paths.comparison_report),
    }


def main() -> None:
    result = run_corruption_flow(load_settings())
    print("Corruption and repair flow completed")
    print(f"Corrupted retrieval hit rate: {result['corrupted_metrics']['retrieval_hit_rate']}")
    print(f"Repaired retrieval hit rate: {result['repaired_metrics']['retrieval_hit_rate']}")
    print(f"Comparison report: {result['comparison_report']}")
