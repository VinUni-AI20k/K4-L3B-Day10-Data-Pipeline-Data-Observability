from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from core.config import load_settings
from ingestion.crossref import fetch_source_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks


def main() -> None:
    settings = load_settings()
    
    records = fetch_source_records(settings)
    
    run_date = datetime.now(timezone.utc)
    df = build_clean_dataframe(records, run_date)
    
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(settings.paths.clean_csv, index=False)
    df.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=False)
    
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json
    )
    
    build_test_set(df, settings.paths.eval_testset)
    
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers
    )
    
    quality_res = run_data_quality_checks(df, settings, "baseline")
    
    report_content = f"""# Phase 1: Baseline Report
    
## Data Observability Quality Checks
- **Overall Success**: `{quality_res['success']}`
- **Great Expectations Validations**: `{quality_res['gx_success']}`
- **Freshness SLA**: `{quality_res['freshness']['is_fresh']}` ({quality_res['freshness']['stale_rows']} stale rows out of {quality_res['freshness']['total_rows']})

## Retrieval-Augmented Generation Metrics
- **Test Samples Evaluated**: {bundle.summary['samples']}
- **Retrieval Hit Rate**: {bundle.summary['retrieval_hit_rate']:.4f}
- **Mean Token F1 Score**: {bundle.summary['mean_token_f1']:.4f}
- **LLM-as-a-Judge Accuracy**: {bundle.summary['judge_accuracy']:.4f}
- **Mean Judge Score (1-5)**: {bundle.summary['mean_judge_score']:.4f}
"""
    settings.paths.baseline_report.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.baseline_report, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Phase 1 completed. Report saved to {settings.paths.baseline_report}")
