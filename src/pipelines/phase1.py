from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from core.config import Settings, load_settings
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(settings: Settings | None = None) -> dict[str, Any]:
    """Execute end-to-end Phase 1 Baseline Data Pipeline."""
    s = settings or load_settings()

    # 1. Fetch source records
    records = fetch_source_records(s)

    # 2. Clean records into DataFrame
    df = build_clean_dataframe(records, datetime.now(timezone.utc))

    # 3. Save clean dataset
    s.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(s.paths.clean_csv, index=False)
    df.to_json(s.paths.clean_json, orient="records", indent=2, force_ascii=False)

    # 4. Build ChromaDB index
    index = LocalEmbeddingIndex.build(df, s, s.paths.embeddings_json)

    # 5. Build evaluation test set
    test_set = build_test_set(df, s.paths.eval_testset)

    # 6. Evaluate baseline RAG
    eval_bundle = evaluate_pipeline(
        settings=s,
        index=index,
        test_set_path=s.paths.eval_testset,
        metrics_output_path=s.paths.baseline_metrics,
        answers_output_path=s.paths.baseline_answers,
    )

    # 7. Run Data Quality Gate (Great Expectations 1.x & Freshness)
    quality_result = run_data_quality_checks(df, s, stage="baseline")

    # 8. Generate Phase 1 Report
    s.paths.baseline_report.parent.mkdir(parents=True, exist_ok=True)
    report_md = f"""# Phase 1 Baseline Report — Data Pipeline & Observability

- **Execution Date:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **Total Clean Records:** {len(df)}
- **Data Quality Status:** `{"PASS" if quality_result["success"] else "FAIL"}` (GX 1.x)
- **Data Freshness SLA:** `{"FRESH" if quality_result["is_fresh"] else "STALE"}` (Threshold: {s.freshness_threshold_days} days)

## 📊 Evaluation Benchmarks (Baseline)

| Metric | Score |
| :--- | :---: |
| **Retrieval Hit Rate** | {eval_bundle.summary["retrieval_hit_rate"]:.2%} |
| **Mean Token F1** | {eval_bundle.summary["mean_token_f1"]:.4f} |
| **Judge Accuracy** | {eval_bundle.summary["judge_accuracy"]:.2%} |
| **Mean Judge Score** | {eval_bundle.summary["mean_judge_score"]:.2f} / 5.0 |

---
*Report generated automatically by Phase 1 Pipeline.*
"""
    with open(s.paths.baseline_report, "w", encoding="utf-8") as f:
        f.write(report_md)

    print("Phase 1 Baseline Pipeline completed successfully!")
    print(f"Artifacts generated: {s.paths.baseline_metrics}, {s.paths.baseline_report}")
    return eval_bundle.summary


def main() -> None:
    run_phase1_pipeline()


if __name__ == "__main__":
    main()
