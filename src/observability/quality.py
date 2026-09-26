from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
import uuid

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json

logger = logging.getLogger(__name__)


def evaluate_freshness_sla(
    df: pd.DataFrame,
    settings: Settings | Any | None = None,
    threshold_days: int | None = None,
    max_stale_ratio: float = 0.25,
) -> dict[str, Any]:
    """Evaluate data freshness SLA based on age_days.

    Alert if proportion of records with age_days > threshold_days exceeds max_stale_ratio.
    """
    total_rows = len(df)
    if isinstance(settings, (int, float)):
        threshold = int(settings)
    elif settings is not None and hasattr(settings, "freshness_threshold_days"):
        threshold = int(settings.freshness_threshold_days)
    else:
        threshold = threshold_days or 180

    if total_rows == 0:
        return {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "total_rows": 0,
            "threshold_days": threshold,
            "max_stale_ratio": max_stale_ratio,
            "is_fresh": True,
        }

    latest_published: str | None = None
    oldest_published: str | None = None
    if "published" in df.columns and not df["published"].dropna().empty:
        latest_published = str(df["published"].dropna().max())
        oldest_published = str(df["published"].dropna().min())

    if "age_days" in df.columns:
        stale_rows = int((df["age_days"] > threshold).sum())
    else:
        stale_rows = 0

    stale_ratio = float(stale_rows / total_rows)
    # Cảnh báo is_fresh = False nếu tỷ lệ bài báo cũ (> 180 ngày) vượt quá 25% (0.25)
    is_fresh = bool(stale_ratio <= max_stale_ratio)

    return {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "total_rows": total_rows,
        "threshold_days": threshold,
        "max_stale_ratio": max_stale_ratio,
        "is_fresh": is_fresh,
    }


def build_freshness_report(
    df: pd.DataFrame,
    settings: Settings,
    report_path: Path | str | None = None,
) -> dict[str, Any]:
    """Generate and save freshness report payload."""
    report = evaluate_freshness_sla(df, settings)
    target_path = Path(report_path) if report_path else settings.paths.freshness_report
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def run_data_quality_checks(
    df: pd.DataFrame,
    settings: Settings,
    stage: str = "baseline",
) -> dict[str, Any]:
    """Run Data Quality Gate using Great Expectations 1.x Ephemeral Context and Freshness SLA.

    Expectations:
    1. ExpectTableRowCountToBeBetween: 5 to 5000 rows.
    2. ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding.
    3. ExpectColumnValuesToBeUnique: paper_id.
    4. ExpectColumnValueLengthsToBeBetween: summary min 30 chars.
    5. Freshness SLA check (age_days > 180 days ratio <= 25%).
    """
    # 1. Ephemeral Context GX 1.x
    context = gx.get_context(mode="ephemeral")
    unique_suffix = uuid.uuid4().hex[:8]
    ds_name = f"papers_source_{stage}_{unique_suffix}"
    asset_name = f"papers_asset_{stage}_{unique_suffix}"
    batch_name = f"papers_batch_{stage}_{unique_suffix}"

    data_source = context.data_sources.add_pandas(name=ds_name)
    data_asset = data_source.add_dataframe_asset(name=asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe(batch_name)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # 2. Add 4 mandatory expectations
    expectation_suite_name = f"papers_suite_{stage}_{unique_suffix}"
    suite = context.suites.add(gx.ExpectationSuite(name=expectation_suite_name))

    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    # 3. Validate batch against suite
    try:
        validation_result = batch.validate(suite)
        gx_success = bool(validation_result.success)
        gx_details = validation_result.to_json_dict()
    except Exception as exc:
        gx_success = False
        gx_details = {"error": str(exc), "success": False}

    # 4. Freshness check
    freshness_report = build_freshness_report(df, settings, settings.paths.freshness_report)
    overall_success = bool(gx_success and freshness_report["is_fresh"])

    result_payload = {
        "stage": stage,
        "success": overall_success,
        "gx_success": gx_success,
        "is_fresh": freshness_report["is_fresh"],
        "total_records": len(df),
        "freshness": freshness_report,
        "validation_result": gx_details,
    }

    # 5. Write report file into data/quality/
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    report_file = settings.paths.quality_dir / f"{stage}_quality_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(result_payload, f, ensure_ascii=False, indent=2)

    if stage == "baseline":
        with open(settings.paths.baseline_quality_report, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, ensure_ascii=False, indent=2)
    elif stage == "corrupted":
        with open(settings.paths.corrupted_quality_report, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, ensure_ascii=False, indent=2)
    elif stage == "repaired":
        with open(settings.paths.repaired_quality_report, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, ensure_ascii=False, indent=2)

    return result_payload
