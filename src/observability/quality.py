from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Flag data as stale when more than 25% of papers exceed the age limit."""
    total_rows = len(df)
    ages = pd.to_numeric(df["age_days"], errors="coerce") if "age_days" in df else pd.Series(dtype=float)
    missing_age_rows = total_rows - int(ages.notna().sum())
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 0.0
    return {
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": 0.25,
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "missing_age_rows": missing_age_rows,
        "stale_ratio": stale_ratio,
        "is_fresh": total_rows > 0 and missing_age_rows == 0 and stale_ratio <= 0.25,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, stage: str) -> dict[str, Any]:
    """Validate the embedding input with GX 1.x and the freshness SLA."""
    freshness = evaluate_freshness_sla(df, settings)
    required_columns = {"paper_id", "title", "summary", "text_for_embedding", "age_days"}
    missing_columns = sorted(required_columns - set(df.columns))
    expectation_results: list[dict[str, Any]] = []
    blank_columns: dict[str, int] = {}
    short_summary_rows = 0

    if not missing_columns:
        context = gx.get_context(mode="ephemeral")
        data_source = context.data_sources.add_pandas(name="papers_source")
        data_asset = data_source.add_dataframe_asset(name="papers_asset")
        batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
        batch = batch_def.get_batch(batch_parameters={"dataframe": df})

        expectations = [gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)]
        expectations.extend(
            gx.expectations.ExpectColumnValuesToNotBeNull(column=column)
            for column in ("paper_id", "title", "text_for_embedding")
        )
        expectations.extend((
            gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
            gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
        ))
        for expectation in expectations:
            validation = batch.validate(expectation)
            expectation_results.append({
                "type": type(expectation).__name__,
                "column": getattr(expectation, "column", None),
                "success": bool(validation.success),
                "result": validation.to_json_dict()["result"],
            })

        for column in ("paper_id", "title", "text_for_embedding"):
            blank_count = int(df[column].fillna("").astype(str).str.strip().eq("").sum())
            if blank_count:
                blank_columns[column] = blank_count
        short_summary_rows = int(df["summary"].fillna("").astype(str).str.strip().str.len().lt(30).sum())

    gx_success = not missing_columns and all(result["success"] for result in expectation_results)
    report = {
        "stage": stage,
        "success": gx_success and not blank_columns and short_summary_rows == 0 and freshness["is_fresh"],
        "gx_success": gx_success,
        "is_fresh": freshness["is_fresh"],
        "row_count": len(df),
        "missing_columns": missing_columns,
        "blank_columns": blank_columns,
        "short_summary_rows": short_summary_rows,
        "expectations": expectation_results,
        "freshness": freshness,
    }
    report_path = settings.paths.quality_dir / f"{safe_slug(stage)}_quality_report.json"
    write_json(report_path, report)
    return report


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
    raise NotImplementedError("Student task: implement freshness reporting.")
