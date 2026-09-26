from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run Great Expectations 1.x data quality checks on the dataframe.

    Checks:
    1. Row count between 1 and 10000
    2. paper_id not null and unique
    3. title not null
    4. summary length between 10 and 5000 chars
    5. text_for_embedding not null

    Writes result JSON to data/quality/<report_name>.json
    """
    import great_expectations as gx

    results_list: list[dict[str, Any]] = []
    overall_success = True

    try:
        # GX 1.x ephemeral context
        context = gx.get_context(mode="ephemeral")
        data_source = context.data_sources.add_pandas(name="papers_source")
        data_asset = data_source.add_dataframe_asset(name="papers_asset")
        batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
        batch = batch_def.get_batch(batch_parameters={"dataframe": df})

        expectations = [
            gx.expectations.ExpectTableRowCountToBeBetween(min_value=1, max_value=10000),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
            gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
            gx.expectations.ExpectColumnValueLengthsToBeBetween(
                column="summary", min_value=10, max_value=5000
            ),
        ]

        for exp in expectations:
            try:
                result = batch.validate(exp)
                success = bool(result.success)
                results_list.append(
                    {
                        "expectation_type": type(exp).__name__,
                        "success": success,
                        "result": str(result.result),
                    }
                )
                if not success:
                    overall_success = False
            except Exception as exc:
                results_list.append(
                    {
                        "expectation_type": type(exp).__name__,
                        "success": False,
                        "result": f"Error: {exc}",
                    }
                )
                overall_success = False

    except Exception as exc:
        # Fallback: manual checks without GX
        overall_success, results_list = _manual_quality_checks(df)
        results_list.insert(
            0, {"expectation_type": "GX_INIT", "success": False, "result": f"GX unavailable: {exc}. Used manual checks."}
        )

    payload: dict[str, Any] = {
        "report_name": report_name,
        "success": overall_success,
        "row_count": len(df),
        "results": results_list,
    }

    output_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(output_path, payload)

    return payload


def _manual_quality_checks(df: pd.DataFrame) -> tuple[bool, list[dict[str, Any]]]:
    """Fallback quality checks without Great Expectations."""
    results: list[dict[str, Any]] = []
    overall = True

    def check(name: str, passed: bool, detail: str) -> None:
        nonlocal overall
        results.append({"expectation_type": name, "success": passed, "result": detail})
        if not passed:
            overall = False

    check("ExpectTableRowCountToBeBetween",
          1 <= len(df) <= 10000,
          f"row_count={len(df)}")

    null_paper_id = int(df["paper_id"].isna().sum()) if "paper_id" in df.columns else len(df)
    check("ExpectColumnValuesToNotBeNull(paper_id)",
          null_paper_id == 0,
          f"null_count={null_paper_id}")

    dup_paper_id = int(df["paper_id"].duplicated().sum()) if "paper_id" in df.columns else 0
    check("ExpectColumnValuesToBeUnique(paper_id)",
          dup_paper_id == 0,
          f"duplicate_count={dup_paper_id}")

    null_title = int(df["title"].isna().sum()) if "title" in df.columns else len(df)
    check("ExpectColumnValuesToNotBeNull(title)",
          null_title == 0,
          f"null_count={null_title}")

    null_embed = int(df["text_for_embedding"].isna().sum()) if "text_for_embedding" in df.columns else len(df)
    check("ExpectColumnValuesToNotBeNull(text_for_embedding)",
          null_embed == 0,
          f"null_count={null_embed}")

    if "summary" in df.columns:
        lengths = df["summary"].fillna("").str.len()
        bad = int(((lengths < 10) | (lengths > 5000)).sum())
        check("ExpectColumnValueLengthsToBeBetween(summary, 10, 5000)",
              bad == 0,
              f"out_of_range={bad}")

    return overall, results


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build freshness SLA report.

    Computes:
    - latest_published / oldest_published
    - stale_rows: rows where age_days > freshness_threshold_days
    - stale_ratio
    - is_fresh: True if stale_ratio <= 0.25
    """
    report_path = Path(report_path)
    threshold = settings.freshness_threshold_days

    total_rows = len(df)

    if "age_days" in df.columns:
        valid = df["age_days"].dropna()
        stale_rows = int((valid > threshold).sum())
        stale_ratio = stale_rows / total_rows if total_rows > 0 else 0.0
    else:
        stale_rows = 0
        stale_ratio = 0.0

    if "published" in df.columns:
        published_sorted = df["published"].dropna().sort_values()
        oldest = str(published_sorted.iloc[0]) if len(published_sorted) > 0 else "N/A"
        latest = str(published_sorted.iloc[-1]) if len(published_sorted) > 0 else "N/A"
    else:
        oldest = latest = "N/A"

    is_fresh = stale_ratio <= 0.25

    payload: dict[str, Any] = {
        "latest_published": latest,
        "oldest_published": oldest,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": is_fresh,
        "freshness_threshold_days": threshold,
    }

    write_json(report_path, payload)
    return payload
