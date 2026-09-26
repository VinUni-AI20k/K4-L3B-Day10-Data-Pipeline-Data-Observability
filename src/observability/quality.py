from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import write_json

FRESHNESS_STALE_RATIO_THRESHOLD = 0.25


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Danh gia ti le bai bao cu (age_days > threshold) so voi nguong SLA."""
    total_rows = len(df)
    if total_rows == 0:
        return {
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": False,
        }

    stale_mask = df["age_days"] > settings.freshness_threshold_days
    stale_rows = int(stale_mask.sum())
    stale_ratio = stale_rows / total_rows
    is_fresh = stale_ratio <= FRESHNESS_STALE_RATIO_THRESHOLD

    return {
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "is_fresh": is_fresh,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, stage: str) -> dict[str, Any]:
    """Chay bo 4 Expectations bat buoc voi Great Expectations 1.x Ephemeral Context,
    ket hop danh gia freshness SLA."""
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"{stage}_source")
    data_asset = data_source.add_dataframe_asset(name=f"{stage}_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"{stage}_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]

    expectation_results = []
    overall_success = True
    for expectation in expectations:
        result = batch.validate(expectation)
        result_dict = result.to_json_dict()
        expectation_results.append(result_dict)
        if not result_dict.get("success", False):
            overall_success = False

    freshness = evaluate_freshness_sla(df, settings)
    if not freshness["is_fresh"]:
        overall_success = False

    report = {
        "stage": stage,
        "success": overall_success,
        "row_count": len(df),
        "expectations": expectation_results,
        "freshness": freshness,
    }

    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    output_path = (
        settings.paths.baseline_quality_report
        if stage == "baseline"
        else settings.paths.corrupted_quality_report
        if "corrupt" in stage
        else settings.paths.quality_dir / f"{stage}_quality_report.json"
    )
    write_json(output_path, report)

    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report va ghi JSON."""
    published_dates = pd.to_datetime(df["published"], errors="coerce", utc=True) if len(df) else pd.Series([], dtype="datetime64[ns, UTC]")
    latest_published = published_dates.max()
    oldest_published = published_dates.min()

    freshness = evaluate_freshness_sla(df, settings)

    payload = {
        "latest_published": latest_published.isoformat() if pd.notna(latest_published) else None,
        "oldest_published": oldest_published.isoformat() if pd.notna(oldest_published) else None,
        "stale_rows": freshness["stale_rows"],
        "total_rows": freshness["total_rows"],
        "stale_ratio": freshness["stale_ratio"],
        "is_fresh": freshness["is_fresh"],
        "freshness_threshold_days": settings.freshness_threshold_days,
    }
    write_json(report_path, payload)
    return payload
