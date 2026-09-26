from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay data quality checks bang Great Expectations 1.x ephemeral mode."""
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{report_name}")

    suite_name = f"papers_quality_{report_name}"
    suite = context.suites.add(gx.ExpectationSuite(name=suite_name))

    # 4 Expectations thiet yeu theo chuan GX 1.x
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=20, max_value=30))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=10))

    val_def = context.validation_definitions.add(
        gx.ValidationDefinition(name=f"papers_validation_{report_name}", data=batch_def, suite=suite)
    )

    result = val_def.run(batch_parameters={"dataframe": df})
    gx_success = bool(result.success)

    # Tinh toan Freshness SLA: ty le age_days > 180 khong vuot qua 25%
    total_rows = len(df)
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0
    stale_ratio = (stale_rows / total_rows) if total_rows > 0 else 0.0
    is_fresh = stale_ratio <= 0.25

    overall_success = gx_success and is_fresh

    failed_expectations: list[str] = []
    for item in result.results:
        if not item.success:
            exp_type = getattr(item.expectation_config, "type", str(type(item.expectation_config)))
            failed_expectations.append(exp_type)

    report_payload = {
        "report_name": report_name,
        "success": overall_success,
        "gx_success": gx_success,
        "is_fresh": is_fresh,
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "failed_expectations": failed_expectations,
        "statistics": {
            "evaluated_expectations": len(suite.expectations),
            "successful_expectations": len(suite.expectations) - len(failed_expectations),
            "unsuccessful_expectations": len(failed_expectations),
        },
    }

    # Xac dinh output path
    output_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    if report_name == "baseline":
        output_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        output_path = settings.paths.corrupted_quality_report
    write_json(output_path, report_payload)

    return report_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report theo SLA 180 ngay."""
    total_rows = len(df)
    latest_published = str(df["published"].max()) if not df.empty and "published" in df.columns else ""
    oldest_published = str(df["published"].min()) if not df.empty and "published" in df.columns else ""

    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0
    stale_ratio = (stale_rows / total_rows) if total_rows > 0 else 0.0
    is_fresh = stale_ratio <= 0.25

    report_payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": is_fresh,
    }

    write_json(Path(report_path), report_payload)
    return report_payload

