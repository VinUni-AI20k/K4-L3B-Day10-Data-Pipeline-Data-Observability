from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from core.config import load_settings
from core.utils import read_json
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks


def main() -> None:
    settings = load_settings()
    
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    df = pd.read_json(settings.paths.clean_json)
    
    corrupted_df = corrupt_clean_dataframe(df, settings.paths.corruption_log)
    
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df.to_csv(settings.paths.corrupted_clean_csv, index=False)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2, force_ascii=False)
    
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json
    )
    
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers
    )
    
    run_data_quality_checks(corrupted_df, settings, "corrupted")
    
    records = load_raw_records(settings.paths.raw_records_json)
    run_date = datetime.now(timezone.utc)
    repaired_df = build_clean_dataframe(records, run_date)
    
    repaired_df.to_csv(settings.paths.repaired_clean_csv, index=False)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=False)
    
    repaired_index = LocalEmbeddingIndex.build(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json
    )
    
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers
    )
    
    report_content = f"""# Data Corruption & Self-Healing Report

| Metric | Baseline (Healthy) | Corrupted (Silent Failure) | Repaired (Self-Healed) |
|---|---|---|---|
| Retrieval Hit Rate | {baseline_metrics.get('retrieval_hit_rate', 0.0):.4f} | {corrupted_bundle.summary.get('retrieval_hit_rate', 0.0):.4f} | {repaired_bundle.summary.get('retrieval_hit_rate', 0.0):.4f} |
| Mean Token F1 Score | {baseline_metrics.get('mean_token_f1', 0.0):.4f} | {corrupted_bundle.summary.get('mean_token_f1', 0.0):.4f} | {repaired_bundle.summary.get('mean_token_f1', 0.0):.4f} |
| LLM Judge Accuracy | {baseline_metrics.get('judge_accuracy', 0.0):.4f} | {corrupted_bundle.summary.get('judge_accuracy', 0.0):.4f} | {repaired_bundle.summary.get('judge_accuracy', 0.0):.4f} |
"""
    settings.paths.comparison_report.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.comparison_report, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Flow completed. Comparison report saved to {settings.paths.comparison_report}")
