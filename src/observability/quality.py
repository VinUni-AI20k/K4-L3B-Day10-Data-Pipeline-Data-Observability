from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


_MAX_STALE_RATIO = 0.25


def _quality_report_path(settings: Settings, report_name: str) -> Path:
    stage = safe_slug(report_name)
    if stage == "baseline":
        return settings.paths.baseline_quality_report
    if stage == "corrupted":
        return settings.paths.corrupted_quality_report
    return settings.paths.quality_dir / f"{stage}_quality_report.json"


def _freshness_report_path(settings: Settings, report_name: str) -> Path:
    stage = safe_slug(report_name)
    if stage == "baseline":
        return settings.paths.freshness_report
    return settings.paths.quality_dir / f"{stage}_freshness_report.json"


def _expectation_summary(result: Any) -> dict[str, Any]:
    payload = result.to_json_dict()
    config = payload.get("expectation_config", {})
    kwargs = config.get("kwargs", {})
    details = payload.get("result", {})
    exception = payload.get("exception_info", {})
    return {
        "expectation_type": config.get("type"),
        "column": kwargs.get("column"),
        "success": bool(payload.get("success")),
        "observed_value": details.get("observed_value"),
        "element_count": details.get("element_count"),
        "unexpected_count": details.get("unexpected_count"),
        "unexpected_percent": details.get("unexpected_percent"),
        "exception_message": exception.get("exception_message") if exception.get("raised_exception") else None,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the required GX 1.x expectations and the freshness SLA gate."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    stage = safe_slug(report_name)
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_{stage}_source")
    data_asset = data_source.add_dataframe_asset(name=f"papers_{stage}_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe(f"papers_{stage}_batch")

    expectations = [
        gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        gxe.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="title"),
        gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gxe.ExpectColumnValuesToBeUnique(column="paper_id"),
        gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]
    suite = context.suites.add(
        gx.ExpectationSuite(name=f"papers_{stage}_suite", expectations=expectations)
    )
    validation = context.validation_definitions.add(
        gx.ValidationDefinition(
            name=f"papers_{stage}_validation",
            data=batch_definition,
            suite=suite,
        )
    )
    validation_result = validation.run(
        batch_parameters={"dataframe": df},
        result_format="SUMMARY",
    )

    freshness = build_freshness_report(
        df,
        settings,
        _freshness_report_path(settings, report_name),
    )
    gx_success = bool(validation_result.success)
    payload = {
        "report_name": report_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "success": gx_success and freshness["is_fresh"],
        "gx_success": gx_success,
        "freshness_success": freshness["is_fresh"],
        "row_count": len(df),
        "statistics": validation_result.to_json_dict().get("statistics", {}),
        "expectations": [_expectation_summary(item) for item in validation_result.results],
        "freshness": freshness,
    }
    write_json(_quality_report_path(settings, report_name), payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Measure publication freshness using the configured age threshold."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    total_rows = len(df)
    if "published" in df.columns:
        published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    else:
        published = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")

    if "age_days" in df.columns:
        age_days = pd.to_numeric(df["age_days"], errors="coerce")
    else:
        age_days = pd.Series(float("nan"), index=df.index, dtype="float64")

    invalid_age_rows = int(age_days.isna().sum())
    stale_mask = age_days > settings.freshness_threshold_days
    stale_rows = int(stale_mask.sum())
    stale_ratio = stale_rows / total_rows if total_rows else 0.0
    valid_published = published.dropna()
    latest = valid_published.max().date().isoformat() if not valid_published.empty else None
    oldest = valid_published.min().date().isoformat() if not valid_published.empty else None
    stale_paper_ids = (
        df.loc[stale_mask, "paper_id"].astype(str).tolist()
        if "paper_id" in df.columns
        else []
    )

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": _MAX_STALE_RATIO,
        "latest_published": latest,
        "oldest_published": oldest,
        "stale_rows": stale_rows,
        "stale_ratio": stale_ratio,
        "stale_paper_ids": stale_paper_ids,
        "invalid_age_rows": invalid_age_rows,
        "total_rows": total_rows,
        "is_fresh": total_rows > 0 and invalid_age_rows == 0 and stale_ratio <= _MAX_STALE_RATIO,
    }
    write_json(Path(report_path), payload)
    return payload
