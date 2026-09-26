from __future__ import annotations

import json
from typing import Any

import pandas as pd
try:
    import great_expectations as gx
    import great_expectations.expectations as gxe
    GX_AVAILABLE = True
except ImportError:
    GX_AVAILABLE = False


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    
    if GX_AVAILABLE:
        context = gx.get_context(mode="ephemeral")
        data_source = context.data_sources.add_pandas(name="papers_source")
        data_asset = data_source.add_dataframe_asset(name="papers_asset")
        batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
        
        suite = context.suites.add(gx.ExpectationSuite(name="papers_suite"))
        suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=1, max_value=100))
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
        suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
        suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=1, max_value=10000))
        
        validation_definition = context.validation_definitions.add(
            gx.ValidationDefinition(name="papers_validation", data=batch_def, suite=suite)
        )
        validation_result = validation_definition.run(batch_parameters={"dataframe": df})
        gx_success = validation_result.success
    else:
        gx_success = True
        
    success = gx_success and freshness["is_fresh"]
    
    res = {
        "success": success,
        "gx_success": gx_success,
        "freshness": freshness
    }
    
    report_path = getattr(settings.paths, f"{report_name}_quality_report", settings.paths.baseline_quality_report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    return res


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    if df.empty:
        res = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": False
        }
    else:
        latest = str(df["published"].max())
        oldest = str(df["published"].min())
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
        total_rows = len(df)
        is_fresh = (stale_rows / total_rows) <= 0.25 if total_rows > 0 else False
        
        res = {
            "latest_published": latest,
            "oldest_published": oldest,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "is_fresh": is_fresh
        }
        
    if report_path:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
            
    return res
