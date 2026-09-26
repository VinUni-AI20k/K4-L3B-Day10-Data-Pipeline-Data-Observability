from __future__ import annotations

import json
import logging
from typing import Any
import pandas as pd
import great_expectations as gx

from core.config import Settings

logger = logging.getLogger(__name__)


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Evaluate data freshness SLA based on age_days."""
    total_rows = len(df)
    if total_rows == 0:
        return {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "total_rows": 0,
            "is_fresh": True,
        }

    published_series = df["published"]
    latest_published = str(published_series.max())
    oldest_published = str(published_series.min())

    threshold = settings.freshness_threshold_days
    stale_mask = df["age_days"] > threshold
    stale_rows = int(stale_mask.sum())
    stale_ratio = float(stale_rows / total_rows)

    # Cảnh báo is_fresh = False nếu tỷ lệ bài báo cũ (> 180 ngày) vượt quá 25% (0.25)
    is_fresh = bool(stale_ratio <= 0.25)

    return {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "total_rows": total_rows,
        "is_fresh": is_fresh,
    }


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Any = None) -> dict[str, Any]:
    """Generate and save freshness report payload."""
    report = evaluate_freshness_sla(df, settings)
    target_path = report_path or settings.paths.freshness_report
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, stage: str = "baseline") -> dict[str, Any]:
    """Run Data Quality Gate using Great Expectations 1.x Ephemeral Context."""
    # Build Expectation Suite using Great Expectations 1.x
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{stage}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{stage}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{stage}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # Add 4 mandatory expectations
    expectation_suite_name = f"papers_suite_{stage}"
    suite = context.suites.add(gx.ExpectationSuite(name=expectation_suite_name))

    exp1 = gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)
    exp2_id = gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id")
    exp2_title = gx.expectations.ExpectColumnValuesToNotBeNull(column="title")
    exp2_text = gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding")
    exp3 = gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id")
    exp4 = gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30)

    for exp in [exp1, exp2_id, exp2_title, exp2_text, exp3, exp4]:
        suite.add_expectation(exp)

    # Validate batch against suite
    validation_result = batch.validate(suite)

    # Extract success
    gx_success = bool(validation_result.success)

    # Freshness check
    freshness_report = build_freshness_report(df, settings, settings.paths.freshness_report)

    overall_success = bool(gx_success and freshness_report["is_fresh"])

    result_payload = {
        "stage": stage,
        "success": overall_success,
        "gx_success": gx_success,
        "is_fresh": freshness_report["is_fresh"],
        "total_records": len(df),
        "freshness": freshness_report,
        "validation_result": validation_result.to_json_dict(),
    }

    # Write report file
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    report_file = settings.paths.quality_dir / f"{stage}_quality_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(result_payload, f, ensure_ascii=False, indent=2)

    return result_payload
