from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd
from great_expectations.expectations.core import (
    ExpectColumnValueLengthsToBeBetween,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToNotBeNull,
    ExpectTableRowCountToBeBetween,
)

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the required Great Expectations 1.x checks and freshness SLA."""
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    expectations = {
        "row_count": ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        "paper_id_not_null": ExpectColumnValuesToNotBeNull(column="paper_id"),
        "title_not_null": ExpectColumnValuesToNotBeNull(column="title"),
        "text_for_embedding_not_null": ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        "paper_id_unique": ExpectColumnValuesToBeUnique(column="paper_id"),
        "summary_length": ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    }
    expectation_results = {}
    for name, expectation in expectations.items():
        validation = batch.validate(expectation)
        expectation_results[name] = validation.to_json_dict()

    freshness = evaluate_freshness_sla(df, settings)
    result = {
        "success": all(item["success"] for item in expectation_results.values()) and freshness["is_fresh"],
        "stage": report_name,
        "expectations": expectation_results,
        "freshness": freshness,
    }
    report_path = _quality_report_path(settings, report_name)
    write_json(report_path, result)
    return result


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Return freshness metrics and flag datasets with more than 25% stale rows."""
    total_rows = len(df)
    ages = pd.to_numeric(df.get("age_days", pd.Series(dtype="float64")), errors="coerce")
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    published = pd.to_datetime(df.get("published", pd.Series(dtype="object")), errors="coerce").dropna()
    return {
        "latest_published": published.max().date().isoformat() if not published.empty else None,
        "oldest_published": published.min().date().isoformat() if not published.empty else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": 0.25,
        "is_fresh": total_rows > 0 and stale_ratio <= 0.25,
    }


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and persist the standalone freshness report."""
    result = evaluate_freshness_sla(df, settings)
    write_json(report_path, result)
    return result


def _quality_report_path(settings: Settings, report_name: str):
    if report_name == "baseline":
        return settings.paths.baseline_quality_report
    if report_name == "corrupted":
        return settings.paths.corrupted_quality_report
    return settings.paths.quality_dir / f"{report_name}_quality_report.json"
