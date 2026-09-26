from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
from great_expectations import expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Khởi tạo Ephemeral Context Great Expectations 1.x và thực thi 4 nhóm Expectations cùng Freshness SLA."""
    context = gx.get_context(mode="ephemeral")
    ds_name = f"papers_source_{report_name}"
    asset_name = f"papers_asset_{report_name}"
    batch_name = f"papers_batch_{report_name}"

    data_source = context.data_sources.add_pandas(name=ds_name)
    data_asset = data_source.add_dataframe_asset(name=asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe(batch_name)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # 4 Expectations thiết yếu theo chuẩn GX 1.x
    expectations = [
        gxe.ExpectTableRowCountToBeBetween(min_value=15, max_value=50),
        gxe.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="title"),
        gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gxe.ExpectColumnValuesToBeUnique(column="paper_id"),
        gxe.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8),
        gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20),
    ]

    check_results = []
    all_gx_success = True

    for exp in expectations:
        res = batch.validate(exp)
        success = bool(res.success)
        if not success:
            all_gx_success = False

        kwargs = {}
        if hasattr(exp, "configuration") and exp.configuration and hasattr(exp.configuration, "kwargs"):
            kwargs = dict(exp.configuration.kwargs)

        check_results.append({
            "expectation_type": exp.__class__.__name__,
            "kwargs": kwargs,
            "success": success,
            "result": dict(getattr(res, "result", {})),
        })

    # Đánh giá Freshness SLA: cảnh báo nếu tỷ lệ bài báo có age_days > 180 vượt quá 25%
    total_rows = len(df)
    stale_rows = 0
    stale_ratio = 0.0
    is_fresh = True
    if "age_days" in df.columns and total_rows > 0:
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
        stale_ratio = float(stale_rows / total_rows)
        if stale_ratio > 0.25:
            is_fresh = False

    overall_success = bool(all_gx_success and is_fresh)

    report = {
        "report_name": report_name,
        "success": overall_success,
        "gx_success": all_gx_success,
        "is_fresh": is_fresh,
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "checks": check_results,
    }

    # Lưu báo cáo vào data/quality/
    out_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    if report_name == "baseline":
        out_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        out_path = settings.paths.corrupted_quality_report

    write_json(out_path, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | None = None) -> dict[str, Any]:
    """Tổng hợp báo cáo Freshness SLA theo chu kỳ."""
    total_rows = len(df)
    if total_rows == 0:
        report = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": False,
            "freshness_threshold_days": settings.freshness_threshold_days,
        }
    else:
        latest_published = str(df["published"].max())
        oldest_published = str(df["published"].min())
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
        stale_ratio = float(stale_rows / total_rows)
        is_fresh = stale_ratio <= 0.25
        report = {
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "stale_ratio": round(stale_ratio, 4),
            "is_fresh": is_fresh,
            "freshness_threshold_days": settings.freshness_threshold_days,
        }

    target = report_path or settings.paths.freshness_report
    write_json(target, report)
    return report
