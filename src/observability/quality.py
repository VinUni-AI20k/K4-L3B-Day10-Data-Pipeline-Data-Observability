from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings

import great_expectations as gx
from great_expectations.expectations import (
    ExpectTableRowCountToBeBetween,
    ExpectColumnValuesToNotBeNull,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValueLengthsToBeBetween,
)
from core.utils import write_json

def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """TODO(student): tao bo data quality checks.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = context.suites.add(gx.ExpectationSuite(name=f"papers_suite_{report_name}"))
    
    # 4 Hàng rào kiểm định bắt buộc theo spec Huong_dan.txt
    suite.add_expectation(ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    validation_result = batch.validate(suite)
    result_dict = validation_result.to_json_dict()
    success = result_dict.get("success", False)

    summary = {
        "report_name": report_name,
        "success": success,
        "total_checks": len(result_dict.get("results", [])),
        "passed_checks": sum(1 for r in result_dict.get("results", []) if r.get("success")),
        "details": result_dict,
    }

    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    else:
        report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    write_json(report_path, summary)
    return summary


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """TODO(student): tong hop freshness report.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    if df.empty or "age_days" not in df.columns:
        summary = {
            "is_fresh": False,
            "stale_rows": len(df),
            "stale_ratio": 1.0,
            "latest_published": "N/A",
            "oldest_published": "N/A",
        }
    else:
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
        total_rows = len(df)
        stale_ratio = stale_rows / total_rows if total_rows > 0 else 0.0
        is_fresh = stale_ratio <= 0.25  # Cảnh báo nếu > 25% số bài báo có age_days > 180

        summary = {
            "total_rows": total_rows,
            "stale_rows": stale_rows,
            "stale_ratio": stale_ratio,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": is_fresh,
            "latest_published": str(df["published"].max()),
            "oldest_published": str(df["published"].min()),
        }

    write_json(report_path, summary)
    return summary
