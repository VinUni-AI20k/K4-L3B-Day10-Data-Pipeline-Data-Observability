from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


def _freshness_metrics(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    total_rows = len(df)
    ages = pd.to_numeric(df["age_days"], errors="coerce") if "age_days" in df else pd.Series(dtype=float)
    invalid_age_rows = total_rows - int(ages.notna().sum())
    stale_rows = int(ages.gt(settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 0.0
    published = pd.to_datetime(df["published"], errors="coerce") if "published" in df else pd.Series(dtype="datetime64[ns]")
    latest = published.max()
    oldest = published.min()
    return {
        "latest_published": latest.date().isoformat() if pd.notna(latest) else None,
        "oldest_published": oldest.date().isoformat() if pd.notna(oldest) else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "invalid_age_rows": invalid_age_rows,
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": 0.25,
        "is_fresh": total_rows > 0 and invalid_age_rows == 0 and stale_ratio <= 0.25,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str | None = None) -> dict[str, Any]:
    """Validate a dataframe with GX 1.x and the freshness SLA.

    Pass report_name=None to inspect the result without writing an artifact.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name="papers_quality")
    for expectation in (
        gx.expectations.ExpectTableRowCountToBeBetween(
            min_value=settings.max_results, max_value=settings.max_results
        ),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="summary"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=1),
    ):
        suite.add_expectation(expectation)

    validation = batch.validate(suite)
    gx_result = validation.to_json_dict()
    freshness = _freshness_metrics(df, settings)
    payload = {
        "success": bool(validation.success) and freshness["is_fresh"],
        "gx_success": bool(validation.success),
        "freshness": freshness,
        "statistics": gx_result["statistics"],
        "results": gx_result["results"],
    }
    if report_name is not None:
        report_path = settings.paths.quality_dir / f"{safe_slug(report_name)}_quality_report.json"
        write_json(report_path, payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path=None) -> dict[str, Any]:
    """Summarize the SLA; omit report_path for an in-memory check."""
    payload = _freshness_metrics(df, settings)
    if report_path is not None:
        write_json(report_path, payload)
    return payload
