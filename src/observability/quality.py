from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json


_STALE_RATIO_LIMIT = 0.25


def _quality_report_path(settings: Settings, report_name: str) -> Path:
    """Resolve a report name without allowing it to escape the quality directory."""
    aliases = {
        "baseline": settings.paths.baseline_quality_report,
        "baseline_quality_report": settings.paths.baseline_quality_report,
        "corrupted": settings.paths.corrupted_quality_report,
        "corrupted_quality_report": settings.paths.corrupted_quality_report,
    }
    normalized = Path(str(report_name)).stem
    if normalized in aliases:
        return aliases[normalized]
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", normalized).strip("._") or "quality_report"
    if not safe_name.endswith("quality_report"):
        safe_name = f"{safe_name}_quality_report"
    return settings.paths.quality_dir / f"{safe_name}.json"


def _freshness_values(df: pd.DataFrame, threshold_days: int) -> dict[str, Any]:
    total_rows = int(len(df))
    if "age_days" in df.columns:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
    elif "published" in df.columns:
        published = pd.to_datetime(df["published"], errors="coerce", utc=True)
        today = pd.Timestamp(now_utc().date(), tz="UTC")
        ages = (today - published).dt.days
    else:
        ages = pd.Series(float("nan"), index=df.index, dtype="float64")

    invalid_age_rows = int(ages.isna().sum())
    stale_rows = int((ages > threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 0.0
    is_fresh = total_rows > 0 and invalid_age_rows == 0 and stale_ratio <= _STALE_RATIO_LIMIT
    return {
        "threshold_days": threshold_days,
        "stale_ratio_limit": _STALE_RATIO_LIMIT,
        "stale_rows": stale_rows,
        "invalid_age_rows": invalid_age_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "is_fresh": is_fresh,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the GX 1.x quality gate and persist a compact JSON result.

    Five expectation instances are used from the four expectation classes required
    by the rubric. ``ExpectColumnValuesToNotBeNull`` is intentionally applied to
    both ``paper_id`` and ``title``.
    """
    required_columns = {"paper_id", "title", "summary", "published", "age_days"}
    missing_columns = sorted(required_columns - set(df.columns))
    expectation_results: list[dict[str, Any]] = []

    if not missing_columns:
        context = gx.get_context(mode="ephemeral")
        suffix = re.sub(r"[^a-zA-Z0-9]+", "_", str(report_name)).strip("_") or "quality"
        data_source = context.data_sources.add_pandas(name=f"papers_{suffix}")
        asset = data_source.add_dataframe_asset(name=f"papers_{suffix}_asset")
        batch_definition = asset.add_batch_definition_whole_dataframe(name="whole_dataframe")
        batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

        expectations = [
            gxe.ExpectTableRowCountToBeBetween(
                min_value=settings.max_results,
                max_value=settings.max_results,
            ),
            gxe.ExpectColumnValuesToNotBeNull(column="paper_id"),
            gxe.ExpectColumnValuesToNotBeNull(column="title"),
            gxe.ExpectColumnValuesToBeUnique(column="paper_id"),
            gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20),
        ]
        for expectation in expectations:
            validation = batch.validate(expectation)
            result = validation.to_json_dict()
            config = result.get("expectation_config", {})
            expectation_results.append(
                {
                    "expectation_type": config.get("type") or expectation.__class__.__name__,
                    "column": config.get("kwargs", {}).get("column"),
                    "success": bool(result.get("success")),
                    "result": result.get("result", {}),
                    "exception_info": result.get("exception_info", {}),
                }
            )

    freshness = _freshness_values(df, settings.freshness_threshold_days)
    expectations_success = bool(expectation_results) and all(
        item["success"] for item in expectation_results
    )
    payload: dict[str, Any] = {
        "report_name": Path(str(report_name)).stem,
        "generated_at": now_utc().isoformat(),
        "success": not missing_columns and expectations_success and freshness["is_fresh"],
        "row_count": int(len(df)),
        "missing_columns": missing_columns,
        "expectations": expectation_results,
        "freshness_sla": freshness,
    }
    write_json(_quality_report_path(settings, report_name), payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize publication freshness and persist it as JSON."""
    if "published" in df.columns:
        published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    else:
        published = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")

    freshness = _freshness_values(df, settings.freshness_threshold_days)
    valid_published = published.dropna()
    payload: dict[str, Any] = {
        "generated_at": now_utc().isoformat(),
        "latest_published": (
            valid_published.max().date().isoformat() if not valid_published.empty else None
        ),
        "oldest_published": (
            valid_published.min().date().isoformat() if not valid_published.empty else None
        ),
        "invalid_published_rows": int(published.isna().sum()),
        **freshness,
    }
    payload["is_fresh"] = bool(payload["is_fresh"] and payload["invalid_published_rows"] == 0)
    write_json(Path(report_path), payload)
    return payload
