from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _jsonify(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonify(item) for item in value]
    if hasattr(value, "to_json_dict"):
        try:
            return _jsonify(value.to_json_dict())
        except Exception:
            pass
    if hasattr(value, "model_dump"):
        try:
            return _jsonify(value.model_dump())
        except Exception:
            pass
    return str(value)


def _gx_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    gx_df = df.copy()
    for column in gx_df.columns:
        sample = gx_df[column].dropna()
        if sample.empty:
            continue
        if isinstance(sample.iloc[0], (list, dict)):
            gx_df[column] = gx_df[column].apply(lambda value: value if isinstance(value, str) else str(value))
    for column in ("paper_id", "title", "summary"):
        if column in gx_df.columns:
            gx_df[column] = gx_df[column].fillna("").astype(str)
    return gx_df


def _quality_report_path(settings: Settings, report_name: str):
    mapping = {
        "baseline": settings.paths.baseline_quality_report,
        "corrupted": settings.paths.corrupted_quality_report,
    }
    return mapping.get(report_name, settings.paths.quality_dir / f"{report_name}_quality_report.json")


def _freshness_payload(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    if df.empty:
        return {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 1.0,
            "threshold_days": settings.freshness_threshold_days,
            "stale_ratio_limit": 0.25,
            "is_fresh": False,
        }

    published = pd.to_datetime(df["published"], utc=True, errors="coerce")
    stale_mask = pd.to_numeric(df["age_days"], errors="coerce").fillna(0) > settings.freshness_threshold_days
    stale_rows = int(stale_mask.sum())
    total_rows = int(len(df))
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    latest = published.max()
    oldest = published.min()
    return {
        "latest_published": None if pd.isna(latest) else latest.date().isoformat(),
        "oldest_published": None if pd.isna(oldest) else oldest.date().isoformat(),
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(float(stale_ratio), 4),
        "threshold_days": settings.freshness_threshold_days,
        "stale_ratio_limit": 0.25,
        "is_fresh": bool(stale_ratio <= 0.25),
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run Great Expectations 1.x checks plus a freshness SLA summary."""
    import great_expectations as gx
    from great_expectations.expectations import (
        ExpectColumnValueLengthsToBeBetween,
        ExpectColumnValuesToBeUnique,
        ExpectColumnValuesToNotBeNull,
        ExpectTableRowCountToBeBetween,
    )

    gx_df = _gx_dataframe(df)
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    settings.paths.gx_dir.mkdir(parents=True, exist_ok=True)

    context = gx.get_context(mode="ephemeral")
    suffix = "".join(ch if ch.isalnum() else "_" for ch in report_name) or "papers"
    data_source = context.data_sources.add_pandas(name=f"papers_source_{suffix}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{suffix}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{suffix}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": gx_df})

    suite = gx.ExpectationSuite(name=f"papers_suite_{suffix}")
    suite.add_expectation(ExpectTableRowCountToBeBetween(min_value=20, max_value=30))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20, max_value=20000))
    suite.add_expectation(ExpectColumnValueLengthsToBeBetween(column="title", min_value=8, max_value=500))

    validation = batch.validate(suite)
    freshness = _freshness_payload(df, settings)
    results = _jsonify(validation)
    success = bool(getattr(validation, "success", False))
    payload = {
        "success": success,
        "report_name": report_name,
        "row_count": int(len(df)),
        "statistics": _jsonify(getattr(validation, "statistics", {})),
        "results": results,
        "freshness": freshness,
        "expectations": [
            "ExpectTableRowCountToBeBetween",
            "ExpectColumnValuesToNotBeNull",
            "ExpectColumnValuesToBeUnique",
            "ExpectColumnValueLengthsToBeBetween",
        ],
    }
    write_json(_quality_report_path(settings, report_name), payload)
    write_json(settings.paths.gx_dir / f"{suffix}_validation.json", results)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize published-date freshness against the 180-day SLA."""
    payload = _freshness_payload(df, settings)
    write_json(report_path, payload)
    return payload
