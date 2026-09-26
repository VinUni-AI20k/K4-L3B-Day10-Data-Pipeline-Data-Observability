from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run automated Great Expectations 1.x data quality checks on the dataframe."""
    context = gx.get_context(mode="ephemeral")
    # Clean unique names for data source and asset per run
    data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{report_name}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=f"papers_suite_{report_name}")

    # 1. ExpectTableRowCountToBeBetween
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=20, max_value=30))
    # 2. ExpectColumnValuesToNotBeNull
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="summary"))
    # 3. ExpectColumnValuesToBeUnique
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    # 4. ExpectColumnValueLengthsToBeBetween
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20))

    validation_result = batch.validate(suite)
    result_dict = validation_result.to_json_dict()

    # Determine report output path
    if report_name == "baseline":
        out_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        out_path = settings.paths.corrupted_quality_report
    else:
        out_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    write_json(Path(out_path), result_dict)
    return result_dict


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | None = None) -> dict[str, Any]:
    """Calculate freshness metrics and verify against Freshness SLA (stale_ratio <= 0.25)."""
    total_rows = len(df)
    if total_rows == 0:
        report = {
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": True,
        }
    else:
        latest_published = str(df["published"].max()) if "published" in df.columns else "N/A"
        oldest_published = str(df["published"].min()) if "published" in df.columns else "N/A"
        stale_threshold = settings.freshness_threshold_days
        stale_rows = int((df["age_days"] > stale_threshold).sum()) if "age_days" in df.columns else 0
        stale_ratio = stale_rows / total_rows
        is_fresh = stale_ratio <= 0.25
        report = {
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "stale_ratio": round(stale_ratio, 4),
            "is_fresh": is_fresh,
        }

    target_path = report_path or settings.paths.freshness_report
    write_json(Path(target_path), report)
    return report
